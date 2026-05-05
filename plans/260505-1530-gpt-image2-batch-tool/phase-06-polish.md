---
phase: 6
title: "Polish + Settings + README"
status: pending
priority: P3
effort: "0.5d"
dependencies: [4, 5]
---

# Phase 6: Polish + Settings + README

## Overview
Add Settings page (API key test, concurrency, pricing override, output dir, ref image resize), ZIP export of job results, root `npm run dev` (concurrently runs backend+frontend), README with setup/usage docs, and minor UX polish (cost estimate before submit, error toast component, empty states).

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §8 (Risks)

## Requirements

### Functional
- **Settings page** `/settings`:
  - API key (masked input, "Test" button → calls `GET /api/settings/test-key`)
  - Admin key (optional, masked)
  - Default concurrency (1-20 slider)
  - Output directory path
  - Pricing override (input/output $ per M tokens)
  - Ref image max dimension (default 2048, slider 512-4096)
- `GET /api/settings` returns non-secret fields (mask keys)
- `PUT /api/settings` upserts each key into `Setting` table
- `GET /api/settings/test-key` makes minimal API call to validate key
- **Cost estimate** in NewJob: before submit, show `~$X.XX (based on N items × tier pricing)`
- **Error toasts** for failed mutations
- **Empty states** for Dashboard (no jobs yet), Cost (no data yet)
- **ZIP export**: `GET /api/jobs/{id}/export.zip` streams ZIP of all `done` items in job (PNGs + `manifest.json` with prompt/refs/cost per item). Button "Download all (ZIP)" on JobDetail page.
- **Dev script**: root `package.json` with `npm run dev` using `concurrently` to launch both backend (`uvicorn`) and frontend (`vite`) in one command, with prefixed colored logs `[api]` / `[web]`.

### Non-Functional
- Settings stored in SQLite `Setting(key, value)` (already in schema)
- API key value never returned in `GET` — only mask presence
- README covers: prerequisites, setup, env vars, run dev/prod, troubleshooting

## Architecture

```
backend/app/api/settings.py    # GET/PUT/test-key
backend/app/api/exports.py     # GET /api/jobs/{id}/export.zip (streamed)
backend/app/core/openai_client.py (modify) — read max-dim from settings, apply override pricing

frontend/src/pages/Settings.tsx
frontend/src/components/Toast.tsx (or use shadcn toast)
frontend/src/components/CostEstimate.tsx
frontend/src/components/DownloadZipButton.tsx

Root:
package.json   # "dev": concurrently -n api,web -c blue,green ...
```

## Related Code Files

### Create
- `backend/app/api/settings.py`
- `backend/app/api/exports.py`
- `backend/tests/test_settings_api.py`
- `backend/tests/test_zip_export.py`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/CostEstimate.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/components/DownloadZipButton.tsx`
- `package.json` (root, with concurrently dev script)
- `README.md` (root, finalized)
- `docs/project-overview-pdr.md`
- `docs/system-architecture.md`
- `docs/code-standards.md`

### Modify
- `backend/app/main.py` — register settings + exports routers
- `backend/app/core/openai_client.py` — read settings for max_dim and pricing
- `backend/app/core/pricing.py` — accept override
- `frontend/src/App.tsx` — add /settings route
- `frontend/src/pages/NewJob.tsx` — embed `<CostEstimate>`
- `frontend/src/pages/Dashboard.tsx` + `JobDetail.tsx` — use `<EmptyState>`
- `frontend/src/pages/JobDetail.tsx` — embed `<DownloadZipButton>` in header (only enabled when ≥1 done item)

## Implementation Steps

1. `api/settings.py`:
   - `GET /api/settings` returns all keys; mask `openai_api_key`/`openai_admin_key` as `"set"|"unset"`
   - `PUT /api/settings` accepts partial body, validates each key
   - `GET /api/settings/test-key` calls `client.models.list()` (cheapest validation), returns `{ok: true, account: ...}` or `{ok: false, error}`
2. `Settings.tsx` form: each setting → controlled input; on blur PUT
3. `CostEstimate.tsx`: takes `{itemCount, quality, size}` → returns ~USD using current pricing override or defaults; reuses `lib/format.formatUSD`
4. NewJob: render `<CostEstimate items={refsCount} quality={chosen}>` below submit; warn if >$10
5. `EmptyState.tsx`: shadcn Card with icon + title + description + optional CTA
6. README sections:
   - Project overview (1 paragraph)
   - Prerequisites (Python 3.11, Node 20, OpenAI key)
   - Quick start (clone, install, .env, run)
   - Two modes (Mode A vs Mode B with mini examples)
   - Excel format spec (columns, multi-ref delimiter, output_name)
   - Cost dashboard + reconcile
   - Troubleshooting (rate limit, key invalid, large refs)
   - Architecture diagram (link to docs/system-architecture.md)
7. `docs/project-overview-pdr.md`: PDR with goals, non-goals, success metrics
8. `docs/system-architecture.md`: architecture diagram (Mermaid), data flow, state machine, file layout
9. `docs/code-standards.md`: Python (ruff config, type hints), TypeScript (eslint), file size <200, naming conventions
10. `api/exports.py` `GET /api/jobs/{id}/export.zip`:
    - Stream zip via `zipstream-ng` or `zipfile.ZipFile` with `StreamingResponse`
    - Include all `done` items' PNG files
    - Add `manifest.json` at root: `[{row_idx, prompt, refs, output_path, cost_usd, tokens}, ...]`
    - Filename: `{job.name}-{job_id}.zip`
11. `<DownloadZipButton>`: anchor to `/api/jobs/{id}/export.zip`, disabled if no done items, shows count badge `(N images)`
12. Root `package.json`:
    ```json
    {
      "name": "gpt-image2",
      "private": true,
      "scripts": {
        "dev": "concurrently -n api,web -c blue,green \"uvicorn backend.app.main:app --reload --port 8000 --app-dir backend\" \"cd frontend && npm run dev\"",
        "install:all": "cd backend && pip install -r requirements.txt && cd ../frontend && npm install"
      },
      "devDependencies": { "concurrently": "^9.0.0" }
    }
    ```
    README documents BOTH `npm run dev` (1 lệnh) AND 2-terminal fallback for debug

## Todo List
- [ ] api/settings.py with mask + test-key
- [ ] Settings page form
- [ ] CostEstimate component
- [ ] EmptyState component
- [ ] Use override in pricing.py + openai_client.py
- [ ] api/exports.py with streamed ZIP + manifest.json
- [ ] DownloadZipButton component on JobDetail
- [ ] Root package.json with concurrently dev script
- [ ] Test: `npm run dev` boots both backend + frontend with prefixed logs
- [ ] README finalized with all sections (incl. ZIP export, dev script)
- [ ] docs/project-overview-pdr.md
- [ ] docs/system-architecture.md (Mermaid diagrams)
- [ ] docs/code-standards.md
- [ ] Final smoke: fresh clone → `npm run install:all` + `npm run dev` → working tool → ZIP export downloads correctly

## Success Criteria
- [ ] Fresh user follows README only and reaches first generated image
- [ ] API key test button validates without leaking key
- [ ] Pricing override applies to next job's cost calc
- [ ] Empty states show on first run (no jobs, no cost)
- [ ] Cost estimate within ±20% of actual (rough is fine)
- [ ] All docs committed and linked from README
- [ ] ZIP download: open downloaded zip → contains all done PNGs + manifest.json with valid JSON
- [ ] `npm run dev` starts both servers, Ctrl+C stops both cleanly

## Risk Assessment
- **Risk**: Settings race when multiple PUTs in flight → **Mitigation**: per-key upsert, last-write-wins is acceptable
- **Risk**: Cost estimate misleads user → **Mitigation**: caveat label "Estimate; actual may vary based on prompt + ref complexity"
- **Risk**: Pricing override drift from reality → **Mitigation**: admin key reconcile shows truth; settings has "reset to defaults" button
- **Risk**: ZIP of huge job (1000+ images) blocks event loop / fills RAM → **Mitigation**: `StreamingResponse` + chunked write (no full-buffer); `Content-Length` not set (chunked encoding)
- **Risk**: `concurrently` Ctrl+C zombie process trên Windows → **Mitigation**: use `--kill-others-on-fail` flag; document fallback to 2-terminal trong README troubleshooting

## Security Considerations
- API key stored in `Setting` table — encrypt at rest? KISS: no, file is local-only and protected by OS permissions. Document this in README under Security.
- Mask everywhere in UI

## Next Steps
After Phase 6: project ready for daily use. Future improvements (out of scope this plan): ref-image gallery, prompt templates library, multi-key key rotation, scheduled reconcile job, individual-image download from JobDetail (alternative to ZIP), webhook notifications on job complete.
