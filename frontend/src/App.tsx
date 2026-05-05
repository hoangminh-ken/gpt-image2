import { Link, NavLink, Outlet } from 'react-router-dom'

const linkBase = 'block px-3 py-2 rounded-md text-sm font-medium'
const active = 'bg-slate-900 text-white'
const inactive = 'text-slate-600 hover:bg-slate-100'

export function App() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-white border-r border-slate-200 p-4 flex flex-col gap-1">
        <Link to="/" className="text-lg font-semibold text-slate-900 px-3 py-2 mb-2">
          gpt-image2
        </Link>
        <NavLink to="/" end className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}>
          Dashboard
        </NavLink>
        <NavLink to="/jobs/new" className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}>
          New Job
        </NavLink>
        <NavLink to="/cost" className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}>
          Cost
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `${linkBase} ${isActive ? active : inactive}`}>
          Settings
        </NavLink>
        <div className="mt-auto text-xs text-slate-400 px-3">v0.6.0</div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
