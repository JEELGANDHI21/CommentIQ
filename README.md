# CommentIQ

> AI-powered YouTube comment sentiment analysis pipeline

## 🖥️ Screenshots

| Home | Result 1 | Result 2 |
|------|-----------|-----------|
| ![Home](screenshots/Home.png) | ![Result1](screenshots/Output1.png) | ![Result2](screenshots/Output2.png) |

---

## What it does

CommentIQ takes any YouTube video URL and runs it through a 4-stage pipeline:

1. **Collect** — Fetches comments via YouTube Data API v3 and generates a video summary using an LLM via OpenRouter
2. **Filter** — Embeds comments and the video summary using `sentence-transformers`, keeps only relevant ones via cosine similarity
3. **Analyse** — Classifies each relevant comment as positive, negative, or neutral using `cardiffnlp/twitter-roberta-base-sentiment-latest`
4. **Report** — Synthesises the sentiment data into an AI-generated report with praise themes, criticism themes, and a final verdict

Results are cached by video ID so re-analysing the same video is instant.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI + Uvicorn |
| Database | SQLite via aiosqlite |
| Auth | JWT + sha256_crypt (passlib) |
| Sentiment model | RoBERTa (cardiffnlp/twitter-roberta-base-sentiment-latest) |
| Embedding model | all-MiniLM-L6-v2 (sentence-transformers) |
| LLM | OpenRouter (any model) |
| Deployment | Docker Compose + Cloudflare Tunnel |

---

## Project structure

```
commentiq/
├── backend/
│   ├── main.py               # FastAPI app + endpoints
│   ├── pipeline.py           # Background job runner
│   ├── database.py           # SQLite layer (users, jobs, reports, cache)
│   ├── auth.py               # JWT authentication
│   ├── stage1_collect.py     # YouTube API + LLM summary
│   ├── stage2_filter.py      # Cosine similarity relevance filter
│   ├── stage3_sentiment.py   # RoBERTa sentiment classifier
│   ├── stage4_summarise.py   # AI report generation
│   ├── llm_client.py         # OpenRouter wrapper
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   │       ├── AuthPage.jsx
│   │       ├── UrlForm.jsx
│   │       ├── ProgressTracker.jsx
│   │       ├── SentimentChart.jsx
│   │       ├── CommentTable.jsx
│   │       └── ReportCard.jsx
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── .env
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker + Docker Compose (for deployment)

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/commentiq.git
cd commentiq
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```env
YOUTUBE_API_KEY=your_youtube_data_api_v3_key
OPENROUTER_API_KEY=sk-or-your_key
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
SECRET_KEY=your_random_secret        # openssl rand -hex 32
DAILY_REQUEST_LIMIT=10
CACHE_TTL_DAYS=7
```

Get your keys:
- YouTube API key → [console.cloud.google.com](https://console.cloud.google.com) → Enable **YouTube Data API v3**
- OpenRouter key → [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Run locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`

### 4. Run with Docker

```bash
docker compose up --build
```

App runs at `http://localhost:3000`

---

## Deployment with Cloudflare Tunnel

Expose your local app publicly for free — no server required.

```bash
# Install cloudflared from https://github.com/cloudflare/cloudflared/releases

# Start the tunnel (keep this terminal open)
cloudflared tunnel --url http://localhost:5173
```

You'll get a public URL like `https://xxxx.trycloudflare.com`.

> **Note:** The URL changes on each restart. For a permanent URL, create a named tunnel with a free Cloudflare account.

---

## API endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | ❌ | Create account |
| `POST` | `/auth/login` | ❌ | Login, returns JWT |
| `GET` | `/auth/me` | ✅ | Current user + usage |
| `GET` | `/auth/usage` | ✅ | Daily request usage |
| `POST` | `/analyse` | ✅ | Start pipeline job |
| `GET` | `/status/{job_id}` | ✅ | Poll job progress |
| `GET` | `/comments/{video_id}` | ✅ | Filtered comments |
| `GET` | `/history` | ✅ | Past analyses |
| `GET` | `/videos/{video_id}/jobs` | ✅ | Jobs for a video |
| `GET` | `/health` | ❌ | Health check |

---

## Features

- **Per-user rate limiting** — configurable daily request limit, resets at midnight UTC, persisted in DB
- **Report caching** — same video analysed twice within 7 days returns instantly from cache
- **Job persistence** — pipeline state survives server restarts (stored in SQLite)
- **Sentiment scoring** — `polarity`, `subjectivity`, and `weighted_sentiment` (polarity × relevance) per comment
- **Relevance filtering** — noise, spam, and off-topic comments are filtered before sentiment analysis

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `YOUTUBE_API_KEY` | ✅ | — | YouTube Data API v3 key |
| `OPENROUTER_API_KEY` | ✅ | — | OpenRouter API key |
| `OPENROUTER_MODEL` | ❌ | `google/gemini-flash-1.5` | LLM model slug |
| `SECRET_KEY` | ✅ | — | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `1440` | Token lifetime (24h) |
| `DAILY_REQUEST_LIMIT` | ❌ | `10` | Max analyses per user per day |
| `DB_PATH` | ❌ | `commentiq.db` | SQLite file path |
| `CACHE_TTL_DAYS` | ❌ | `7` | Days before re-running pipeline |
| `VITE_API_TARGET` | ❌ | `http://localhost:8000` | Backend URL for Vite proxy |

---

