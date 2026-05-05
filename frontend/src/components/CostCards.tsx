import type { Job } from '../api/jobs'
import { formatUSD } from '../lib/format'

interface Props { jobs: Job[] | undefined }

interface DerivedCost {
  totalUsd: number
  totalDone: number
  totalFailed: number
  runningJobs: number
}

function derive(jobs: Job[] = []): DerivedCost {
  // Note: this is jobs-summary derived, not from /api/cost. Phase 5 adds real /api/cost endpoint.
  return {
    totalUsd: 0, // Phase 5 will populate from server aggregate
    totalDone: jobs.reduce((s, j) => s + j.done, 0),
    totalFailed: jobs.reduce((s, j) => s + j.failed, 0),
    runningJobs: jobs.filter((j) => j.status === 'running' || j.status === 'paused').length,
  }
}

export function CostCards({ jobs }: Props) {
  const d = derive(jobs)
  const cards = [
    { label: 'Images generated', value: d.totalDone.toString(), tone: 'text-emerald-700' },
    { label: 'Failed items', value: d.totalFailed.toString(), tone: 'text-rose-600' },
    { label: 'Active jobs', value: d.runningJobs.toString(), tone: 'text-blue-700' },
    { label: 'Total cost', value: formatUSD(d.totalUsd, 2), tone: 'text-slate-700', subtitle: 'Phase 5 wires real /api/cost' },
  ]
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-lg border border-slate-200 p-4">
          <div className="text-xs text-slate-500">{c.label}</div>
          <div className={`text-2xl font-semibold tabular-nums ${c.tone}`}>{c.value}</div>
          {c.subtitle && <div className="text-[10px] text-slate-400 mt-1">{c.subtitle}</div>}
        </div>
      ))}
    </div>
  )
}
