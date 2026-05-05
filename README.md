# gpt-image2 — Batch Image Generator

Local web app that batches image generation via OpenAI `gpt-image-2`. Upload reference images + a prompt (or an Excel sheet), kick off a job, watch live progress in the browser, and pay-as-you-go cost tracking via the OpenAI Usage API.

> **Scope:** single-user, localhost-only. No auth. PNG output. Designed for personal/internal batches.

## Features

- **Two input modes**
  - **A — Template + refs broadcast**: one prompt × N reference images = N outputs
  - **B — Excel batch**: rows of `prompt | refs | output_name` (multi-ref via `|`)
- **Async worker pool** (default concurrency 5, configurable)
- **Retry policy**: exponential backoff on 429/5xx, permanent fail on 4xx (max 5 attempts)
- **Pause / Resume / Cancel** per job; **Retry** per failed item
- **Live updates** via WebSocket (per-item state pushed to UI)
- **Crash recovery**: on restart, in-flight items are re-queued automatically
- **Cost dashboard**: real-time local cost from `response.usage` + reconcile against OpenAI Usage API (drift indicator)
- **ZIP export**: one-click download of all completed images + `manifest.json`
- **Hybrid ref input**: paste paths OR drag-drop image files

## Stack

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite, openai SDK, Pillow
- **Frontend**: React 19 + Vite + TypeScript + Tailwind v4 + TanStack Query + react-router

## Prerequisites

- Python 3.10+ and `python -m venv` available
- Node.js 20+
- An OpenAI API key with `gpt-image-2` access
- *(Optional)* OpenAI org admin key for cost reconcile against Usage API

## Quick start

```bash
# 1. clone, then from project root:
npm run install:all      # creates backend/.venv, installs deps, runs npm install in frontend/

# 2. configure key
cp backend/.env.example backend/.env
# edit backend/.env and paste your OPENAI_API_KEY=sk-...

# 3. start both servers
npm run dev              # → backend on :8765, frontend on :5173 (concurrently)
```

Open <http://localhost:5173>.

If `npm run dev` produces tangled logs, run them in two terminals instead:

```bash
# terminal 1
cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8765

# terminal 2
cd frontend && npm run dev
```

## Usage

### Mode A — Template + reference broadcast

1. Click **New Job → Mode A**
2. Enter a job name + prompt template
3. Add reference images (paste absolute paths or drag-drop files into the upload zone)
4. Click **Create Job** — generation starts immediately
5. Live progress on the Job Detail page; click items to see thumbnails

### Mode B — Excel batch

Excel format (`.xlsx`):

| prompt | refs | output_name |
|--------|------|-------------|
| anime portrait, blue hair | `C:/refs/a.png\|C:/refs/b.png` | hero_01.png |
| cyberpunk city night | `C:/refs/city.png` | _(blank for auto)_ |

- **Required columns**: `prompt`, `refs`
- **Optional column**: `output_name` (no slashes, no `..`)
- **Multi-ref separator**: `|` (max 8 refs/row)
- **Max**: 1000 rows, 10MB file size

1. Click **New Job → Mode B**
2. Upload `.xlsx` → see per-row validation in preview table
3. Toggle **Skip invalid** if some rows fail validation
4. Click **Create Job**

### Cost tracking

- **Local** (real-time): every API response's `input_tokens`/`output_tokens` × tier pricing → aggregated to `cost_daily(source='local')`
- **OpenAI Usage API** (manual sync): click **Sync OpenAI Usage** on the Cost page (requires `OPENAI_ADMIN_KEY` with org admin scope)
- **Drift indicator**: green ≤5%, amber 5-15%, rose >15%

### ZIP export

On any job with ≥1 completed item, click **Download ZIP**. The archive contains all PNGs plus `manifest.json` with per-item prompt/refs/cost.

## Configuration

All config lives in `backend/.env`:

```ini
OPENAI_API_KEY=sk-...                    # required
OPENAI_ADMIN_KEY=                        # optional, for /api/cost/reconcile
DATABASE_URL=sqlite:///data/app.db       # default
OUTPUT_DIR=outputs                       # generated images
UPLOAD_DIR=data/uploads                  # drag-drop ref images
DEFAULT_CONCURRENCY=5                    # parallel API calls
MAX_REF_DIMENSION=2048                   # auto-resize refs >2048px
HOST=127.0.0.1
PORT=8000
```

Visit **Settings** in the UI to view (read-only) current config + test the API key.

## Project layout

```
gpt-image2/
├── backend/             # FastAPI server
│   ├── app/
│   │   ├── api/         # jobs, preview, uploads, ws, cost, settings, exports
│   │   ├── core/        # worker_pool, executor, retry_policy, openai_client, pricing, ws_broker, usage_api
│   │   ├── db/          # SQLAlchemy models + session
│   │   ├── parsers/     # template (Mode A), excel (Mode B)
│   │   ├── utils/       # slug, store_path
│   │   ├── config.py    # pydantic-settings
│   │   └── main.py      # FastAPI factory + lifespan (boots WorkerPool)
│   ├── tests/           # pytest, 44 tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/            # React + Vite + TS
│   ├── src/
│   │   ├── api/         # client, jobs, cost
│   │   ├── components/  # JobsTable, ItemRow, RefInputHybrid, etc.
│   │   ├── hooks/       # useJob, useJobs, useJobWs, useCost
│   │   ├── pages/       # Dashboard, NewJob, JobDetail, Cost, Settings
│   │   └── lib/         # format, status
│   └── vite.config.ts   # proxy /api + /ws → 127.0.0.1:8765
├── data/                # SQLite DB + uploads (gitignored)
├── outputs/             # generated PNGs (gitignored)
├── plans/               # implementation plans
├── package.json         # root: concurrently dev script
└── README.md
```

## Development

```bash
# run backend tests (44 tests)
npm run test:api

# build frontend (production bundle)
npm run build:web

# lint backend
cd backend && .venv/Scripts/python -m ruff check app/ tests/
```

## Troubleshooting

**Rate limit (429) keeps occurring**
Lower `DEFAULT_CONCURRENCY` to 2-3 in `backend/.env` and restart.

**`OPENAI_API_KEY not configured`**
Make sure `backend/.env` exists (not just `.env.example`) and contains a valid key. Restart the backend.

**ZIP download is empty**
ZIP only includes items with `status=done`. Failed items are excluded.

**Reconcile button disabled**
Set `OPENAI_ADMIN_KEY` in `backend/.env`. Note this is *different* from the inference key — it requires org admin scope.

**Excel paths don't resolve**
Use **absolute** paths in the Excel `refs` column. Backslashes (`\`) and forward slashes (`/`) both work on Windows.

**Server won't start: port in use**
Default is 8765 (backend) and 5173 (frontend). Change via `PORT=` in `backend/.env` or `--port` flag in `vite.config.ts`.

## Pricing reference

Per OpenAI (May 2026):
- Input tokens: $8.00 / 1M
- Output tokens: $30.00 / 1M

Approximate per-image cost for medium 1024×1024 with one reference image: **~$0.07**.

## Out of scope (intentional)

- Multi-user / authentication
- Cloud deployment (Docker/K8s)
- JPEG/WebP output (PNG only)
- Image post-processing (upscale, watermark)
- Webhook notifications
- Distributed worker (single-process async pool is sufficient at single-user scale)

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Backend skeleton + Mode A | ✅ |
| 2 | Async worker + retry/pause/resume + WebSocket | ✅ |
| 3 | Frontend (Dashboard + NewJob + JobDetail) | ✅ |
| 4 | Mode B Excel parser | ✅ |
| 5 | Cost reconcile + Usage API | ✅ |
| 6 | Polish: Settings + ZIP export + README | ✅ |
