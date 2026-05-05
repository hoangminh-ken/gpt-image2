import { Link } from 'react-router-dom'
import { CostCards } from '../components/CostCards'
import { JobsTable } from '../components/JobsTable'
import { useJobs } from '../hooks/useJobs'

export function Dashboard() {
  const { data: jobs, isLoading, error } = useJobs()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Link
          to="/jobs/new"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
        >
          + New Job
        </Link>
      </div>

      <CostCards />

      <section>
        <h2 className="text-sm font-medium text-slate-600 mb-2">Recent jobs</h2>
        {isLoading && <div className="text-slate-500 text-sm">Loading…</div>}
        {error && <div className="text-rose-600 text-sm">{(error as Error).message}</div>}
        {jobs && <JobsTable jobs={jobs} />}
      </section>
    </div>
  )
}
