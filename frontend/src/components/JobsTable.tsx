import { Link } from 'react-router-dom'
import type { Job } from '../api/jobs'
import { formatDateShort } from '../lib/format'
import { jobBadge } from '../lib/status'
import { ProgressBar } from './ProgressBar'

interface Props { jobs: Job[] }

export function JobsTable({ jobs }: Props) {
  if (jobs.length === 0) {
    return (
      <div className="border border-dashed border-slate-300 rounded-lg p-12 text-center text-slate-500 bg-white">
        <div className="text-3xl mb-2">📦</div>
        <div className="font-medium">No jobs yet</div>
        <div className="text-sm">Create one from the "New Job" page.</div>
      </div>
    )
  }
  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs text-slate-600">
          <tr className="text-left">
            <th className="px-3 py-2">Name</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2 w-1/3">Progress</th>
            <th className="px-3 py-2">Created</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j) => {
            const b = jobBadge(j.status)
            return (
              <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                <td className="px-3 py-2">
                  <Link to={`/jobs/${j.id}`} className="text-blue-700 hover:underline font-medium">
                    {j.name}
                  </Link>
                  <div className="text-xs text-slate-400">#{j.id} · {j.mode}</div>
                </td>
                <td className="px-3 py-2">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${b.cls}`}>
                    {b.label}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <ProgressBar done={j.done} failed={j.failed} total={j.total} />
                </td>
                <td className="px-3 py-2 text-xs text-slate-500">
                  {formatDateShort(j.created_at)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
