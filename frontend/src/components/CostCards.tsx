import type { WindowCost } from '../api/cost'
import { useCostSummary } from '../hooks/useCost'
import { formatUSD } from '../lib/format'

function driftColor(pct: number | null): string {
  if (pct === null) return 'text-slate-400'
  if (pct <= 5) return 'text-emerald-700'
  if (pct <= 15) return 'text-amber-700'
  return 'text-rose-700'
}

function Card({ label, w }: { label: string; w: WindowCost }) {
  const driftLabel = w.drift_pct === null ? '—' : `${w.drift_pct.toFixed(1)}% drift`
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold tabular-nums text-slate-800">
        {formatUSD(w.local_usd, 4)}
      </div>
      <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
        <span>OpenAI: <span className="tabular-nums">{formatUSD(w.openai_usd, 4)}</span></span>
        <span className={driftColor(w.drift_pct)}>{driftLabel}</span>
      </div>
    </div>
  )
}

export function CostCards() {
  const { data, isLoading } = useCostSummary()
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg border border-slate-200 p-4 h-24 animate-pulse" />
        ))}
      </div>
    )
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      <Card label="Today" w={data.today} />
      <Card label="Last 7 days" w={data.week} />
      <Card label="Last 30 days" w={data.month} />
    </div>
  )
}
