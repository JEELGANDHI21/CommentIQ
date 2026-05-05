"""
FastAPI Backend — CommentIQ
"""

import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import pandas as pd

import database as db
from pipeline import run_pipeline
from auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, RegisterRequest, LoginResponse,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

app = FastAPI(title="CommentIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    Path("outputs").mkdir(exist_ok=True)
    await db.init_db()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AnalyseRequest(BaseModel):
    video_url:    str
    max_comments: int   = 300
    threshold:    float = 0.20


class JobResponse(BaseModel):
    job_id:       str
    status:       str
    stage:        Optional[int]  = None
    stage_label:  Optional[str]  = None
    progress_pct: Optional[int]  = None
    error:        Optional[str]  = None
    result:       Optional[dict] = None
    cache_hit:    Optional[bool] = None


# ---------------------------------------------------------------------------
# Auth endpoints (public)
# ---------------------------------------------------------------------------

@app.post("/auth/register", status_code=201)
async def register(req: RegisterRequest):
    if len(req.username.strip()) < 3:
        raise HTTPException(400, "Username must be at least 3 characters.")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")
    ok = await db.create_user(req.username.strip().lower(), hash_password(req.password))
    if not ok:
        raise HTTPException(409, "Username already exists.")
    return {"message": "Account created. You can now log in."}


@app.post("/auth/login", response_model=LoginResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form.username.strip().lower(), form.password)
    if not user:
        raise HTTPException(401, "Incorrect username or password.")
    token = create_access_token(user["username"])
    usage = await db.get_usage(user["username"])
    return LoginResponse(access_token=token, username=user["username"], usage=usage)


@app.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    usage = await db.get_usage(current_user["username"])
    return {
        "username":   current_user["username"],
        "created_at": current_user["created_at"],
        "usage":      usage,
    }


@app.get("/auth/usage")
async def usage(current_user: dict = Depends(get_current_user)):
    return await db.get_usage(current_user["username"])


# ---------------------------------------------------------------------------
# Pipeline endpoints (protected)
# ---------------------------------------------------------------------------

@app.post("/analyse", response_model=JobResponse)
async def start_analysis(
    req: AnalyseRequest,
    current_user: dict = Depends(get_current_user),
):
    # Check + consume one daily request
    await db.check_and_increment(current_user["username"])

    job_id = str(uuid.uuid4())
    await db.create_job(job_id, current_user["username"], req.video_url)

    asyncio.create_task(run_pipeline(
        job_id, current_user["username"],
        req.video_url, req.max_comments, req.threshold,
    ))
    return JobResponse(job_id=job_id, status="queued", progress_pct=0)


@app.get("/status/{job_id}", response_model=JobResponse)
async def get_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
):
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return JobResponse(
        job_id=job_id,
        status=job["status"],
        stage=job["stage"],
        stage_label=job["stage_label"],
        progress_pct=job["progress_pct"],
        error=job["error"] or None,
        result=job.get("result"),
        cache_hit=bool(job["cache_hit"]),
    )


@app.get("/comments/{video_id}")
async def get_comments(
    video_id: str,
    sentiment: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    csv_path = await db.get_comment_file(video_id)
    if not csv_path or not Path(csv_path).exists():
        raise HTTPException(404, "Comments not found.")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    if sentiment:
        df = df[df["sentiment"] == sentiment]
    df = df.nlargest(limit, "weighted_sentiment")
    return df[["author", "text", "sentiment", "polarity", "subjectivity",
               "weighted_sentiment", "like_count", "relevance_score"]].to_dict("records")


@app.get("/history")
async def history(current_user: dict = Depends(get_current_user)):
    """Return the user's last 20 analyses."""
    return await db.get_user_jobs(current_user["username"])


@app.get("/videos/{video_id}/jobs")
async def jobs_for_video(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return all jobs this user has run for a specific video_id."""
    return await db.get_jobs_by_video(video_id, current_user["username"])


@app.get("/health")
async def health():
    return {"status": "ok"}