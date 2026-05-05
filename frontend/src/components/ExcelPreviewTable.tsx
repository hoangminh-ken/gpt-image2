import { Fragment, useState } from 'react'
import type { ExcelParseResult } from '../api/jobs'
import { ImagePreviewModal } from './ImagePreviewModal'
import { Thumbnail } from './Thumbnail'

interface Props {
  result: ExcelParseResult
  skipInvalid: boolean
  onSkipChange: (v: boolean) => void
}

export function ExcelPreviewTable({ result, skipInvalid, onSkipChange }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [preview, setPreview] = useState<{ src: string; caption: string } | null>(null)

  if (result.summary.error) {
    return <div className="text-rose-600 text-sm">Parser error: {result.summary.error}</div>
  }

  const toggle = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
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

      <div className="border border-slate-200 rounded overflow-auto max-h-[480px]">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-600 sticky top-0 z-10">
            <tr className="text-left">
              <th className="px-2 py-1.5 w-10">#</th>
              <th className="px-2 py-1.5 w-20">Status</th>
              <th className="px-2 py-1.5 w-44">Refs preview</th>
              <th className="px-2 py-1.5">Prompt</th>
              <th className="px-2 py-1.5 w-32">Output name</th>
              <th className="px-2 py-1.5 w-10"></th>
            </tr>
          </thead>
          <tbody>
            {result.rows.map((r) => {
              const isOpen = expanded.has(r.row_idx)
              return (
                <Fragment key={r.row_idx}>
                  <tr
                    className={`border-t border-slate-100 cursor-pointer ${r.valid ? 'hover:bg-slate-50' : 'bg-rose-50 hover:bg-rose-100'}`}
                    onClick={() => toggle(r.row_idx)}
                  >
                    <td className="px-2 py-2 text-slate-400 tabular-nums align-top">{r.row_idx}</td>
                    <td className="px-2 py-2 align-top">
                      {r.valid
                        ? <span className="text-emerald-700 font-medium">✓ valid</span>
                        : <span className="text-rose-700 font-medium">✗ invalid</span>}
                    </td>
                    <td className="px-2 py-2 align-top">
                      <div className="flex items-center gap-1 flex-wrap">
                        {r.refs.slice(0, 3).map((ref, i) => {
                          const src = `/api/preview/${encodeURI(ref)}`
                          return (
                            <span key={i} onClick={(e) => e.stopPropagation()}>
                              <Thumbnail
                                path={ref}
                                size={36}
                                alt={ref}
                                onClick={() => setPreview({ src, caption: ref })}
                              />
                            </span>
                          )
                        })}
                        {r.refs.length > 3 && (
                          <span className="text-[10px] text-slate-500 ml-1">+{r.refs.length - 3}</span>
                        )}
                        {r.refs.length === 0 && <span className="text-rose-500">no refs</span>}
                      </div>
                    </td>
                    <td className="px-2 py-2 align-top">
                      <div className={isOpen ? 'whitespace-pre-wrap text-slate-700' : 'truncate text-slate-700 max-w-md'} title={!isOpen ? r.prompt : undefined}>
                        {r.prompt || <em className="text-rose-500">empty</em>}
                      </div>
                      {!r.valid && r.errors.length > 0 && (
                        <div className="text-[10px] text-rose-700 mt-1">
                          {r.errors.join(' · ')}
                        </div>
                      )}
                    </td>
                    <td className="px-2 py-2 text-slate-600 align-top">{r.output_name || <span className="text-slate-400">(auto)</span>}</td>
                    <td className="px-2 py-2 align-top text-slate-400">
                      {isOpen ? '▾' : '▸'}
                    </td>
                  </tr>
                  {isOpen && (
                    <tr className="bg-slate-50 border-t border-slate-200">
                      <td colSpan={6} className="px-4 py-3 text-[11px] text-slate-600">
                        <div className="space-y-2">
                          <div>
                            <span className="font-medium text-slate-700">All refs:</span>
                            <ul className="mt-1 space-y-0.5">
                              {r.refs.map((ref, i) => (
                                <li key={i} className="font-mono break-all">{ref}</li>
                              ))}
                            </ul>
                          </div>
                          {r.output_name && (
                            <div>
                              <span className="font-medium text-slate-700">Output filename:</span>{' '}
                              <code>{r.output_name}</code>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-500">
        💡 Click a row to expand · click a thumbnail to preview the reference image
      </div>

      <ImagePreviewModal
        src={preview?.src ?? null}
        caption={preview?.caption}
        onClose={() => setPreview(null)}
      />
    </div>
  )
}
