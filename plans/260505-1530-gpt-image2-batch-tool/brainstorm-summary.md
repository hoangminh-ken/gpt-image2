---
title: GPT-Image-2 Batch Generator — Brainstorm Summary
date: 2026-05-05
status: approved
type: brainstorm
next: /ck:plan
---

# GPT-Image-2 Batch Generator — Brainstorm Summary

## 1. Problem Statement

Build local-only batch image generator using OpenAI `gpt-image-2`. User supplies reference images + prompts, tool fans out concurrent API calls, persists progress/cost, exposes web dashboard for preview/control.

## 2. Requirements (Approved)

### Functional
- Use `gpt-image-2` via `/v1/images/edits` (multi-ref support)
- **Mode A** — template prompt + list refs → broadcast (1 ref + template = 1 output)
- **Mode B** — Excel import: rows of `prompt | refs (pipe-delimited) | output_name (optional)`
- Progress tracking, retry (exponential backoff), pause (soft — finish in-flight, no new dequeue), resume, cancel
- Cost dashboard: real-time local + daily reconcile vs OpenAI Usage API
- Output naming: from Excel column OR user-defined template fallback `{row_idx}-{slug}.png`

### Non-Functional
- Local web app, single-user, no auth, `.env` for API key
- Concurrency default 5, configurable
- PNG output only (KISS)
- SQLite + filesystem persistence (resume after crash/restart)
- Real-time UI via WebSocket

## 3. Tech Stack (Approved)

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite, openai-python SDK, asyncio worker pool
- **Frontend**: React 18 + Vite + TypeScript, TanStack Query, Tailwind (or shadcn/ui)
- **Tooling**: pytest, ruff, eslint, prettier

## 4. Evaluated Approaches

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| CLI + HTML report | Simplest, no server | Pause/resume UX kém, no live preview | Rejected |
| Pure CLI/TUI | Lightweight | No visual preview cho ảnh | Rejected |
| Electron desktop | Distributable .exe | Build nặng, dev complexity | Rejected |
| **Local web (FastAPI + React)** | Web preview tốt, async worker decoupled, real-time WS | Cần chạy 2 process | **Selected** |
| Python CLI + Streamlit | Ít code | Hạn chế khi job chạy nền + control granular | Rejected |
| Node full-stack | Type-safe end-to-end | openai-python SDK ổn định hơn cho image | Rejected |

## 5. Final Architecture

```
Browser (React/Vite) ◄── HTTP/WS ──► FastAPI server
                                          │
                                ┌─────────┴────────┐
                                ▼                  ▼
                      Async Worker Pool        SQLite (jobs/items/cost_daily)
                      (Semaphore=5)
                                │
                                ▼
                      OpenAI images.edit + Usage API
                                │
                                ▼
                      outputs/{job_id}/...png
```

### Data model (SQLite)
- `jobs(id, name, mode, status, config_json, created_at, paused_at, completed_at)`
- `job_items(id, job_id, row_idx, prompt, refs_json, output_name, status, attempts, error, output_path, input_tokens, output_tokens, cost_usd, started_at, finished_at)`
- `cost_daily(date, source[local|openai], input_tokens, output_tokens, cost_usd)`
- `settings(key, value)` — API key ref, concurrency, pricing override

### Item state machine
```
pending → queued → running → done
                     ↓
                  failed_retryable → (backoff 1→2→4→8→16s, max 5) → retrying
                     ↓
                  failed_permanent (4xx non-rate-limit)
```

### Retry policy
- Retry on: HTTP 429, 5xx, network timeout, OpenAI `server_error`
- Don't retry: 400 invalid prompt, 401 auth, 413 payload too large, malformed input
- Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s

### Pause/Resume semantics
- Pause: `jobs.status='paused'` → workers stop dequeuing, in-flight requests finish (already billed)
- Resume: re-enqueue `status IN ('pending','failed_retryable')`
- Restart safety: on boot, mark `running` items as `failed_retryable` for resume

### Cost tracking
- **Local (real-time)**: parse `response.usage.input_tokens` + `output_tokens` per call → `cost_usd = (in×$8 + out×$30)/1M` → write to `job_items` + aggregate to `cost_daily(source='local')`
- **Reconcile**: manual button "Sync OpenAI Usage" → call `GET /v1/organization/usage/images?bucket_width=1d` → write `cost_daily(source='openai')` → dashboard shows drift %
- **Pricing override**: `settings` key for when OpenAI changes prices

### API surface (FastAPI)
```
POST   /api/jobs                  # Create (Mode A or B payload)
GET    /api/jobs                  # List
GET    /api/jobs/{id}             # Detail + items
POST   /api/jobs/{id}/pause
POST   /api/jobs/{id}/resume
POST   /api/jobs/{id}/cancel
POST   /api/jobs/{id}/items/{rid}/retry
GET    /api/cost                  # Aggregated cost
POST   /api/cost/reconcile        # Pull from OpenAI Usage API
GET    /api/settings
PUT    /api/settings
GET    /api/preview/{path}        # Serve generated PNG
WS     /ws/jobs/{id}              # Real-time progress
```

## 6. Project Structure

```
gpt-image2/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/{jobs,cost,settings,ws}.py
│   │   ├── core/{worker,openai_client,retry,pricing}.py
│   │   ├── db/{models,migrations}/
│   │   ├── parsers/{excel,template}.py
│   │   └── config.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/{Dashboard,NewJob,JobDetail,Cost,Settings}.tsx
│   │   ├── components/{ItemTable,CostChart,JobControls}.tsx
│   │   ├── hooks/{useJob,useWebSocket,useCost}.ts
│   │   └── api/client.ts
│   ├── vite.config.ts
│   └── package.json
├── outputs/              # gitignored
├── data/
│   ├── app.db            # gitignored
│   └── inputs/
├── docs/
│   ├── project-overview-pdr.md
│   ├── system-architecture.md
│   └── code-standards.md
├── plans/
└── README.md
```

Modularization rule: keep each file <200 lines. Split worker into `worker.py` (pool) + `executor.py` (per-item) if needed.

## 7. Implementation Phasing

| Phase | Deliverable |
|-------|-------------|
| 1 | Backend skeleton: FastAPI + SQLite schema + Mode A endpoint, sync worker, curl-testable |
| 2 | Async worker pool, retry/backoff, pause/resume, WebSocket progress |
| 3 | Frontend MVP: Dashboard + NewJob (Mode A) + JobDetail with live progress |
| 4 | Mode B: Excel parser + validation UI + multi-ref handling |
| 5 | Cost reconcile: OpenAI Usage API client + drift indicator on dashboard |
| 6 | Polish: Settings page, pricing override, ref image resize helper, README |

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| 4K ref images blow up input tokens | Pillow auto-resize ≤2048px (configurable in settings); UI warning if larger |
| Excel paths break across machines | Support relative paths from Excel folder; pre-validate before run |
| Crash mid-batch | SQLite committed per item; restart resumes from `pending`/`failed_retryable` |
| 429 rate-limit cascade | Semaphore + backoff with jitter; configurable concurrency |
| Pricing drift / new model | `settings.pricing_override_json`; both local+OpenAI cost shown for sanity check |
| API key leak | `.env` gitignored; UI shows masked key; "test key" button |

## 9. Success Criteria

- Run 100-row Excel batch end-to-end without manual intervention
- Pause + restart server + resume — no duplicate API calls, no lost rows
- Local cost USD within ±2% of OpenAI Usage API for completed batch
- Time-to-first-output (TTFO) under 30s after job submit
- Failed row retry from UI works in 1 click
- Dashboard updates within 1s of API response (WebSocket)

## 10. Decisions Locked

| # | Decision |
|---|----------|
| 1 | Form factor: Local web app (FastAPI + React/Vite) |
| 2 | Stack: Python backend, TypeScript frontend |
| 3 | Pairing modes: A (template broadcast) + B (Excel row-based, `\|`-delimited refs) |
| 4 | Cost: dual-source (local real-time + OpenAI reconcile) |
| 5 | Concurrency: default 5, configurable |
| 6 | Output naming: Excel column OR `{row_idx}-{slug}.png` fallback |
| 7 | Pause: soft (finish in-flight) |
| 8 | API key: `.env` only |
| 9 | Auth: none (single-user localhost) |
| 10 | Output format: PNG only (KISS) |

## 11. Out of Scope (Explicit)

- Multi-user / authentication
- Cloud deployment (Docker/K8s)
- JPEG/WebP/AVIF output
- Image post-processing (upscale, watermark)
- Webhook notifications
- Distributed worker (single-process async pool sufficient)

## 11b. Follow-up Decisions (Post-Brainstorm)

- **Mode A ref input** = Hybrid (paste textarea + drag-drop drop zone). Drop zone uploads via `POST /api/uploads/refs` → server returns absolute path → unified `paths[]` state.
- **Dev workflow** = root `npm run dev` (concurrently runs uvicorn + vite with `[api]`/`[web]` prefixes). 2-terminal fallback documented in README.
- **ZIP export** = ADDED to Phase 6 (`GET /api/jobs/{id}/export.zip` streamed, includes `manifest.json` with prompt/refs/cost per item).

## 12. Next Step

Invoke `/ck:plan` with this summary as context to produce phase-by-phase implementation plan with todo lists.
