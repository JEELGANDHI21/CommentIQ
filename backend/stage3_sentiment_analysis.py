"""
Stage 3 — Sentiment Analysis
==============================
Model: SamLowe/roberta-base-go_emotions (28 emotion labels)
Slang: Gen Z normalization layer before model inference
Output: emotion, polarity, subjectivity, sentiment, weighted_sentiment
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)

MODEL_NAME = "SamLowe/roberta-base-go_emotions"
_pipeline  = None


# ---------------------------------------------------------------------------
# Emotion → sentiment + polarity mapping
# ---------------------------------------------------------------------------

EMOTION_TO_SENTIMENT = {
    "admiration":      "positive",
    "amusement":       "positive",    # "killed me", "i'm dead 💀"
    "approval":        "positive",
    "caring":          "positive",
    "desire":          "positive",
    "excitement":      "positive",    # "holy shit he's back"
    "gratitude":       "positive",
    "joy":             "positive",
    "love":            "positive",
    "optimism":        "positive",
    "pride":           "positive",
    "relief":          "positive",
    "neutral":         "neutral",
    "realization":     "neutral",
    "surprise":        "neutral",
    "curiosity":       "neutral",
    "confusion":       "neutral",
    "anger":           "negative",
    "annoyance":       "negative",
    "disappointment":  "negative",
    "disapproval":     "negative",
    "disgust":         "negative",
    "embarrassment":   "negative",
    "fear":            "negative",
    "grief":           "negative",
    "nervousness":     "negative",
    "remorse":         "negative",
    "sadness":         "negative",
}

EMOTION_POLARITY = {
    "admiration": 0.85, "amusement": 0.80, "approval": 0.75,
    "caring": 0.70, "desire": 0.65, "excitement": 0.90,
    "gratitude": 0.85, "joy": 0.90, "love": 0.95,
    "optimism": 0.75, "pride": 0.80, "relief": 0.65,
    "neutral": 0.00, "realization": 0.05, "surprise": 0.10,
    "curiosity": 0.15, "confusion": -0.05,
    "anger": -0.85, "annoyance": -0.60, "disappointment": -0.75,
    "disapproval": -0.70, "disgust": -0.85, "embarrassment": -0.55,
    "fear": -0.70, "grief": -0.90, "nervousness": -0.50,
    "remorse": -0.65, "sadness": -0.80,
}


# ---------------------------------------------------------------------------
# Gen Z slang normalization
# ---------------------------------------------------------------------------

SLANG_PATTERNS = [
    # ── Emotional / sentimental language (misread as negative by model) ──
    (r"\blife\s+hits?\s+hard\b",                    "during difficult times"),
    (r"\bhits?\s+hard\b",                           "is very impactful and moving"),
    (r"\bin\s+tears\b",                             "deeply moved and emotional"),
    (r"\bmakes?\s+me\s+(feel\s+)?emotional\b",      "moves me deeply"),
    (r"\brun\s+to\s+your\s+videos\b",               "always come back to your videos for comfort"),
    (r"\bpeace\s+for\s+me\b",                       "very comforting for me"),
    (r"\bsufficient\s+to\s+make\s+me\b",            "enough to make me"),
    (r"\bdon'?t\s+know\s+why\s+but\b",             "somehow"),
    (r"\b(whenever|when)\s+life\b",                 "during hard times"),
    (r"\bmakes?\s+me\s+cry\b",                      "moves me deeply"),
    (r"\bcried\b",                                  "was deeply moved"),
    (r"\bgives?\s+me\s+(chills|goosebumps)\b",      "is incredibly powerful"),
    (r"\btherapy\b",                                "very comforting content"),
    (r"\bheals?\s+(me|my\s+soul)\b",               "is very comforting"),
    (r"\btouched\s+my\s+(heart|soul)\b",            "deeply moved me"),
    (r"\bbrings?\s+me\s+(back|comfort|peace)\b",    "is very comforting"),
    (r"\bmissed\s+you\b",                           "glad you are back"),
    (r"\bproud\s+of\s+you\b",                       "very impressed and supportive"),

    # ── Gen Z death/kill as extreme positive reactions ────────────────────
    (r"\bfirst\s+\w+\s+(secs?|seconds?|mins?)\s+killed\s+me\b", "the beginning was amazing"),
    (r"\b(this|it|that)\s+killed\s+me\b",      "this made me laugh so much"),
    (r"\bkilled\s+it\b",                        "performed excellently"),
    (r"\b(already\s+)?killed\s+me\b",           "made me laugh so much"),
    (r"\bi'?m\s+dead\b",                        "i found this hilarious"),
    (r"\b(literally\s+)?dying\b",               "laughing so much"),
    (r"\bslayed\b",                             "performed excellently"),

    # ── Skill / quality ───────────────────────────────────────────────────
    (r"\bcracked\b",                            "extremely skilled"),
    (r"\bgoated?\b",                            "greatest of all time"),
    (r"\bbusted\b",                             "impressively broken"),
    (r"\bactually\s+back\b",                    "has returned impressively"),
    (r"\bno\s+way\s+he\s+actually\b",           "it is incredible that he"),
    (r"\bactually\s+cooked\b",                  "performed amazingly"),

    # ── Positive slang ────────────────────────────────────────────────────
    (r"\bW\s+video\b",                          "great video"),
    (r"\b(big\s+)?W\b",                         "great"),
    (r"\bthis\s+slaps\b",                       "this is excellent"),
    (r"\b(actually\s+)?slaps\b",                "is excellent"),
    (r"\bfires?\b(?!\s+(bad|terrible|awful))",  "excellent"),
    (r"\bsick\b(?!\s+(of|and|with))",           "impressive"),
    (r"\bhard\s+carry\b",                       "dominant performance"),
    (r"\bno\s+cap\b",                           "honestly"),
    (r"\bon\s+god\b",                           "seriously"),
    (r"\bfrfr\b",                               "for real"),
    (r"\bngl\b",                                "not going to lie"),
    (r"\bits?\s+(giving|hitting)\b",            "it feels like"),
    (r"\bslay(ing)?\b",                         "performing excellently"),
    (r"\bperiodt?\b",                           "definitely"),
    (r"\bsheesh\b",                             "wow that is impressive"),
    (r"\bbussin\b",                             "excellent"),
    (r"\bhit\s+different\b",                    "feels special"),
    (r"\bsend(ing)?\s+(me|it)\b",              "making me laugh"),
    (r"\bcant?\s+breathe\b",                    "laughing so hard"),

    # ── Negative slang ────────────────────────────────────────────────────
    (r"\bL\s+take\b",                           "bad opinion"),
    (r"\b(big\s+)?L\b",                         "loss or failure"),
    (r"\btrash\b",                              "bad"),
    (r"\bdogwater\b",                           "very bad"),
    (r"\bcooked\b(?!\s+amazingly)",             "in a bad situation"),
    (r"\bration(ed)?\b",                        "criticized"),

    # ── Intensity amplifiers ──────────────────────────────────────────────
    (r"\binsane(ly)?\b",                        "incredibly impressive"),
    (r"\bcraz(y|ily)\s+good\b",                "extremely good"),
    (r"\bactually\s+insane\b",                 "genuinely incredible"),
    (r"\bholy\s+shit\b",                        "wow"),
    (r"\bwtf\b",                               "wow"),
    (r"\bomg\b",                               "oh my god"),
    (r"\blmao\b",                              "this is very funny"),
    (r"\blmfao\b",                             "this is hilarious"),
    (r"\blol\b",                               "this is funny"),
    (r"\bgoat\b",                              "greatest of all time"),
    (r"\bimo\b",                               "in my opinion"),
]

_COMPILED_SLANG = [
    (re.compile(pat, re.IGNORECASE), repl)
    for pat, repl in SLANG_PATTERNS
]


def normalize_slang(text: str) -> str:
    for pattern, replacement in _COMPILED_SLANG:
        text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# Positive emoji override
# ---------------------------------------------------------------------------

# These emojis — when present — almost always signal positive or emotional-positive
# intent, even when the surrounding text seems sad or negative to the model.
# 😭 and 🥹 in internet culture = overwhelmed with positive emotion, NOT sad.
POSITIVE_OVERRIDE_EMOJIS = {
    ":red_heart:", ":orange_heart:", ":yellow_heart:",
    ":green_heart:", ":blue_heart:", ":purple_heart:",
    ":white_heart:", ":brown_heart:", ":black_heart:",
    ":revolving_hearts:", ":two_hearts:", ":heart_decoration:",
    ":sparkling_heart:", ":growing_heart:", ":beating_heart:",
    ":heart_with_arrow:", ":heart_with_ribbon:",
    ":smiling_face_with_3_hearts:",      # 🥰
    ":smiling_face_with_heart-eyes:",    # 😍
    ":face_holding_back_tears:",         # 🥹 Gen Z = overwhelmed positive
    ":loudly_crying_face:",              # 😭 internet = so good it hurts
    ":pleading_face:",                   # 🥺
    ":folded_hands:",                    # 🙏 = gratitude
    ":star-struck:",                     # 🤩
    ":fire:",                            # 🔥
    ":crown:",                           # 👑
}


def apply_emoji_override(clean_text: str, result: dict) -> dict:
    """
    If a comment contains strong positive emojis but was classified negative,
    override to neutral minimum.

    Rationale: 😭❤️🥹 are almost universally used as positive signals in
    internet/South Asian/Gen Z comment culture. The model was not trained on
    this usage pattern and consistently misreads them.
    """
    if result["sentiment"] != "negative":
        return result

    has_positive_emoji = any(e in clean_text for e in POSITIVE_OVERRIDE_EMOJIS)
    if has_positive_emoji:
        log.debug(
            "Emoji override: flipping '%s' from negative → neutral (had positive emoji)",
            clean_text[:60],
        )
        result["sentiment"] = "neutral"
        result["polarity"]  = round(abs(result["polarity"]) * 0.3, 4)
        result["emotion"]   = "realization"   # most neutral fallback emotion
    return result


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    try:
        import emoji as emoji_lib
    except ImportError:
        raise ImportError("Run: pip install emoji")

    text = str(text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+',    '', text)
    text = re.sub(r'#\w+',    '', text)
    text = normalize_slang(text)            # Gen Z slang normalization
    text = emoji_lib.demojize(text)         # ❤️ → :red_heart:
    text = text.strip()
    return text if text else "no comment"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline as hf_pipeline
        except ImportError:
            raise ImportError("Run: pip install transformers torch")
        log.info("Loading '%s' (first run ~500 MB)…", MODEL_NAME)
        _pipeline = hf_pipeline(
            task="text-classification",
            model=MODEL_NAME,
            top_k=None,
            truncation=True,
            max_length=512,
        )
        log.info("Model ready.")
    return _pipeline


def get_sentiment(text: str) -> dict:
    import torch
    import torch.nn.functional as F

    classifier = _get_pipeline()
    inputs = classifier.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        outputs = classifier.model(**inputs)

    scores_tensor = F.softmax(outputs.logits, dim=1).detach()[0]
    id2label      = classifier.model.config.id2label
    score_dict    = {id2label[i]: float(scores_tensor[i]) for i in range(len(scores_tensor))}

    top_emotion = max(score_dict, key=score_dict.__getitem__)
    confidence  = score_dict[top_emotion]
    sentiment   = EMOTION_TO_SENTIMENT.get(top_emotion, "neutral")
    polarity    = EMOTION_POLARITY.get(top_emotion, 0.0) * confidence

    result = {
        "emotion":      top_emotion,
        "polarity":     round(polarity, 4),
        "subjectivity": round(confidence, 4),
        "sentiment":    sentiment,
    }

    # Apply emoji override AFTER model inference
    # (clean_text already has emojis converted to :emoji_name: tokens)
    result = apply_emoji_override(text, result)
    return result


# ---------------------------------------------------------------------------
# Result + main
# ---------------------------------------------------------------------------

@dataclass
class SentimentResult:
    total: int; positive: int; negative: int; neutral: int; output_path: str

    @property
    def positive_pct(self): return 100 * self.positive / self.total if self.total else 0
    @property
    def negative_pct(self): return 100 * self.negative / self.total if self.total else 0
    @property
    def neutral_pct(self):  return 100 * self.neutral  / self.total if self.total else 0

    def summary_str(self):
        return (f"positive={self.positive} ({self.positive_pct:.1f}%) | "
                f"negative={self.negative} ({self.negative_pct:.1f}%) | "
                f"neutral={self.neutral} ({self.neutral_pct:.1f}%)")


def analyse(csv_path: str, output_dir: Optional[str] = None) -> SentimentResult:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    log.info("Loaded %d comments from %s", len(df), csv_path.name)

    if "text" not in df.columns:
        raise ValueError("CSV must have a 'text' column.")

    log.info("Cleaning and normalising…")
    df["clean_text"] = df["text"].apply(clean_text)

    _get_pipeline()
    log.info("Classifying %d comments with go_emotions…", len(df))

    results = []
    for i, text in enumerate(df["clean_text"], 1):
        results.append(get_sentiment(text))
        if i % 20 == 0 or i == len(df):
            log.info("  %d / %d…", i, len(df))

    sdf = pd.DataFrame(results)
    df["emotion"]      = sdf["emotion"]
    df["polarity"]     = sdf["polarity"]
    df["subjectivity"] = sdf["subjectivity"]
    df["sentiment"]    = sdf["sentiment"]

    df["weighted_sentiment"] = df["polarity"] * df["relevance_score"]

    if "relevance_score" in df.columns:
        df = df.sort_values(["relevance_score", "polarity"], ascending=[False, False])

    out_dir  = Path(output_dir) if output_dir else csv_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / csv_path.name.replace("_relevant_comments", "_sentiment_comments")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    log.info("Written → %s", out_path)

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