import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ImagePreviewModal } from '../components/ImagePreviewModal'
import { ItemRow } from '../components/ItemRow'
import { JobControls } from '../components/JobControls'
import { OpenFolderButton } from '../components/OpenFolderButton'
import { ProgressBar } from '../components/ProgressBar'
import { useJob, useJobControls } from '../hooks/useJob'
import { useJobWs } from '../hooks/useJobWs'
import { formatDateShort, formatUSD } from '../lib/format'
import { jobBadge } from '../lib/status'

export function JobDetail() {
  const { id } = useParams<{ id: string }>()
  const jobId = id ? parseInt(id, 10) : NaN
  const { data: job, isLoading, error } = useJob(jobId)
  useJobWs(Number.isFinite(jobId) ? jobId : undefined, !!job)

  const [preview, setPreview] = useState<{ src: string; caption: string } | null>(null)

  if (Number.isNaN(jobId)) return <div className="text-rose-600">Invalid job id</div>
  if (isLoading) return <div className="text-slate-500 text-sm">Loading…</div>
  if (error) return <div className="text-rose-600 text-sm">{(error as Error).message}</div>
  if (!job) return null

  const totalCost = job.items.reduce((s, i) => s + i.cost_usd, 0)
  const badge = jobBadge(job.status)
  const jobOutputDir = `outputs/${job.id}`
  const hasOutputs = job.items.some((i) => !!i.output_path)
  const failedCount = job.items.filter((i) =>
    i.status === 'failed_permanent' || i.status === 'failed_retryable' || i.status === 'cancelled',
  ).length

  return (
    <div className="space-y-5">
      <div className="flex items-center text-sm text-slate-500">
        <Link to="/" className="hover:underline">Dashboard</Link>
        <span className="mx-1.5">›</span>
        <Link to="/history" className="hover:underline">History</Link>
        <span className="mx-1.5">›</span>
        <span>Job #{job.id}</span>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">{job.name}</h1>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
              <span>#{job.id}</span>
              <span>·</span>
              <span>{job.mode}</span>
              <span>·</span>
              <span>created {formatDateShort(job.created_at)}</span>
              {job.completed_at && <>
                <span>·</span>
                <span>completed {formatDateShort(job.completed_at)}</span>
              </>}
            </div>
          </div>
          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${badge.cls}`}>
            {badge.label}
          </span>
        </div>

        <ProgressBar done={job.done} failed={job.failed} total={job.total} />

        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="text-sm">
            <span className="text-slate-500">Total cost: </span>
            <span className="font-medium tabular-nums">{formatUSD(totalCost)}</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {hasOutputs && <OpenFolderButton path={jobOutputDir} label="Open output folder" />}
            {failedCount > 0 && <RetryAllButton jobId={job.id} count={failedCount} />}
            {job.done > 0 && (
              <a
                href={`/api/jobs/${job.id}/export.zip`}
                className="px-3 py-1.5 rounded text-sm font-medium border bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100"
              >
                ⬇ Download ZIP ({job.done})
              </a>
            )}
            <JobControls job={job} />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-600">
            <tr className="text-left">
              <th className="px-3 py-2 w-10">#</th>
              <th className="px-3 py-2 w-36">Output</th>
              <th className="px-3 py-2 w-32">Status</th>
              <th className="px-3 py-2">Prompt / refs</th>
              <th className="px-3 py-2 w-32">Tokens (in/out)</th>
              <th className="px-3 py-2 w-20">Cost</th>
              <th className="px-3 py-2 w-20"></th>
            </tr>
          </thead>
          <tbody>
            {job.items.map((it) => (
              <ItemRow
                key={it.id}
                jobId={job.id}
                item={it}
                onPreview={(src, caption) => setPreview({ src, caption })}
              />
            ))}
          </tbody>
        </table>
      </div>

      <ImagePreviewModal
        src={preview?.src ?? null}
        caption={preview?.caption}
        onClose={() => setPreview(null)}
      />
    </div>
  )
}

function RetryAllButton({ jobId, count }: { jobId: number; count: number }) {
  const { retryAll } = useJobControls(jobId)
  const click = () => {
    if (!confirm(`Retry ${count} failed item(s)? Each one costs ~$0.07.`)) return
    retryAll.mutate()
  }
  return (
    <button
      onClick={click}
      disabled={retryAll.isPending}
      className="px-3 py-1.5 rounded text-sm font-medium border bg-amber-50 border-amber-300 text-amber-800 hover:bg-amber-100 disabled:opacity-50"
      title="Re-queue every failed/cancelled item in this job"
    >
      {retryAll.isPending ? 'Retrying…' : `↻ Retry all failed (${count})`}
    </button>
  )
}
