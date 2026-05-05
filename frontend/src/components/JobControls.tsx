import type { Job } from '../api/jobs'
import { useJobControls } from '../hooks/useJob'

interface Props { job: Job }

export function JobControls({ job }: Props) {
  const { pause, resume, cancel } = useJobControls(job.id)
  const btn = 'px-3 py-1.5 rounded text-sm font-medium border transition disabled:opacity-50 disabled:cursor-not-allowed'

  return (
    <div className="flex gap-2">
      {(job.status === 'running' || job.status === 'pending') && (
        <button
          className={`${btn} bg-yellow-50 border-yellow-300 text-yellow-800 hover:bg-yellow-100`}
          onClick={() => pause.mutate()}
          disabled={pause.isPending}
        >
          ❚❚ Pause
        </button>
      )}
      {job.status === 'paused' && (
        <button
          className={`${btn} bg-blue-50 border-blue-300 text-blue-800 hover:bg-blue-100`}
          onClick={() => resume.mutate()}
          disabled={resume.isPending}
        >
          ▶ Resume
        </button>
      )}
      {!['done', 'cancelled'].includes(job.status) && (
        <button
          className={`${btn} bg-rose-50 border-rose-300 text-rose-700 hover:bg-rose-100`}
          onClick={() => {
            if (confirm(`Cancel job "${job.name}"? Pending items will be marked cancelled.`)) {
              cancel.mutate()
            }
          }}
          disabled={cancel.isPending}
        >
          ✗ Cancel
        </button>
      )}
    </div>
  )
}
