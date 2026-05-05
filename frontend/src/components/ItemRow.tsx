import type { JobItem } from '../api/jobs'
import { useJobControls } from '../hooks/useJob'
import { formatTokens, formatUSD } from '../lib/format'
import { itemBadge } from '../lib/status'
import { OpenFolderButton } from './OpenFolderButton'
import { Thumbnail } from './Thumbnail'

interface Props {
  jobId: number
  item: JobItem
  onPreview?: (path: string, caption: string) => void
}

export function ItemRow({ jobId, item, onPreview }: Props) {
  const { retry } = useJobControls(jobId)
  const badge = itemBadge(item.status)
  const canRetry = item.status === 'failed_permanent' || item.status === 'failed_retryable' || item.status === 'cancelled'
  const previewSrc = item.output_path ? `/api/preview/${encodeURI(item.output_path)}` : null
  const caption = item.output_path ? item.output_path.split(/[/\\]/).pop() || '' : ''

  return (
    <tr className="border-b border-slate-200 hover:bg-slate-50">
      <td className="px-3 py-2 text-xs text-slate-500 tabular-nums align-top">{item.row_idx}</td>
      <td className="px-3 py-2 align-top">
        <Thumbnail
          path={item.output_path}
          size={120}
          alt={`output ${item.row_idx}`}
          onClick={previewSrc && onPreview ? () => onPreview(previewSrc, caption) : undefined}
        />
        {item.output_path && (
          <div className="mt-1">
            <OpenFolderButton path={item.output_path} selectFile size="sm" variant="inline" label="show in folder" />
          </div>
        )}
      </td>
      <td className="px-3 py-2 align-top">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${badge.cls}`}>
          <span>{badge.icon}</span>
          {badge.label}
        </span>
        {item.attempts > 1 && (
          <span className="ml-1 text-xs text-slate-400">×{item.attempts}</span>
        )}
      </td>
      <td className="px-3 py-2 max-w-md align-top">
        <div className="text-xs text-slate-700 line-clamp-3">{item.prompt}</div>
        <div className="text-[10px] text-slate-400 mt-1 truncate" title={item.refs.join('\n')}>
          refs: {item.refs.length} · {item.refs[0]?.split(/[/\\]/).pop()}{item.refs.length > 1 ? ` (+${item.refs.length - 1})` : ''}
        </div>
        {item.error && (
          <div className="text-[10px] text-rose-600 mt-1 line-clamp-2" title={item.error}>
            {item.error}
          </div>
        )}
      </td>
      <td className="px-3 py-2 text-xs text-slate-600 tabular-nums align-top">
        {formatTokens(item.input_tokens)} / {formatTokens(item.output_tokens)}
      </td>
      <td className="px-3 py-2 text-xs tabular-nums align-top">{formatUSD(item.cost_usd)}</td>
      <td className="px-3 py-2 text-right align-top">
        {canRetry && (
          <button
            className="text-xs px-2 py-1 border border-slate-300 rounded hover:bg-slate-100 disabled:opacity-50"
            onClick={() => retry.mutate(item.id)}
            disabled={retry.isPending}
          >
            ↻ retry
          </button>
        )}
      </td>
    </tr>
  )
}
