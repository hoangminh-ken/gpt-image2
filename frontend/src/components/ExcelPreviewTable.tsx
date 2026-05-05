import type { ExcelParseResult } from '../api/jobs'

interface Props {
  result: ExcelParseResult
  skipInvalid: boolean
  onSkipChange: (v: boolean) => void
}

export function ExcelPreviewTable({ result, skipInvalid, onSkipChange }: Props) {
  if (result.summary.error) {
    return <div className="text-rose-600 text-sm">Parser error: {result.summary.error}</div>
  }
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm">
        <div className="text-slate-700">
          <span className="font-medium">{result.summary.total}</span> rows ·{' '}
          <span className="text-emerald-700 font-medium">{result.summary.valid} valid</span> ·{' '}
          <span className="text-rose-700 font-medium">{result.summary.invalid} invalid</span>
        </div>
        {result.summary.invalid > 0 && (
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={skipInvalid} onChange={(e) => onSkipChange(e.target.checked)} />
            Skip invalid rows
          </label>
        )}
      </div>

      <div className="border border-slate-200 rounded overflow-auto max-h-96">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-600 sticky top-0">
            <tr className="text-left">
              <th className="px-2 py-1.5 w-10">#</th>
              <th className="px-2 py-1.5 w-16">Status</th>
              <th className="px-2 py-1.5">Prompt</th>
              <th className="px-2 py-1.5 w-32">Refs</th>
              <th className="px-2 py-1.5 w-32">Output name</th>
              <th className="px-2 py-1.5">Errors</th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((r) => (
              <tr key={r.row_idx} className={r.valid ? '' : 'bg-rose-50'}>
                <td className="px-2 py-1 text-slate-400 tabular-nums">{r.row_idx}</td>
                <td className="px-2 py-1">
                  {r.valid
                    ? <span className="text-emerald-700">✓ ok</span>
                    : <span className="text-rose-700">✗ invalid</span>}
                </td>
                <td className="px-2 py-1 max-w-xs truncate" title={r.prompt}>{r.prompt}</td>
                <td className="px-2 py-1 text-slate-600">{r.refs.length} ref(s)</td>
                <td className="px-2 py-1 text-slate-600 truncate">{r.output_name || '—'}</td>
                <td className="px-2 py-1 text-rose-700 max-w-xs truncate" title={r.errors.join('; ')}>
                  {r.errors.join('; ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
