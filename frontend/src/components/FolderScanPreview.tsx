import type { FolderScanResult } from '../api/jobs'
import { OpenFolderButton } from './OpenFolderButton'

interface Props { result: FolderScanResult }

export function FolderScanPreview({ result }: Props) {
  return (
    <div className="space-y-2">
      <div className="text-sm text-slate-700">
        <span className="font-medium">{result.subfolders.length}</span> subfolder(s) ·{' '}
        <strong className="text-emerald-700">{result.total_to_run}</strong> to run
        {result.total_images > result.total_to_run && (
          <> · <span className="text-amber-700">{result.total_images - result.total_to_run}</span> already done (skipped)</>
        )}
      </div>
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
