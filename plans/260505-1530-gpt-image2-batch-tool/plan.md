---
title: GPT-Image-2 Batch Generator
status: pending
priority: P1
created: 2026-05-05
type: implementation
source: brainstorm-summary.md
---

# GPT-Image-2 Batch Generator — Implementation Plan

Local web app that batches image generation via OpenAI `gpt-image-2`, with retry/pause/resume, Excel input mode, and dual-source cost dashboard.

## Context Links
- Brainstorm: [brainstorm-summary.md](./brainstorm-summary.md)
- OpenAI docs: https://developers.openai.com/api/docs/models/gpt-image-2
- Pricing: $8/M input tokens, $30/M output tokens

## Phases

| # | Phase | Status | Priority | Effort | Depends On |
|---|-------|--------|----------|--------|-----------|
| 1 | [Backend Skeleton + Mode A](./phase-01-backend-skeleton.md) | ✅ completed | P1 | 1d | — |
| 2 | [Async Worker + Retry/Pause/Resume](./phase-02-async-worker.md) | ✅ completed | P1 | 1.5d | 1 |
| 3 | [Frontend Dashboard + NewJob + JobDetail](./phase-03-frontend-dashboard.md) | ✅ completed | P1 | 2d | 2 |
| 4 | [Mode B Excel Parser](./phase-04-excel-mode.md) | ✅ completed | P2 | 0.5d | 3 |
| 5 | [Cost Reconcile + OpenAI Usage API](./phase-05-cost-reconcile.md) | pending | P2 | 0.5d | 3 |
| 6 | [Polish + Settings + README](./phase-06-polish.md) | pending | P3 | 0.5d | 4, 5 |

**Total estimate**: ~6 days solo dev

## Key Dependencies
- Python 3.11+, FastAPI, SQLAlchemy, openai≥1.50, Pillow, openpyxl, pytest, ruff
- Node 20+, Vite, React 18, TypeScript, TanStack Query, Tailwind/shadcn
- OpenAI API key with `gpt-image-2` access

## Decisions Locked (from brainstorm + follow-up)
1. Local web app, single-user, no auth, `.env` API key
2. Python FastAPI + React/Vite TypeScript
3. SQLite + filesystem persistence
4. Two pairing modes: A (template broadcast), B (Excel row-based, `|`-delimited refs)
5. Dual-source cost: local real-time + OpenAI Usage API reconcile
6. Default concurrency 5, soft pause (finish in-flight)
7. PNG output only
8. Mode A ref input: hybrid (paste paths textarea + drag-drop upload to `/api/uploads/refs`)
9. Dev workflow: root `npm run dev` via concurrently (single command), 2-terminal fallback documented
10. ZIP export of job results in Phase 6 (`GET /api/jobs/{id}/export.zip` with manifest.json)

## Out of Scope
Multi-user, auth, cloud deploy, JPEG/WebP, image post-processing, webhooks, distributed workers.

## Success Criteria (Plan-Level)
- [ ] Run 100-row Excel batch end-to-end without manual intervention
- [ ] Pause + restart server + resume — no duplicate API calls, no lost rows
- [ ] Local USD cost within ±2% of OpenAI Usage API for completed batch
- [ ] Failed row retry from UI works in 1 click
- [ ] WebSocket updates within 1s of API response

## Next Step
Run `/ck:cook plans/260505-1530-gpt-image2-batch-tool` to start Phase 1.
