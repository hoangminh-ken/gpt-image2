interface Props { done: number; failed: number; total: number }

export function ProgressBar({ done, failed, total }: Props) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  const failPct = total > 0 ? Math.round((failed / total) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-slate-600">
        <span>{done} / {total} done{failed > 0 ? `, ${failed} failed` : ''}</span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <div className="h-2 w-full bg-slate-200 rounded overflow-hidden flex">
        <div className="h-full bg-emerald-500" style={{ width: `${pct}%` }} />
        <div className="h-full bg-rose-500" style={{ width: `${failPct}%` }} />
      </div>
    </div>
  )
}
