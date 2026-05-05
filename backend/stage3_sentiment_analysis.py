"""
Stage 3 — Sentiment Analysis
==============================
Reads the relevant_comments.csv produced by Stage 2, cleans each comment,
classifies sentiment using RoBERTa, and writes an enriched CSV.

Model: cardiffnlp/twitter-roberta-base-sentiment-latest
  - Fine-tuned on ~124M tweets, excellent for short informal text
  - Labels: negative / neutral / positive

Text cleaning (matches notebook):
  - Strip URLs, @mentions, #hashtags
  - Convert emojis to text descriptions via the `emoji` library
    (e.g. ❤️ → ":red_heart:") so RoBERTa can process them

Output columns added to the CSV:
    clean_text          — pre-processed comment text fed to the model
    polarity            — scores[positive] - scores[negative]  (-1 to +1)
    subjectivity        — max(scores), i.e. model confidence   (0 to 1)
    sentiment           — "negative" | "neutral" | "positive"
    weighted_sentiment  — polarity x relevance_score

Requirements:
    pip install transformers torch pandas emoji
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
LABELS = ["negative", "neutral", "positive"]   # model output order

# Cached model + tokenizer (loaded once per process)
_tokenizer = None
_model = None


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_model():
    global _tokenizer, _model
    if _model is None:
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
        except ImportError:
            raise ImportError(
                "transformers is not installed.\n"
                "  Run: pip install transformers torch"
            )
        log.info("Loading model '%s' (first run downloads ~500 MB)…", MODEL_NAME)
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        _model.eval()
        log.info("Model ready.")
    return _tokenizer, _model


# ---------------------------------------------------------------------------
# Text cleaning  (mirrors notebook clean_text())
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """
    Preprocess a comment before feeding it to the model.

    Steps (matching notebook exactly):
      1. Cast to string
      2. Strip URLs
      3. Strip @mentions
      4. Strip #hashtags
      5. Convert emojis to :emoji_name: tokens so RoBERTa can read them
      6. Fall back to "no comment" if nothing remains
    """
    
    try:
        import emoji as emoji_lib
    except ImportError:
        raise ImportError(
            "emoji package is not installed.\n"
            "  Run: pip install emoji"
        )

    text = str(text)
    text = re.sub(r'http\S+', '', text)   # strip URLs
    text = re.sub(r'@\w+', '', text)      # strip @mentions
    text = re.sub(r'#\w+', '', text)      # strip #hashtags
    text = emoji_lib.demojize(text)        # ❤️ → :red_heart:
    text = text.strip()
    return text if text else "no comment"


# ---------------------------------------------------------------------------
# Per-comment sentiment scorer  (mirrors notebook get_sentiment_roberta())
# ---------------------------------------------------------------------------

def get_sentiment(text: str) -> dict:
    """
    Run RoBERTa on a single cleaned comment and return sentiment fields.

    Returns:
        {
            polarity:     float  — scores[positive] − scores[negative]
            subjectivity: float  — max(scores), i.e. model confidence
            sentiment:    str    — "negative" | "neutral" | "positive"
        }
    """
    import torch
    import numpy as np

    tokenizer, model = _load_model()

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        outputs = model(**inputs)

    scores = (
        torch.nn.functional.softmax(outputs.logits, dim=1)
        .detach()
        .numpy()[0]
    )   # [neg_score, neu_score, pos_score]

    polarity     = float(scores[2] - scores[0])   # positive − negative
    subjectivity = float(max(scores))             # model confidence
    sentiment    = LABELS[int(scores.argmax())]

    return {
        "polarity":     round(polarity, 4),
        "subjectivity": round(subjectivity, 4),
        "sentiment":    sentiment,
    }


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    total: int
    positive: int
    negative: int
    neutral: int
    output_path: str

    @property
    def positive_pct(self) -> float:
        return 100 * self.positive / self.total if self.total else 0

    @property
    def negative_pct(self) -> float:
        return 100 * self.negative / self.total if self.total else 0

    @property
    def neutral_pct(self) -> float:
        return 100 * self.neutral / self.total if self.total else 0

    def summary_str(self) -> str:
        return (
            f"positive={self.positive} ({self.positive_pct:.1f}%) | "
            f"negative={self.negative} ({self.negative_pct:.1f}%) | "
            f"neutral={self.neutral} ({self.neutral_pct:.1f}%)"
        )


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def analyse(
    csv_path: str,
    output_dir: Optional[str] = None,
) -> SentimentResult:
    """
    Full Stage 3 pipeline: read CSV → clean → classify → add weighted score → write CSV.

    Args:
        csv_path:   Path to the *_relevant_comments.csv from Stage 2.
        output_dir: Where to write the output CSV.
                    Defaults to the same directory as csv_path.

    Returns:
        SentimentResult with counts and output path.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    log.info("Loaded %d comments from %s", len(df), csv_path.name)

    if "text" not in df.columns:
        raise ValueError("CSV must have a 'text' column (output of Stage 2).")

    # --- Step 1: Clean text ---
    log.info("Cleaning comment text…")
    df["clean_text"] = df["text"].apply(clean_text)

    # --- Step 2: Classify (row-by-row, matches notebook) ---
    _load_model()   # warm up once before the loop
    log.info("Running sentiment classification on %d comments…", len(df))

    results = []
    for i, text in enumerate(df["clean_text"], 1):
        results.append(get_sentiment(text))
        if i % 20 == 0 or i == len(df):
            log.info("  %d / %d classified…", i, len(df))

    sentiment_df = pd.DataFrame(results)
    df["polarity"]     = sentiment_df["polarity"]
    df["subjectivity"] = sentiment_df["subjectivity"]
    df["sentiment"]    = sentiment_df["sentiment"]

    # --- Step 3: Weighted sentiment (matches notebook) ---
    df["weighted_sentiment"] = df["polarity"] * df["relevance_score"]

    # --- Step 4: Sort by relevance then polarity ---
    if "relevance_score" in df.columns:
        df = df.sort_values(
            ["relevance_score", "polarity"], ascending=[False, False]
        )

    # --- Step 5: Write output ---
    out_dir = Path(output_dir) if output_dir else csv_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / csv_path.name.replace(
        "_relevant_comments", "_sentiment_comments"
    )

    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    log.info("Enriched CSV written → %s", out_path)

    counts = df["sentiment"].value_counts()
    result = SentimentResult(
        total=len(df),
        positive=int(counts.get("positive", 0)),
        negative=int(counts.get("negative", 0)),
        neutral=int(counts.get("neutral",  0)),
        output_path=str(out_path),
    )

    log.info("Stage 3 complete — %s", result.summary_str())
    return result