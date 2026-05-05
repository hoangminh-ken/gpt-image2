import { CostCards } from '../components/CostCards'
import { useCostSummary, useReconcile } from '../hooks/useCost'
import { formatUSD } from '../lib/format'

export function CostPage() {
  const { data } = useCostSummary()
  const reconcile = useReconcile()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Cost</h1>
        <button
          disabled={reconcile.isPending || !data?.admin_key_configured}
          onClick={() => reconcile.mutate()}
          className="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
          title={!data?.admin_key_configured ? 'Configure OPENAI_ADMIN_KEY in backend/.env' : ''}
        >
          {reconcile.isPending ? 'Syncing…' : 'Sync OpenAI Usage'}
        </button>
      </div>
      {!data?.admin_key_configured && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded p-3">
          Reconcile is unavailable. Set <code>OPENAI_ADMIN_KEY</code> (org admin scope) in <code>backend/.env</code> to enable.
        </div>
      )}
      {reconcile.error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded p-3">
          {(reconcile.error as Error).message}
        </div>
      )}
      {reconcile.data && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded p-3">
          Reconciled {reconcile.data.count} day(s) at {new Date(reconcile.data.fetched_at).toLocaleString()}.
        </div>
      )}
      <CostCards />

      {data && data.by_day.length > 0 && (
        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 text-sm font-medium text-slate-700">
            Daily breakdown (last 30 days)
          </div>
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-600">
              <tr className="text-left">
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2 text-right">Local</th>
                <th className="px-3 py-2 text-right">OpenAI</th>
                <th className="px-3 py-2 text-right">Diff</th>
              </tr>
            </thead>
            <tbody>
              {data.by_day.slice().reverse().map((d) => {
                const diff = d.openai - d.local
                return (
                  <tr key={d.date} className="border-t border-slate-100">
                    <td className="px-3 py-1.5 tabular-nums">{d.date}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{formatUSD(d.local, 4)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{formatUSD(d.openai, 4)}</td>
                    <td className={`px-3 py-1.5 text-right tabular-nums ${diff > 0 ? 'text-rose-600' : diff < 0 ? 'text-emerald-700' : 'text-slate-400'}`}>
                      {diff === 0 ? '—' : `${diff > 0 ? '+' : ''}${formatUSD(diff, 4)}`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
