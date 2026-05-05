import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Job, JobStatus } from '../api/jobs'
import { OpenFolderButton } from '../components/OpenFolderButton'
import { ProgressBar } from '../components/ProgressBar'
import { useJobs } from '../hooks/useJobs'
import { formatDateShort } from '../lib/format'
import { jobBadge } from '../lib/status'

const STATUS_FILTERS: (JobStatus | 'all')[] = ['all', 'running', 'paused', 'done', 'failed', 'cancelled']

export function History() {
  const { data: jobs, isLoading, error } = useJobs()
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all')
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    if (!jobs) return []
    let list = jobs
    if (statusFilter !== 'all') list = list.filter((j) => j.status === statusFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter((j) => j.name.toLowerCase().includes(q) || String(j.id).includes(q))
    }
    return list
  }, [jobs, statusFilter, search])

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-semibold">History</h1>
        <Link to="/jobs/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium">
          + New Job
        </Link>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-3 flex items-center gap-3 flex-wrap">
        <input
          placeholder="Search by name or #id"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="border border-slate-300 rounded-md px-3 py-1.5 text-sm flex-1 min-w-[200px]"
        />
        <div className="flex gap-1 flex-wrap">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 text-xs rounded-full border ${
                statusFilter === s
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {s}
              {s !== 'all' && jobs && (
                <span className="ml-1 opacity-70">{jobs.filter((j) => j.status === s).length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <div className="text-slate-500 text-sm">Loading…</div>}
      {error && <div className="text-rose-600 text-sm">{(error as Error).message}</div>}

      {filtered.length === 0 && jobs && (
        <div className="border border-dashed border-slate-300 rounded-lg p-12 text-center text-slate-500 bg-white">
          No jobs match these filters.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-600">
              <tr className="text-left">
                <th className="px-3 py-2">Job</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 w-1/3">Progress</th>
                <th className="px-3 py-2">Created</th>
                <th className="px-3 py-2 w-44">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((j: Job) => {
                const b = jobBadge(j.status)
                const hasOutputs = j.done > 0
                return (
                  <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2">
                      <Link to={`/jobs/${j.id}`} className="text-blue-700 hover:underline font-medium">
                        {j.name}
                      </Link>
                      <div className="text-xs text-slate-400">#{j.id} · {j.mode}</div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${b.cls}`}>{b.label}</span>
                    </td>
                    <td className="px-3 py-2">
                      <ProgressBar done={j.done} failed={j.failed} total={j.total} />
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500">{formatDateShort(j.created_at)}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {hasOutputs && <OpenFolderButton path={`outputs/${j.id}`} size="sm" label="Folder" />}
                        {j.done > 0 && (
                          <a
                            href={`/api/jobs/${j.id}/export.zip`}
                            className="text-xs px-2 py-1 rounded border bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100"
                            title="Download all done images as ZIP"
                          >
                            ⬇ ZIP
                          </a>
                        )}
                      </div>
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
