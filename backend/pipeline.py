"""
pipeline.py — Background pipeline runner with DB state + report caching
"""

import logging
import traceback

import database as db

log = logging.getLogger(__name__)

STAGE_LABELS = {
    1: "Collecting comments",
    2: "Filtering relevant comments",
    3: "Analysing sentiment",
    4: "Generating AI report",
}
STAGE_PCT = {1: 10, 2: 35, 3: 70, 4: 95}


async def run_pipeline(job_id, username, video_url, max_comments, threshold):
    import asyncio
    from pathlib import Path

    output_dir = Path("outputs") / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    async def set_stage(stage):
        await db.update_job_stage(job_id, stage, STAGE_LABELS[stage], STAGE_PCT[stage])
        log.info("[%s] Stage %d — %s", job_id[:8], stage, STAGE_LABELS[stage])

    try:
        # Stage 1
        await set_stage(1)
        from stage1_data_collect import collect
        data = await asyncio.to_thread(collect, video_url, max_comments)

        # Now we know the video_id — update the job row
        await db._execute(
            "UPDATE jobs SET video_id=? WHERE job_id=?",
            data.video_id, job_id,
        )

        # Cache check
        cached = await db.get_cached_report(data.video_id)
        if cached:
            log.info("[%s] Cache hit — %s", job_id[:8], data.video_id)
            await db.complete_job(job_id, cached, cache_hit=True)
            return

        # Stage 2
        await set_stage(2)
        from stage2_relevance_filter import filter_comments
        s2 = await asyncio.to_thread(filter_comments, data, str(output_dir), threshold)

        # Stage 3
        await set_stage(3)
        from stage3_sentiment_analysis import analyse
        s3 = await asyncio.to_thread(analyse, s2.output_path, str(output_dir))
        await db.save_comment_file(data.video_id, s3.output_path)

        # Stage 4
        await set_stage(4)
        from stage4_generate_summary import summarise
        s4 = await asyncio.to_thread(
            summarise, s3.output_path, data.video_summary, data.video_id, str(output_dir)
        )

        result = {
            "video_id":               data.video_id,
            "title":                  data.title,
            "channel":                data.channel,
            "view_count":             data.view_count,
            "video_summary":          data.video_summary,
            "total_comments":         s4.total_comments,
            "positive_count":         s4.positive_count,
            "negative_count":         s4.negative_count,
            "neutral_count":          s4.neutral_count,
            "positive_pct":           s4.positive_pct,
            "negative_pct":           s4.negative_pct,
            "neutral_pct":            s4.neutral_pct,
            "avg_relevance_score":    s4.avg_relevance_score,
            "avg_weighted_sentiment": s4.avg_weighted_sentiment,
            "top_liked_comment":      s4.top_liked_comment,
            "top_liked_count":        s4.top_liked_count,
            "most_positive_comment":  s4.most_positive_comment,
            "most_positive_polarity": s4.most_positive_polarity,
            "most_negative_comment":  s4.most_negative_comment,
            "most_negative_polarity": s4.most_negative_polarity,
            "ai_overall_sentiment":   s4.ai_overall_sentiment,
            "ai_praise_themes":       s4.ai_praise_themes,
            "ai_criticism_themes":    s4.ai_criticism_themes,
            "ai_verdict":             s4.ai_verdict,
        }

        await db.save_report(data.video_id, data.title, data.channel, data.video_summary, result)
        await db.complete_job(job_id, result, cache_hit=False)
        log.info("[%s] Pipeline complete ✓", job_id[:8])

    except Exception as exc:
        await db.fail_job(job_id, str(exc))
        log.error("[%s] Failed: %s\n%s", job_id[:8], exc, traceback.format_exc())