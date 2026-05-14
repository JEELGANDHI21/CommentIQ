import os
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from llm_client import get_client

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

@dataclass
class Comment:
    comment_id: str
    author: str
    text: str
    like_count: int
    reply_count: int
    published_at: str
    updated_at: str
    is_reply: bool = False
    parent_id: Optional[str] = None


@dataclass
class VideoData:
    video_id: str
    title: str
    channel: str
    published_at: str
    description: str
    view_count: int
    like_count: int
    comment_count: int
    video_summary: str            # LLM-generated summary — used by all downstream stages
    comments: list[Comment] = field(default_factory=list)


def extract_video_id(url_or_id: str) -> str:
    """Accept a full YouTube URL or a bare video ID and return the 11-char ID."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, url_or_id)
        if match:
            return match.group(1)
    # Assume it is already a bare ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    raise ValueError(f"Cannot extract a valid video ID from: {url_or_id!r}")


def build_youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


def fetch_video_metadata(youtube, video_id: str) -> dict:
    """Return raw snippet + statistics for a single video."""
    response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()

    items = response.get("items", [])
    if not items:
        raise ValueError(f"No video found for ID: {video_id}")
    return items[0]

def fetch_comments(
    youtube,
    video_id: str,
    max_comments: int = 500,
    include_replies: bool = True,
    order: str = "relevance",       # "relevance" | "time"
) -> list[Comment]:
    """
    Fetch top-level comments and (optionally) their replies.

    Args:
        youtube:         Authorised YouTube API client.
        video_id:        Target video ID.
        max_comments:    Hard cap on total comments collected.
        include_replies: Whether to fetch reply threads too.
        order:           Sort order returned by the API.

    Returns:
        List of Comment dataclass instances.
    """
    comments: list[Comment] = []
    next_page_token: Optional[str] = None

    log.info("Fetching comments for video: %s (max=%d)", video_id, max_comments)

    while len(comments) < max_comments:
        try:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                pageToken=next_page_token,
                order=order,
                textFormat="plainText",
            ).execute()
        except HttpError as exc:
            if exc.resp.status == 403:
                log.warning("Comments disabled or quota exceeded: %s", exc)
                break
            raise

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            thread_id = item["id"]

            comments.append(Comment(
                comment_id=item["snippet"]["topLevelComment"]["id"],
                author=top.get("authorDisplayName", ""),
                text=top.get("textDisplay", ""),
                like_count=int(top.get("likeCount", 0)),
                reply_count=int(item["snippet"].get("totalReplyCount", 0)),
                published_at=top.get("publishedAt", ""),
                updated_at=top.get("updatedAt", ""),
                is_reply=False,
            ))

            # Fetch inline replies (up to 5 included in the thread response)
            if include_replies and item["snippet"].get("totalReplyCount", 0) > 0:
                replies_data = item.get("replies", {}).get("comments", [])
                for reply_item in replies_data:
                    rs = reply_item["snippet"]
                    comments.append(Comment(
                        comment_id=reply_item["id"],
                        author=rs.get("authorDisplayName", ""),
                        text=rs.get("textDisplay", ""),
                        like_count=int(rs.get("likeCount", 0)),
                        reply_count=0,
                        published_at=rs.get("publishedAt", ""),
                        updated_at=rs.get("updatedAt", ""),
                        is_reply=True,
                        parent_id=thread_id,
                    ))

                    if len(comments) >= max_comments:
                        break

            if len(comments) >= max_comments:
                break

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        # Polite delay to stay within quota limits
        time.sleep(0.1)

    log.info("Collected %d comments total.", len(comments))
    return comments


def build_video_summary(title: str, description: str) -> str:
    """
    Generate a rich topic summary using OpenRouter LLM.

    Uses only the video title and description — no transcript required.
    The summary is used by Stage 2 as the reference embedding for
    relevance-matching against comments.

    Falls back to a heuristic excerpt if the LLM call fails.

    Args:
        title:       Video title.
        description: YouTube video description field.

    Returns:
        A 3-5 sentence plain-text summary of the video's topics and themes.
    """
    context_parts = []
    if title:
        context_parts.append(f"Video title: {title}")
    if description:
        context_parts.append(f"Description:\n{description[:1500].strip()}")

    if not context_parts:
        log.warning("No content available to summarise — returning empty summary.")
        return ""

    prompt = (
        "\n\n".join(context_parts) + "\n\n"
        "Write a concise 3–5 sentence summary of what this video is about. "
        "Cover the main topic, key themes, and any notable points. "
        "Plain prose only — no bullet points, no headers."
    )

    system = (
        "You are a video content analyst. Your summaries are factual, neutral, "
        "and rich with topical keywords. They are used to match viewer comments "
        "to the video's subject matter, so precision matters."
    )

    try:
        client = get_client()
        summary = client.chat(prompt=prompt, system=system, max_tokens=300, temperature=0.2)
        log.info("LLM summary generated — %d chars via %s", len(summary), client.model)
        return summary

    except Exception as exc:
        log.warning(
            "LLM summary failed — falling back to heuristic.\n"
            "  Reason: %s\n"
            "  Tip: check your OPENROUTER_API_KEY and OPENROUTER_MODEL in .env",
            exc,
        )
        # Heuristic fallback: first 2 sentences of description
        sentences = re.split(r"(?<=[.!?])\s+", description.strip())
        return f"{title}. " + " ".join(sentences[:2]) if sentences else title


# Main
def collect(
    video_url_or_id: str,
    max_comments: int = 500,
    include_replies: bool = True,
    api_key: str = None,
) -> VideoData:
    """
    Full Stage 1 pipeline: metadata + comments + LLM summary.

    No transcript is fetched — the summary is generated purely from
    the video title and description, which are always available.

    Args:
        video_url_or_id: Full YouTube URL or bare 11-char video ID.
        max_comments:    Maximum number of comments to collect.
        include_replies: Whether to include reply comments.
        api_key:         YouTube Data API v3 key. Falls back to YOUTUBE_API_KEY env var.

    Returns:
        Populated VideoData instance ready for Stage 2.
    """
    api_key = api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "YouTube API key not found. Set YOUTUBE_API_KEY env var or pass api_key=."
        )

    video_id = extract_video_id(video_url_or_id)
    log.info("Starting Stage 1 collection for video ID: %s", video_id)

    youtube = build_youtube_client(api_key)

    # --- Metadata ---
    raw = fetch_video_metadata(youtube, video_id)
    snippet = raw["snippet"]
    stats = raw.get("statistics", {})

    # --- Comments ---
    comments = fetch_comments(
        youtube,
        video_id,
        max_comments=max_comments,
        include_replies=include_replies,
    )

    # --- Summary (title + description → LLM) ---
    video_summary = build_video_summary(
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
    )

    video_data = VideoData(
        video_id=video_id,
        title=snippet.get("title", ""),
        channel=snippet.get("channelTitle", ""),
        published_at=snippet.get("publishedAt", ""),
        description=snippet.get("description", ""),
        view_count=int(stats.get("viewCount", 0)),
        like_count=int(stats.get("likeCount", 0)),
        comment_count=int(stats.get("commentCount", 0)),
        video_summary=video_summary,
        comments=comments,
    )

    log.info(
        "Stage 1 complete — '%s' | %d comments | summary: %d chars",
        video_data.title,
        len(video_data.comments),
        len(video_data.video_summary),
    )
    return video_data