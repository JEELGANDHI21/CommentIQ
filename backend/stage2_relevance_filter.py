"""
Stage 2 — Relevance Filter
===========================
Embeds the video summary and each comment using a sentence-transformer model,
computes cosine similarity, and writes relevant comments to a CSV file.
 
Comments whose similarity score meets the threshold are kept; the rest are
discarded (or optionally written to a separate rejection log).
 
Requirements:
    pip install sentence-transformers pandas
 
How it works:
    1. Embed the video summary → one reference vector.
    2. Embed all comment texts in a single batch → comment vectors.
    3. Compute cosine similarity between each comment vector and the reference.
    4. Keep comments where similarity >= threshold (default 0.20).
    5. Write kept comments + metadata + score to relevant_comments.csv.
 
Threshold guide:
    0.15 — very loose  (keeps most comments; good for general/vague videos)
    0.20 — balanced    (default; works well for most music/talk videos)
    0.30 — strict      (only tightly on-topic comments; good for tutorial videos)
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

_model = None
_model_name : str = ""

DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"

def _get_model(model_name : str = DEFAULT_EMBED_MODEL):
    """Load and cache the sentence-transformer model (loaded once per process)."""
    global _model, _model_name
    
    if _model is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
              "sentence-transformers is not installed.\n"
                "  Run: pip install sentence-transformers"
            )  
        log.info("Loading embedding model '%s' (first run downloads ~80 MB)…", model_name)
        
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        log.info("Embedding model loaded.")
    return _model

def compute_similarities(
    reference_text : str,
    candidate_texts : list[str],
    model_name : str = DEFAULT_EMBED_MODEL
)-> list[float]:
    """
    Return cosine similarity scores between `reference_text` and each candidate.
 
    Args:
        reference_text:   The video summary (reference embedding).
        candidate_texts:  List of comment texts to compare against.
        model_name:       Sentence-transformer model to use.
 
    Returns:
        List of float scores in [-1, 1]; practically in [0, 1] for natural text.
        Index i corresponds to candidate_texts[i].
    """
    import numpy as np
    
    model = _get_model(model_name)
    
    log.info(
        "Embedding reference + %d comments with '%s'…",
        len(candidate_texts), model_name,
    )
    
    ref_vec = model.encode(reference_text, convert_to_numpy=True, normalize_embeddings=True)
    
    comment_vec = model.encode(
        candidate_texts, 
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=len(candidate_texts) > 200,
    )
    
    scores = (comment_vec @ ref_vec).tolist()
    log.info("Similarity scores computed — min=%.3f, max=%.3f, mean=%.3f",
             min(scores), max(scores), sum(scores) / len(scores))
    return scores


@dataclass
class FilterResult:
    total : int
    kept : int
    discarded : int
    threshold : float
    output_path : str
    rejected_path : Optional[str]
    
def filter_comments(
    video_data,
    output_dir : str = "outputs",
    threshold : float = 0.20,
    embed_model : str = DEFAULT_EMBED_MODEL,
    save_rejected : bool = False
) -> FilterResult:
    """
    Full Stage 2 pipeline: embed → score → filter → write CSV.
 
    Args:
        video_data:   VideoData object returned by stage1_collect.collect().
        output_dir:   Directory to write CSV files into (created if missing).
        threshold:    Minimum cosine similarity to keep a comment.
        embed_model:  Sentence-transformer model name.
        save_rejected: If True, also save discarded comments to a separate CSV.
 
    Returns:
        FilterResult with counts and output file paths.
    """
    
    comments = video_data.comments
    if not comments:
        log.warning("No comments to filter.")
        return FilterResult(0, 0, 0, threshold, "", None)
    
    if not video_data.video_summary:
        log.warning(
            "video_summary is empty — all comments will score near zero. "
            "Check that Stage 1 LLM summary ran successfully."
        )
    
    # --- Compute scores ---
    texts = [c.text for c in comments]
    scores = compute_similarities(video_data.video_summary, texts, model_name=embed_model)
 
    # --- Split kept / discarded ---
    rows_kept = []
    rows_discarded = []  
    
    for comment, score in zip(comments, scores):
        row = {
            "video_id":     video_data.video_id,
            "comment_id":   comment.comment_id,
            "author":       comment.author,
            "text":         comment.text,
            "like_count":   comment.like_count,
            "reply_count":  comment.reply_count,
            "is_reply":     comment.is_reply,
            "parent_id":    comment.parent_id or "",
            "published_at": comment.published_at,
            "relevance_score": round(score, 4),
        }
        if score >= threshold:
            rows_kept.append(row)
        else:
            rows_discarded.append(row)
    
    # Sort kept comments by relevance score descending
    rows_kept.sort(key=lambda r: r["relevance_score"], reverse=True)
 
    # --- Write CSVs ---
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
 
    safe_id = video_data.video_id
    kept_path = out_dir / f"{safe_id}_relevant_comments.csv"
    rejected_path = out_dir / f"{safe_id}_rejected_comments.csv" if save_rejected else None
    
    df_kept = pd.DataFrame(rows_kept)
    df_kept.to_csv(kept_path, index=False, encoding="utf-8-sig")
    log.info(
        "Wrote %d relevant comments → %s",
        len(rows_kept), kept_path,
    )
 
    if save_rejected and rows_discarded:
        df_rejected = pd.DataFrame(rows_discarded)
        df_rejected.to_csv(rejected_path, index=False, encoding="utf-8-sig")
        log.info("Wrote %d rejected comments → %s", len(rows_discarded), rejected_path)
 
    result = FilterResult(
        total=len(comments),
        kept=len(rows_kept),
        discarded=len(rows_discarded),
        threshold=threshold,
        output_path=str(kept_path),
        rejected_path=str(rejected_path) if rejected_path else None,
    )
 
    log.info(
        "Stage 2 complete — %d/%d comments kept (threshold=%.2f) | "
        "acceptance rate: %.1f%%",
        result.kept, result.total, threshold,
        100 * result.kept / result.total if result.total else 0,
    )
 
    return result
    
    