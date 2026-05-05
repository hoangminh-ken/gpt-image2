---
phase: 2
title: "Async Worker + Retry/Pause/Resume + WebSocket"
status: completed
priority: P1
effort: "1.5d"
dependencies: [1]
completed: 2026-05-05
smoke_test: "PASS — 2 concurrent items (~73s vs 140s sequential), total $0.1447, retry/pause/cancel endpoints verified via 31 unit tests"
---

# Phase 2: Async Worker + Retry/Pause/Resume + WebSocket

## Overview
Replace blocking worker with `asyncio` pool (Semaphore=N), add exponential-backoff retry, soft pause (finish in-flight), resume from DB on server restart, and WebSocket channel for real-time per-item status updates.

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §3, §5
- [phase-01-backend-skeleton.md](./phase-01-backend-skeleton.md)

## Requirements

### Functional
- `POST /api/jobs/{id}/pause` → set status `paused`, workers stop dequeuing
- `POST /api/jobs/{id}/resume` → re-enqueue items in `pending|failed_retryable`
- `POST /api/jobs/{id}/cancel` → mark `cancelled`, cancel pending only
- `POST /api/jobs/{id}/items/{rid}/retry` → reset attempts, mark pending, enqueue
- `WS /ws/jobs/{id}` → push `{type: "item_update", item: {...}}` on each state change
- Server restart resumes any `running` job: in-flight items → `failed_retryable`, then re-enqueue

### Non-Functional
- Concurrency configurable via `Settings` table key `concurrency` (default 5)
- Retry backoff: 1s, 2s, 4s, 8s, 16s with ±25% jitter, max 5 attempts
- Retry only on: HTTP 429, 500-599, network timeout, OpenAI `server_error`
- No retry on: 400, 401, 403, 413, validation errors
- Per-item DB commit before WS broadcast (consistency)

## Architecture

```
backend/app/core/
├── worker_pool.py      # WorkerPool: asyncio.Queue + Semaphore + N tasks
├── executor.py         # async run_item(item_id): retry loop + DB updates
├── retry_policy.py     # is_retryable(exc), backoff(attempt) -> seconds
└── ws_broker.py        # in-memory pub/sub: subscribe(job_id), publish(...)

backend/app/api/
├── jobs.py             # add pause/resume/cancel/retry endpoints
└── ws.py               # WebSocket endpoint /ws/jobs/{id}
```

### State machine (item-level)
```
pending → queued → running → done
                     ↓ (transient error)
                  failed_retryable → (sleep backoff) → queued
                     ↓ (max attempts OR non-retryable)
                  failed_permanent
                     ↑
                  retry button → pending
```

### Pool lifecycle
- App startup: scan jobs `WHERE status='running'` → mark in-flight items `failed_retryable`, enqueue items `WHERE status IN ('pending','failed_retryable')`
- Shutdown: signal pool stop, await drain (configurable `SHUTDOWN_TIMEOUT=60s`)

## Related Code Files

### Create
- `backend/app/core/worker_pool.py`
- `backend/app/core/executor.py`
- `backend/app/core/retry_policy.py`
- `backend/app/core/ws_broker.py`
- `backend/app/api/ws.py`
- `backend/tests/test_retry_policy.py`
- `backend/tests/test_worker_pool.py`
- `backend/tests/test_pause_resume.py`

### Modify
- `backend/app/main.py` — lifespan starts/stops worker pool, runs resume scan
- `backend/app/api/jobs.py` — add pause/resume/cancel/retry routes
- `backend/app/core/openai_client.py` — make `edit_image` async, raise typed exceptions
- `backend/app/db/models.py` — add `JobItem.next_retry_at` column (migration)

### Delete
- `backend/app/core/worker_sync.py` (replaced by pool+executor)

## Implementation Steps

1. Migration: add `JobItem.next_retry_at TIMESTAMP NULL`, status enum value `failed_retryable`
2. `retry_policy.py`:
   - `is_retryable(exc) -> bool` — match openai exception types
   - `backoff(attempt) -> float` — `min(2**attempt, 16) * jitter(0.75..1.25)`
3. `ws_broker.py`: dict `{job_id: set[WebSocket]}`, `publish` iterates and removes dead sockets
4. `core/openai_client.py`: convert to async (`AsyncOpenAI`), raise typed `RetryableError`/`PermanentError` wrapping `openai.APIError`
5. `core/executor.py`: `async def run_item(item_id, db_factory, broker)`:
   - load item, mark `running`, broadcast
   - try call, on success: write PNG, update tokens/cost, status=`done`
   - on retryable: increment attempts, status=`failed_retryable`, schedule `next_retry_at = now + backoff`
   - on permanent or attempts>=5: status=`failed_permanent`
   - commit, broadcast
6. `core/worker_pool.py`:
   - `class WorkerPool: queue, semaphore, tasks[]`
   - `start(n)`: spawn N consumers
   - consumer loop: `await queue.get()`, check `Job.status != 'paused'`, run `run_item`, `queue.task_done()`
   - `enqueue(item_id)`, `enqueue_many`, `drain()`
   - separate "scheduler" task: poll DB for items where `next_retry_at <= now` AND `status='failed_retryable'`, re-enqueue every 1s
7. `main.py` lifespan:
   ```python
   async def lifespan(app):
       pool = WorkerPool(concurrency=settings.concurrency)
       await resume_scan(db, pool)  # mark in-flight failed, enqueue pending
       pool.start()
       app.state.pool = pool
       yield
       await pool.shutdown(timeout=60)
   ```
8. `api/ws.py`:
   ```python
   @router.websocket("/ws/jobs/{job_id}")
   async def ws_job(ws: WebSocket, job_id: int):
       await ws.accept()
       await broker.subscribe(job_id, ws)
       try:
           while True: await ws.receive_text()  # keepalive
       except WebSocketDisconnect:
           broker.unsubscribe(job_id, ws)
   ```
9. `api/jobs.py` add:
   - `POST /api/jobs/{id}/pause` — UPDATE status, no queue manipulation needed
   - `POST /api/jobs/{id}/resume` — UPDATE status, enqueue all `pending|failed_retryable`
   - `POST /api/jobs/{id}/cancel` — UPDATE status, items with `pending` → `cancelled`
   - `POST /api/jobs/{id}/items/{rid}/retry` — reset attempts=0, status=pending, enqueue
10. Tests:
    - `test_retry_policy.py`: backoff bounds, retryable exception classification
    - `test_worker_pool.py`: stub openai client, verify N concurrent in-flight ≤ concurrency
    - `test_pause_resume.py`: pause mid-batch, verify no new items dequeued, resume continues

## Todo List
- [ ] Migration for `next_retry_at` + new status enum
- [ ] retry_policy.py + tests
- [ ] ws_broker.py
- [ ] openai_client.py async + typed errors
- [ ] executor.py with full state machine
- [ ] worker_pool.py with scheduler
- [ ] Resume-on-startup scan in lifespan
- [ ] api/ws.py WebSocket endpoint
- [ ] pause/resume/cancel/retry endpoints
- [ ] Integration test: pause mid-batch + resume
- [ ] Integration test: kill server mid-batch + restart resumes

## Success Criteria
- [ ] Concurrent in-flight requests respect `concurrency` setting
- [ ] 429 from API triggers retry, eventual success
- [ ] Pause: in-flight finishes, no new dequeues; resume continues from where paused
- [ ] Server kill mid-batch + restart: no lost items, no duplicate API calls (verify by mock counter)
- [ ] WS client receives item_update on each state change
- [ ] All tests pass; no file >200 lines

## Risk Assessment
- **Risk**: race between `pause` flag check and `run_item` start → **Mitigation**: check `Job.status` inside consumer right before semaphore acquire
- **Risk**: WS dead-socket buildup → **Mitigation**: try/except on send, evict on failure, periodic cleanup
- **Risk**: SQLite write contention from N workers → **Mitigation**: single AsyncSession factory, WAL mode, 1 commit per item is fine at concurrency=5
- **Risk**: Lifespan resume_scan fails on startup → **Mitigation**: log + continue (job stays running, scheduler picks up retryable items)

## Security Considerations
- WS endpoint has no auth (single-user localhost) — bind only to `127.0.0.1`
- Validate `job_id` exists before subscribing (404 otherwise)

## Next Steps
Phase 3 builds the React frontend consuming these endpoints + WS.
