---
phase: 3
title: "Frontend Dashboard + NewJob + JobDetail"
status: pending
priority: P1
effort: "2d"
dependencies: [2]
---

# Phase 3: Frontend Dashboard + NewJob + JobDetail

## Overview
Build React/Vite UI for the three core pages: Dashboard (cost summary + jobs list), NewJob (Mode A only this phase), JobDetail (live progress, item table, controls). WebSocket integration for real-time updates.

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §6
- [phase-02-async-worker.md](./phase-02-async-worker.md) — API + WS contracts

## Requirements

### Functional
- **Dashboard `/`**: cost today/week/month, jobs list (running highlighted, click → detail)
- **NewJob `/jobs/new`**: Mode A form (template prompt textarea + **hybrid ref input**: paste paths OR drag-drop files), submit → redirect to detail
- **JobDetail `/jobs/:id`**:
  - Header: name, status, progress bar, pause/resume/cancel buttons
  - Items table: status icon, thumbnail (from `/api/preview/...`), prompt, refs, tokens, cost, retry button
  - Live updates via WebSocket subscription
  - Optimistic UI on control button clicks

### Non-Functional
- TanStack Query for HTTP, native WebSocket hook
- Tailwind + shadcn/ui components
- Dev: Vite proxy `/api` → `localhost:8000`, WS proxy `/ws` → `localhost:8000`
- File <200 lines per component

## Architecture

```
frontend/
├── index.html
├── vite.config.ts             # proxy /api + /ws
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── src/
    ├── main.tsx               # router + QueryClient provider
    ├── App.tsx                # layout shell, sidebar nav
    ├── api/
    │   ├── client.ts          # fetch wrapper, JSON helpers
    │   ├── jobs.ts            # job endpoints
    │   └── cost.ts            # cost endpoints
    ├── hooks/
    │   ├── useJob.ts          # GET job detail
    │   ├── useJobs.ts         # GET jobs list
    │   ├── useJobWs.ts        # WS subscription, merges into TanStack cache
    │   └── useCost.ts
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── NewJob.tsx
    │   └── JobDetail.tsx
    ├── components/
    │   ├── JobsTable.tsx
    │   ├── ItemRow.tsx
    │   ├── ProgressBar.tsx
    │   ├── JobControls.tsx    # pause/resume/cancel
    │   ├── CostCards.tsx
    │   ├── RefInputHybrid.tsx # paste textarea + drop zone unified
    │   └── Thumbnail.tsx
    └── lib/
        ├── format.ts          # formatUSD, formatDuration
        └── status.ts          # status → color/icon
```

## Related Code Files

### Create
- All files under `frontend/` listed above
- `frontend/.env.example` (`VITE_API_BASE=/api`)
- Root `package.json` with dev script `concurrently "uvicorn ..." "vite"` (optional dev convenience)

### Modify
- Root `README.md` — add frontend setup section

## Implementation Steps

1. `npm create vite@latest frontend -- --template react-ts`
2. Install: `react-router-dom`, `@tanstack/react-query`, `tailwindcss`, `clsx`, `date-fns`. shadcn init.
3. `vite.config.ts` proxy:
   ```ts
   server: { proxy: {
     '/api': 'http://localhost:8000',
     '/ws':  { target: 'ws://localhost:8000', ws: true }
   }}
   ```
4. `api/client.ts`: tiny fetch wrapper, throws on non-2xx with JSON error parsed
5. `api/jobs.ts`: `listJobs()`, `getJob(id)`, `createJob(payload)`, `pauseJob(id)`, `resumeJob(id)`, `cancelJob(id)`, `retryItem(jobId, itemId)`
6. `hooks/useJobs.ts` + `useJob.ts` — TanStack queries
7. `hooks/useJobWs.ts`:
   ```ts
   const ws = new WebSocket(`ws://${location.host}/ws/jobs/${jobId}`)
   ws.onmessage = (e) => {
     const msg = JSON.parse(e.data)
     if (msg.type === 'item_update') {
       queryClient.setQueryData(['job', jobId], (old) => mergeItem(old, msg.item))
     }
   }
   ```
8. `App.tsx` layout: sidebar (Dashboard, New Job, Cost, Settings) + outlet
9. `Dashboard.tsx`:
   - `<CostCards>` row (today/week/month from `/api/cost`)
   - `<JobsTable>` with sortable columns
10. `NewJob.tsx` Mode A form:
    - Job name input
    - Template prompt textarea
    - `<RefInputHybrid>` — unified component with TWO sub-inputs:
      - **Textarea** for paste paths (one per line, absolute paths)
      - **Drop zone** below — drag files → POST multipart to `/api/uploads/refs` → server returns absolute paths → auto-append to textarea
      - Both feed same internal `paths: string[]` state. Final submit uses unified list.
      - Show thumbnails next to each path (resolved via `/api/preview/{path}`)
      - Inline validation: red highlight + tooltip if path doesn't exist (debounced HEAD check)
    - Estimated cost preview based on count × tier
    - Submit → POST /api/jobs → navigate to detail
11. `JobDetail.tsx`:
    - Header card: name, status badge, progress (done / total), `<JobControls>`
    - Items table with virtualized rows if >100 (use `react-virtuoso` later, skip for Phase 3)
    - `<ItemRow>`: status icon, `<Thumbnail src={`/api/preview/${item.output_path}`}>`, prompt, refs, tokens, cost, retry button on `failed_permanent`
    - Subscribe `useJobWs(jobId)` mounts → unmounts on route change
12. `JobControls`: pause/resume/cancel mutations with TanStack Query, optimistic update
13. Add lightweight unit test (vitest) for `lib/status.ts` mapping
14. Manual smoke: start backend + frontend, create Mode A job, watch live updates

## Todo List
- [ ] Vite scaffold + Tailwind + shadcn
- [ ] vite.config proxy
- [ ] api/client + api/jobs + api/cost
- [ ] useJob/useJobs/useJobWs/useCost hooks
- [ ] Layout + router
- [ ] Dashboard page (cost + jobs list)
- [ ] NewJob Mode A form with `<RefInputHybrid>` (paste + drop)
- [ ] JobDetail with items table
- [ ] WebSocket merge into query cache
- [ ] JobControls pause/resume/cancel/retry
- [ ] Manual end-to-end test

## Success Criteria
- [ ] Create Mode A job from UI → ảnh xuất hiện preview real-time qua WS
- [ ] Pause button instantly grays out running rows; resume continues
- [ ] Failed row shows retry button; click → row goes to pending → done
- [ ] Dashboard cost matches sum of completed items
- [ ] No file >200 lines

## Risk Assessment
- **Risk**: Browser `File` API không lộ path nguồn → **Mitigation**: Hybrid input — drop zone uploads to `/api/uploads/refs` (Phase 1 endpoint), paste textarea cho user đã có path. Cả hai feed same `paths[]` state.
- **Risk**: Upload tmpdir đầy disk theo thời gian → **Mitigation**: Phase 1 endpoint cleanup files >7 ngày on startup; Phase 6 settings cho phép user clear thủ công
- **Risk**: WS reconnect on network blip → **Mitigation**: useJobWs has reconnect with exponential backoff (max 5)
- **Risk**: Thumbnail spam reloads on every item update → **Mitigation**: cache key on output_path, only update src when changes

## Security Considerations
- Vite dev proxy only — production build serves static via FastAPI `StaticFiles`
- `/api/preview` already path-traversal-safe (Phase 1)

## Next Steps
Phase 4 adds Excel upload + Mode B parser to NewJob page.
