---
phase: 5
title: "Cost Reconcile + OpenAI Usage API"
status: completed
priority: P2
effort: "0.5d"
dependencies: [3]
completed: 2026-05-05
smoke_test: "PASS — 4 cost tests (summary empty, summary with data + drift calc, reconcile no key 400, reconcile success with respx mock). Backend 41 tests, frontend 346KB."
---

# Phase 5: Cost Reconcile + OpenAI Usage API

## Overview
Add daily reconcile against OpenAI Organization Usage API to verify local cost tracking. Dashboard shows drift % and tooltip explaining discrepancy sources.

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §5 (Cost tracking)
- OpenAI Usage API: `GET /v1/organization/usage/images?bucket_width=1d&start_time=...`

## Requirements

### Functional
- `POST /api/cost/reconcile` — pulls last 30 days from OpenAI Usage API, upserts into `cost_daily(source='openai')`
- `GET /api/cost` — returns aggregated:
  ```json
  {
    "today": {"local_usd": 1.23, "openai_usd": 1.20, "drift_pct": 2.5},
    "week": {...}, "month": {...},
    "by_day": [{"date": "...", "local": ..., "openai": ...}]
  }
  ```
- Dashboard `<CostCards>` shows drift indicator (green ≤5%, yellow 5-15%, red >15%)
- `/cost` detail page: line chart local vs openai per day + manual reconcile button

### Non-Functional
- Reconcile runs on-demand only (no scheduler — KISS)
- Requires `OPENAI_ADMIN_KEY` (separate from inference key) or org-scoped key with usage permission
- Graceful fallback: if Usage API call fails (403, no admin key), show "Reconcile unavailable, configure OPENAI_ADMIN_KEY" hint

## Architecture

```
backend/app/core/usage_api.py
  async def fetch_image_usage(start_ts, end_ts, admin_key) -> List[DailyUsage]
    GET https://api.openai.com/v1/organization/usage/images
    Auth: Bearer {admin_key}
    Pagination via 'next_page' cursor
    Returns daily buckets with input_tokens, output_tokens, num_images

backend/app/api/cost.py
  GET /api/cost                  # aggregated dashboard payload
  POST /api/cost/reconcile       # trigger Usage API pull, upsert cost_daily
  GET /api/cost/by-day           # raw daily series for chart

frontend/src/pages/Cost.tsx      # detail page with chart
frontend/src/components/CostCards.tsx (already in Phase 3 — extend with drift)
frontend/src/components/CostChart.tsx  # recharts LineChart
```

## Related Code Files

### Create
- `backend/app/core/usage_api.py`
- `backend/app/api/cost.py` (new dedicated router)
- `backend/tests/test_usage_api.py` (with respx mock)
- `backend/tests/test_cost_aggregation.py`
- `frontend/src/pages/Cost.tsx`
- `frontend/src/components/CostChart.tsx`

### Modify
- `backend/app/config.py` — add `OPENAI_ADMIN_KEY` optional setting
- `backend/app/main.py` — register cost router
- `backend/app/db/models.py` — already has `CostDaily(date, source, ...)`, no migration needed
- `frontend/src/components/CostCards.tsx` — add drift badge
- `frontend/src/api/cost.ts` — add `reconcile()`, `getByDay()`
- `frontend/src/App.tsx` — add `/cost` route to sidebar
- Root `README.md` — note about admin key

## Implementation Steps

1. `config.py`: `OPENAI_ADMIN_KEY: Optional[str] = None`
2. `core/usage_api.py`:
   ```python
   async def fetch_image_usage(start_unix: int, end_unix: int, admin_key: str):
       url = "https://api.openai.com/v1/organization/usage/images"
       params = {"start_time": start_unix, "end_time": end_unix, "bucket_width": "1d", "limit": 31}
       async with httpx.AsyncClient() as c:
           resp = await c.get(url, params=params, headers={"Authorization": f"Bearer {admin_key}"})
           resp.raise_for_status()
           return resp.json()  # paginated; loop until no next_page
   ```
3. Cost calculation from Usage API response: each bucket has `input_tokens`, `output_tokens`, `num_model_requests`. Compute USD with same `pricing.compute_cost`.
4. `api/cost.py`:
   - `GET /api/cost`: SQL aggregations on `cost_daily` (group by date, pivot source); compute drift = abs(local-openai)/local
   - `POST /api/cost/reconcile`: fetch last 30 days, upsert `cost_daily(date, source='openai')`, return summary `{updated_dates: [...], drift_summary: {...}}`
5. Frontend `cost.ts` API client + TanStack mutation for reconcile
6. `Cost.tsx`: cards + `<CostChart>` (recharts) with two lines (local, openai)
7. `CostCards.tsx`: extend with drift badge using `lib/status.ts` color thresholds
8. Tests:
   - Mock Usage API response with `respx`, assert `cost_daily` rows upserted
   - Aggregation: insert sample data, assert drift calc
9. Manual test: run small batch → check local cost; click reconcile → verify openai matches within ±2%

## Todo List
- [ ] usage_api.py with pagination
- [ ] OPENAI_ADMIN_KEY config
- [ ] api/cost.py with /cost and /reconcile
- [ ] Aggregation SQL (CTE or pandas) for dashboard payload
- [ ] respx mocks + tests
- [ ] CostCards drift badge
- [ ] Cost.tsx page with chart
- [ ] Sidebar /cost route
- [ ] Manual reconcile end-to-end
- [ ] README admin-key section

## Success Criteria
- [ ] Admin key configured → reconcile button populates `cost_daily(source='openai')` for last 30 days
- [ ] Drift between local vs openai for completed batch ≤ 2%
- [ ] Chart renders both sources, hover shows exact USD per day
- [ ] Without admin key: button shows "Configure OPENAI_ADMIN_KEY" hint, no crash

## Risk Assessment
- **Risk**: Usage API requires admin key not regular key → **Mitigation**: clear error message + README step-by-step guide
- **Risk**: Usage API endpoint changes / not GA → **Mitigation**: feature-flag via setting; fallback to local-only if 404
- **Risk**: Reconciling overlapping days double-counts → **Mitigation**: upsert by composite key `(date, source)`, never sum
- **Risk**: Time zone confusion (UTC vs local) → **Mitigation**: store UTC dates; UI shows local TZ with note

## Security Considerations
- Admin key is more sensitive than inference key (full org access) — never log, never return in API
- `.env` only, masked in any settings UI

## Next Steps
Phase 6: settings UI, pricing override, ref image resize helper, README finalization.
