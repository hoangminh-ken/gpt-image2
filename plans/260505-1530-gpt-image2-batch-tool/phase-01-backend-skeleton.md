---
phase: 1
title: "Backend Skeleton + Mode A"
status: completed
priority: P1
effort: "1d"
dependencies: []
completed: 2026-05-05
smoke_test: "PASS — gift-card ref + product-mockup prompt → 1024x1024 PNG, 68s, $0.0724, 2461 in / 1756 out tokens"
---

# Phase 1: Backend Skeleton + Mode A

## Overview
Stand up FastAPI app with SQLite schema, OpenAI client wrapper, and Mode A (template + ref broadcast) endpoint executed by a synchronous worker. Curl-testable, no UI yet.

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §5, §6, §7

## Requirements

### Functional
- `POST /api/jobs` with Mode A payload: `{name, mode:"template", template_prompt, ref_paths[], output_dir}`
- `GET /api/jobs/{id}` returns job + items list
- `GET /api/jobs` lists all jobs
- `GET /api/preview/{path}` serves generated PNG (path-traversal safe)
- `POST /api/uploads/refs` — multipart upload, accepts 1+ image files, saves to `data/uploads/{date}/{uuid}.png`, returns absolute paths. Powers drag-drop UX in NewJob (Phase 3).
- Worker generates 1 image per ref, calls `client.images.edit(model="gpt-image-2", image=ref, prompt=template_prompt)`
- Persist tokens + cost per item via `response.usage`
- Save outputs to `outputs/{job_id}/{idx}-{slug}.png` (Mode A has no output_name yet)

### Non-Functional
- `.env` for `OPENAI_API_KEY`, gitignored
- All DB writes committed per-item (crash-safe)
- File <200 lines per module

## Architecture

```
backend/app/
├── main.py              # FastAPI factory, lifespan, CORS for localhost:5173
├── config.py            # pydantic-settings, env vars
├── api/
│   ├── jobs.py          # POST/GET endpoints
│   ├── preview.py       # GET /api/preview/{path}
│   └── uploads.py       # POST /api/uploads/refs (drag-drop)
├── core/
│   ├── openai_client.py # wrapper around openai SDK
│   ├── pricing.py       # token → USD calc
│   └── worker_sync.py   # blocking executor (Phase 1 only)
├── db/
│   ├── session.py       # engine, get_db()
│   ├── models.py        # Job, JobItem, CostDaily, Setting
│   └── migrations/      # alembic init
├── parsers/
│   └── template.py      # build items from Mode A payload
└── utils/
    └── slug.py          # prompt → filename slug
```

## Related Code Files

### Create
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/db/session.py`
- `backend/app/db/models.py`
- `backend/app/api/jobs.py`
- `backend/app/api/preview.py`
- `backend/app/api/uploads.py`
- `backend/app/core/openai_client.py`
- `backend/app/core/pricing.py`
- `backend/app/core/worker_sync.py`
- `backend/app/parsers/template.py`
- `backend/app/utils/slug.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/pyproject.toml` (ruff, pytest config)
- `.gitignore` (root)
- `backend/alembic.ini` + initial migration
- `backend/tests/test_jobs_mode_a.py`

### Modify
- `README.md` (root) — add backend setup instructions

## Implementation Steps

1. Init repo: `.gitignore` (data/, outputs/, .env, node_modules/, __pycache__/, *.db)
2. Create `backend/` Python project, install deps:
   ```
   fastapi[standard]>=0.115
   sqlalchemy>=2.0
   alembic
   openai>=1.50
   pillow
   pydantic-settings
   python-multipart
   pytest
   ruff
   ```
3. `config.py`: load `OPENAI_API_KEY`, `DATABASE_URL=sqlite:///data/app.db`, `OUTPUT_DIR=outputs`, `DEFAULT_CONCURRENCY=5`
4. `db/models.py`: SQLAlchemy 2.0 declarative
   - `Job(id PK, name, mode enum, status enum, config_json, created_at, paused_at, completed_at)`
   - `JobItem(id PK, job_id FK, row_idx, prompt, refs_json, output_name nullable, status enum, attempts int default 0, error nullable, output_path nullable, input_tokens int default 0, output_tokens int default 0, cost_usd Numeric(10,6) default 0, started_at, finished_at)`
   - `CostDaily(date PK, source PK, input_tokens, output_tokens, cost_usd)`
   - `Setting(key PK, value)`
5. Alembic init + first revision
6. `core/pricing.py`: `compute_cost(in_tokens, out_tokens, override=None) -> Decimal` using $8/$30 per M defaults
7. `core/openai_client.py`: thin wrapper exposing `edit_image(prompt, ref_path, size, quality) -> {image_b64, usage}`. Reads ref from disk, base64-encodes (or uses file handle for multipart). Auto-resize >2048px via Pillow.
8. `parsers/template.py`: `build_items(template_prompt, ref_paths) -> List[ItemSpec]` — one item per ref, slug from prompt
9. `core/worker_sync.py`: `run_job(job_id)` — load items, loop, call openai_client, write PNG to `outputs/{job_id}/`, update item status+tokens+cost, commit per-item
10. `api/jobs.py`:
    - `POST /api/jobs` — validate payload, insert Job + items, kick off `run_job` in BackgroundTasks
    - `GET /api/jobs` — list with progress counts
    - `GET /api/jobs/{id}` — job + items
11. `api/preview.py` — sanitize path (must start with absolute `OUTPUT_DIR` OR `UPLOAD_DIR`), `FileResponse`
11b. `api/uploads.py` — `POST /api/uploads/refs` accepts `files: List[UploadFile]`, validates content-type (image/*), max 10MB each, max 8 files, saves to `data/uploads/{YYYY-MM-DD}/{uuid}.{ext}`, returns `[{name, path, size}, ...]`. Auto-cleanup files older than 7 days at startup (best-effort).
12. `main.py` — register routers, CORS for `http://localhost:5173`
13. Tests: `tests/test_jobs_mode_a.py` — happy path with mocked openai client (use `respx` or monkey-patch)
14. Run: `uvicorn backend.app.main:app --reload --port 8000`
15. Manual smoke test with `curl -F` against real API (one cheap low-quality 1024×1024 ref)

## Todo List
- [ ] Repo init + .gitignore + backend skeleton
- [ ] requirements.txt + venv install
- [ ] config.py + .env.example
- [ ] DB models + alembic migration
- [ ] pricing.py with unit test
- [ ] openai_client.py with auto-resize
- [ ] template.py parser
- [ ] worker_sync.py executor
- [ ] api/jobs.py endpoints
- [ ] api/preview.py with path-traversal guard
- [ ] api/uploads.py with size/type validation + cleanup-on-startup
- [ ] main.py + CORS
- [ ] Mocked unit tests pass
- [ ] Real-API smoke test (1 image) succeeds

## Success Criteria
- [ ] `curl -X POST /api/jobs` with Mode A payload returns job_id
- [ ] Background task generates ≥1 PNG in `outputs/{job_id}/`
- [ ] `GET /api/jobs/{id}` shows item with `status=done`, `cost_usd>0`, `input_tokens>0`
- [ ] `GET /api/preview/{path}` returns PNG bytes
- [ ] All tests pass under `pytest`
- [ ] No file >200 lines

## Risk Assessment
- **Risk**: openai SDK breaking changes between minor versions → **Mitigation**: pin to `>=1.50,<2.0`, capture wire format in test fixtures
- **Risk**: Path traversal on `/api/preview` → **Mitigation**: resolve to absolute path, assert startswith(OUTPUT_DIR.resolve())
- **Risk**: Large ref images blow up memory → **Mitigation**: Pillow streaming resize before base64
- **Risk**: Decimal vs float cost rounding → **Mitigation**: use `Decimal` end-to-end, store as Numeric(10,6)

## Security Considerations
- API key never logged, never returned in any response
- `.env` gitignored, `.env.example` committed without secrets
- Reject ref paths outside allowed roots (configurable list of safe dirs)

## Next Steps
Phase 2 replaces `worker_sync.py` with async pool + adds retry/pause/resume/WebSocket.
