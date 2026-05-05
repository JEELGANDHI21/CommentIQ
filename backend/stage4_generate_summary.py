"""
Stage 4 — AI Summary
======================
Reads the sentiment-enriched CSV from Stage 3, builds a structured context
from the sentiment data, and uses OpenRouter to generate a rich, human-readable
video summary report.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import pandas as pd

from llm_client import get_client

log = logging.getLogger(__name__)


@dataclass
class VideoReport:
    video_id: str
    video_summary: str
    total_comments: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    avg_relevance_score: float
    avg_weighted_sentiment: float          # new — mean of polarity × relevance
    top_liked_comment: str
    top_liked_count: int
    most_positive_comment: str
    most_positive_polarity: float          # was most_positive_score
    most_negative_comment: str
    most_negative_polarity: float          # was most_negative_score
    ai_overall_sentiment: str
    ai_praise_themes: str
    ai_criticism_themes: str
    ai_verdict: str
    output_json_path: str
    output_md_path: str


def _build_context(df: pd.DataFrame, video_summary: str) -> str:
    total = len(df)
    pos = (df["sentiment"] == "positive").sum()
    neg = (df["sentiment"] == "negative").sum()
    neu = (df["sentiment"] == "neutral").sum()

    # Use subjectivity (model confidence) for ranking — matches Stage 3 columns
    top_pos = (
        df[df["sentiment"] == "positive"]
        .nlargest(10, "subjectivity")["text"].tolist()          # ← was sentiment_score
    )
    top_neg = (
        df[df["sentiment"] == "negative"]
        .nlargest(10, "subjectivity")["text"].tolist()          # ← was sentiment_score
    )

    # Top by weighted_sentiment — most relevant AND most emotionally strong
    top_weighted = (
        df.nlargest(5, "weighted_sentiment")
        [["text", "like_count", "sentiment", "weighted_sentiment"]]
        .to_dict("records")
    )

    top_liked = (
        df.nlargest(5, "like_count")
        [["text", "like_count", "sentiment"]].to_dict("records")
    )

    def fmt(comments):
        return "\n".join(f'  - "{c}"' for c in comments)

    def fmt_liked(records):
        return "\n".join(
            f'  - [{r["like_count"]} likes | {r["sentiment"]}] "{r["text"]}"'
            for r in records
        )

    def fmt_weighted(records):
        return "\n".join(
            f'  - [w={r["weighted_sentiment"]:.3f} | {r["sentiment"]}] "{r["text"]}"'
            for r in records
        )

    return f"""VIDEO SUMMARY:
{video_summary}

SENTIMENT BREAKDOWN ({total} relevant comments):
  Positive : {pos} ({100*pos/total:.1f}%)
  Negative : {neg} ({100*neg/total:.1f}%)
  Neutral  : {neu} ({100*neu/total:.1f}%)

TOP POSITIVE COMMENTS (by model confidence):
{fmt(top_pos)}

TOP NEGATIVE COMMENTS (by model confidence):
{fmt(top_neg)}

TOP COMMENTS BY WEIGHTED SENTIMENT (relevance × polarity — best overall signal):
{fmt_weighted(top_weighted)}

MOST LIKED COMMENTS:
{fmt_liked(top_liked)}"""


SYSTEM = (
    "You are an expert video content analyst. Write concise, insightful, neutral "
    "summaries of YouTube audience sentiment. Be specific — reference actual themes "
    "from the comments. Plain prose only, no bullet points, no markdown headers."
)


def _llm(prompt: str, max_tokens: int = 200) -> str:
    try:
        return get_client().chat(prompt=prompt, system=SYSTEM, max_tokens=max_tokens, temperature=0.4)
    except Exception as exc:
        log.warning("LLM call failed: %s", exc)
        return "(generation failed)"


def generate_ai_sections(context: str) -> dict:
    log.info("Generating AI narrative (4 sections)…")

    overall = _llm(
        f"{context}\n\nWrite 2 sentences summarising the overall audience sentiment. "
        "Be specific about tone and what is driving it.", 150)
    log.info("  ✓ Overall sentiment")

    praise = _llm(
        f"{context}\n\nBased only on the positive comments, write 2–3 sentences describing "
        "the specific things viewers praised. Name concrete themes.", 200)
    log.info("  ✓ Praise themes")

    criticism = _llm(
        f"{context}\n\nBased only on the negative comments, write 2–3 sentences describing "
        "specific criticisms or concerns. If very few, note that too.", 200)
    log.info("  ✓ Criticism themes")

    verdict = _llm(
        f"{context}\n\nWrite a single verdict paragraph (3–5 sentences) a content creator "
        "could read to quickly understand how their audience received this video — "
        "overall reaction, strongest emotions, one key takeaway.", 250)
    log.info("  ✓ Verdict")

    return {
        "ai_overall_sentiment": overall,
        "ai_praise_themes":     praise,
        "ai_criticism_themes":  criticism,
        "ai_verdict":           verdict,
    }


def _render_markdown(r: VideoReport) -> str:
    bar = lambda pct: "█" * round(pct / 5)
    return f"""# Video Sentiment Report
**Video ID:** `{r.video_id}`

---

## What This Video Is About
{r.video_summary}

---

## Audience Sentiment
| Label    | Count | % | Bar |
|----------|------:|--:|-----|
| Positive | {r.positive_count:>5} | {r.positive_pct:.1f}% | {bar(r.positive_pct)} |
| Negative | {r.negative_count:>5} | {r.negative_pct:.1f}% | {bar(r.negative_pct)} |
| Neutral  | {r.neutral_count:>5} | {r.neutral_pct:.1f}% | {bar(r.neutral_pct)} |

*{r.total_comments} relevant comments · avg relevance: {r.avg_relevance_score:.3f} · avg weighted sentiment: {r.avg_weighted_sentiment:.3f}*

---

## Overall Sentiment
{r.ai_overall_sentiment}

## What Viewers Praised
{r.ai_praise_themes}

## What Viewers Criticised
{r.ai_criticism_themes}

---

## Notable Comments

**Most liked** ({r.top_liked_count:,} likes):
> {r.top_liked_comment}

**Most positive** (polarity {r.most_positive_polarity:.3f}):
> {r.most_positive_comment}

**Most negative** (polarity {r.most_negative_polarity:.3f}):
> {r.most_negative_comment}

---

## Verdict
{r.ai_verdict}
"""


def summarise(
    sentiment_csv_path: str,
    video_summary: str = "",
    video_id: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> VideoReport:
    csv_path = Path(sentiment_csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Sentiment CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    log.info("Loaded %d sentiment-labelled comments from %s", len(df), csv_path.name)

    if video_id is None:
        video_id = csv_path.name.split("_")[0]

    total   = len(df)
    pos     = int((df["sentiment"] == "positive").sum())
    neg     = int((df["sentiment"] == "negative").sum())
    neu     = int((df["sentiment"] == "neutral").sum())
    avg_rel = float(df["relevance_score"].mean()) if "relevance_score" in df.columns else 0.0
    avg_w   = float(df["weighted_sentiment"].mean()) if "weighted_sentiment" in df.columns else 0.0

    top_liked_row = df.nlargest(1, "like_count").iloc[0]

    # Use polarity for ranking most positive / negative         ← was sentiment_score
    most_pos_row  = df[df["sentiment"] == "positive"].nlargest(1, "polarity").iloc[0]
    neg_df        = df[df["sentiment"] == "negative"]
    most_neg_row  = neg_df.nlargest(1, "subjectivity").iloc[0] if len(neg_df) else df.iloc[-1]

    context     = _build_context(df, video_summary)
    ai_sections = generate_ai_sections(context)

    out_dir = Path(output_dir) if output_dir else csv_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{video_id}_video_report.json"
    md_path   = out_dir / f"{video_id}_video_report.md"

    report = VideoReport(
        video_id=video_id,
        video_summary=video_summary,
        total_comments=total,
        positive_count=pos,
        negative_count=neg,
        neutral_count=neu,
        positive_pct=round(100 * pos / total, 1),
        negative_pct=round(100 * neg / total, 1),
        neutral_pct=round(100 * neu / total, 1),
        avg_relevance_score=round(avg_rel, 4),
        avg_weighted_sentiment=round(avg_w, 4),
        top_liked_comment=str(top_liked_row["text"]),
        top_liked_count=int(top_liked_row["like_count"]),
        most_positive_comment=str(most_pos_row["text"]),
        most_positive_polarity=round(float(most_pos_row["polarity"]), 4),    # ← was sentiment_score
        most_negative_comment=str(most_neg_row["text"]),
        most_negative_polarity=round(float(most_neg_row["polarity"]), 4),    # ← was sentiment_score
        output_json_path=str(json_path),
        output_md_path=str(md_path),
        **ai_sections,
    )

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    log.info("Report JSON → %s", json_path)

    md_path.write_text(_render_markdown(report), encoding="utf-8")
    log.info("Report markdown → %s", md_path)

    log.info("Stage 4 complete.")
    return report