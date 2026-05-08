import type { FolderScanResult } from '../api/jobs'
import { OpenFolderButton } from './OpenFolderButton'

interface Props { result: FolderScanResult }

export function FolderScanPreview({ result }: Props) {
  const truncated = result.truncated_subfolders > 0 || result.truncated_by_total
  return (
    <div className="space-y-2">
      <div className="text-sm text-slate-700">
        <span className="font-medium">{result.subfolders.length}</span> subfolder(s) ·{' '}
        <strong className="text-emerald-700">{result.total_to_run}</strong> to run
        {result.total_images > result.total_to_run && (
          <> · <span className="text-amber-700">{result.total_images - result.total_to_run}</span> already done (skipped)</>
        )}
      </div>
      {truncated && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded p-2 space-y-1">
          <div className="font-medium">⚠ Scan was truncated:</div>
          {result.truncated_subfolders > 0 && (
            <div>• {result.truncated_subfolders} additional subfolder(s) NOT scanned (cap = 5000).</div>
          )}
          {result.truncated_by_total && (
            <div>• Total image cap reached (50,000) — remaining subfolders skipped.</div>
          )}
          <div className="text-rose-700">
            Solution: split parent into smaller batches, or open an issue to raise the cap further.
          </div>
        </div>
      )}
      <div className="border border-slate-200 rounded max-h-72 overflow-auto bg-white">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-600 sticky top-0 z-10">
            <tr className="text-left">
              <th className="px-2 py-1.5">Subfolder</th>
              <th className="px-2 py-1.5 w-20 text-right">To run</th>
              <th className="px-2 py-1.5 w-20 text-right">Skipped</th>
              <th className="px-2 py-1.5 w-12"></th>
            </tr>
          </thead>
          <tbody>
            {result.subfolders.map((s) => (
              <tr key={s.path} className="border-t border-slate-100">
                <td className="px-2 py-1.5">
                  <div className="font-medium text-slate-800">{s.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono truncate max-w-md" title={s.path}>{s.path}</div>
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">{s.images.length}</td>
                <td className="px-2 py-1.5 text-right tabular-nums text-amber-700">{s.skipped_existing || ''}</td>
                <td className="px-2 py-1.5">
                  <OpenFolderButton path={s.path} size="sm" variant="inline" label="open" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
