"""
database.py — SQLite async database layer
==========================================
Replaces:
  - users.json         → users table
  - in-memory jobs dict → jobs table
  - in-memory rate store → users.requests_today / last_reset_date

Uses aiosqlite for async access (non-blocking in FastAPI).
DB file: commentiq.db (auto-created on first run).

Tables:
  users         — auth + per-user rate limiting
  jobs          — pipeline job state (survives restarts)
  reports       — cached pipeline results (by video_id)
  comment_files — CSV paths for /comments endpoint
"""

import json
import logging
import os
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite
from fastapi import HTTPException

log = logging.getLogger(__name__)

DB_PATH      = os.getenv("DB_PATH", "commentiq.db")
CACHE_TTL_DAYS = int(os.getenv("CACHE_TTL_DAYS", 7))   # re-run pipeline after N days


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username        TEXT PRIMARY KEY,
    password        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    daily_limit     INTEGER DEFAULT 10,
    requests_today  INTEGER DEFAULT 0,
    last_reset_date TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    username        TEXT NOT NULL,
    video_id        TEXT DEFAULT '',    -- extracted 11-char YouTube ID
    video_url       TEXT,
    status          TEXT DEFAULT 'queued',
    stage           INTEGER DEFAULT 0,
    stage_label     TEXT DEFAULT '',
    progress_pct    INTEGER DEFAULT 0,
    error           TEXT DEFAULT '',
    result_json     TEXT DEFAULT '',
    created_at      TEXT NOT NULL,
    completed_at    TEXT DEFAULT '',
    cache_hit       INTEGER DEFAULT 0,
    FOREIGN KEY (username) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS reports (
    video_id        TEXT PRIMARY KEY,
    title           TEXT,
    channel         TEXT,
    summary         TEXT,
    result_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comment_files (
    video_id        TEXT PRIMARY KEY,
    csv_path        TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_username ON jobs(username);
CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_video_id ON jobs(video_id);
"""


async def init_db():
    """Create tables if they don't exist. Call once on app startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    log.info("Database initialised — %s", DB_PATH)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at() -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=CACHE_TTL_DAYS)
    return dt.isoformat()


async def _fetchone(query: str, *args) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def _fetchall(query: str, *args) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, args) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def _execute(query: str, *args):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(query, args)
        await db.commit()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

async def get_user(username: str) -> Optional[dict]:
    return await _fetchone("SELECT * FROM users WHERE username = ?", username)


async def create_user(username: str, hashed_password: str) -> bool:
    """Returns False if username already taken."""
    existing = await get_user(username)
    if existing:
        return False
    await _execute(
        "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
        username, hashed_password, _now(),
    )
    log.info("User created: %s", username)
    return True


async def get_all_users() -> list[dict]:
    return await _fetchall("SELECT username, created_at, daily_limit, requests_today FROM users")


async def set_user_limit(username: str, daily_limit: int):
    """Admin: change a user's daily request limit."""
    await _execute(
        "UPDATE users SET daily_limit = ? WHERE username = ?",
        daily_limit, username,
    )


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

async def check_and_increment(username: str) -> dict:
    """
    Check daily limit and increment counter.
    Resets counter automatically on new day.
    Raises HTTP 429 if limit exceeded.
    Returns current usage dict.
    """
    today = date.today().isoformat()
    user  = await get_user(username)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Auto-reset on new day
    if user["last_reset_date"] != today:
        await _execute(
            "UPDATE users SET requests_today = 0, last_reset_date = ? WHERE username = ?",
            today, username,
        )
        user["requests_today"]  = 0
        user["last_reset_date"] = today

    if user["requests_today"] >= user["daily_limit"]:
        reset_at = (datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)).isoformat()
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily limit of {user['daily_limit']} analyses reached. "
                f"Resets at {reset_at} UTC."
            ),
        )

    await _execute(
        "UPDATE users SET requests_today = requests_today + 1 WHERE username = ?",
        username,
    )

    used      = user["requests_today"] + 1
    remaining = user["daily_limit"] - used
    reset_at  = (datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)).isoformat()

    return {
        "used":      used,
        "limit":     user["daily_limit"],
        "remaining": remaining,
        "reset_at":  reset_at,
    }


async def get_usage(username: str) -> dict:
    """Return current usage without incrementing."""
    today = date.today().isoformat()
    user  = await get_user(username)

    if not user:
        return {"used": 0, "limit": 10, "remaining": 10, "reset_at": ""}

    used = user["requests_today"] if user["last_reset_date"] == today else 0
    reset_at = (datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)).isoformat()

    return {
        "used":      used,
        "limit":     user["daily_limit"],
        "remaining": user["daily_limit"] - used,
        "reset_at":  reset_at,
    }


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

async def create_job(job_id: str, username: str, video_url: str, video_id: str = ""):
    await _execute(
        """INSERT INTO jobs (job_id, username, video_id, video_url, status, created_at)
           VALUES (?, ?, ?, ?, 'queued', ?)""",
        job_id, username, video_id, video_url, _now(),
    )


async def get_job(job_id: str) -> Optional[dict]:
    job = await _fetchone("SELECT * FROM jobs WHERE job_id = ?", job_id)
    if job and job.get("result_json"):
        try:
            job["result"] = json.loads(job["result_json"])
        except Exception:
            job["result"] = None
    return job


async def update_job_stage(job_id: str, stage: int, label: str, pct: int):
    await _execute(
        """UPDATE jobs SET stage=?, stage_label=?, progress_pct=?, status='running'
           WHERE job_id=?""",
        stage, label, pct, job_id,
    )


async def complete_job(job_id: str, result: dict, cache_hit: bool = False):
    await _execute(
        """UPDATE jobs SET status='done', progress_pct=100,
           result_json=?, completed_at=?, cache_hit=?
           WHERE job_id=?""",
        json.dumps(result), _now(), int(cache_hit), job_id,
    )


async def fail_job(job_id: str, error: str):
    await _execute(
        "UPDATE jobs SET status='error', error=?, completed_at=? WHERE job_id=?",
        error, _now(), job_id,
    )


async def get_user_jobs(username: str, limit: int = 20) -> list[dict]:
    """Return recent jobs for a user (for history page)."""
    return await _fetchall(
        """SELECT job_id, video_id, video_url, status, stage_label, progress_pct,
                  error, created_at, completed_at, cache_hit
           FROM jobs WHERE username=? ORDER BY created_at DESC LIMIT ?""",
        username, limit,
    )


async def get_jobs_by_video(video_id: str, username: str) -> list[dict]:
    """Return all jobs a user has run for a specific video_id."""
    return await _fetchall(
        """SELECT job_id, video_id, video_url, status, created_at,
                  completed_at, cache_hit
           FROM jobs WHERE video_id=? AND username=?
           ORDER BY created_at DESC""",
        video_id, username,
    )


# ---------------------------------------------------------------------------
# Reports cache
# ---------------------------------------------------------------------------

async def get_cached_report(video_id: str) -> Optional[dict]:
    """Return cached report if it exists and hasn't expired."""
    row = await _fetchone("SELECT * FROM reports WHERE video_id = ?", video_id)
    if not row:
        return None

    # Check expiry
    expires = datetime.fromisoformat(row["expires_at"])
    if datetime.now(timezone.utc) > expires:
        log.info("Cache expired for video %s — will re-run pipeline.", video_id)
        await _execute("DELETE FROM reports WHERE video_id = ?", video_id)
        return None

    log.info("Cache hit for video %s (expires %s)", video_id, row["expires_at"])
    return json.loads(row["result_json"])


async def save_report(video_id: str, title: str, channel: str,
                      summary: str, result: dict):
    """Upsert a report into the cache."""
    await _execute(
        """INSERT INTO reports (video_id, title, channel, summary, result_json, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(video_id) DO UPDATE SET
               result_json=excluded.result_json,
               created_at=excluded.created_at,
               expires_at=excluded.expires_at""",
        video_id, title, channel, summary,
        json.dumps(result), _now(), _expires_at(),
    )
    log.info("Report cached for video %s (TTL %d days)", video_id, CACHE_TTL_DAYS)


# ---------------------------------------------------------------------------
# Comment files
# ---------------------------------------------------------------------------

async def save_comment_file(video_id: str, csv_path: str):
    await _execute(
        """INSERT INTO comment_files (video_id, csv_path, created_at)
           VALUES (?, ?, ?)
           ON CONFLICT(video_id) DO UPDATE SET csv_path=excluded.csv_path""",
        video_id, csv_path, _now(),
    )


async def get_comment_file(video_id: str) -> Optional[str]:
    row = await _fetchone(
        "SELECT csv_path FROM comment_files WHERE video_id = ?", video_id
    )
    return row["csv_path"] if row else None