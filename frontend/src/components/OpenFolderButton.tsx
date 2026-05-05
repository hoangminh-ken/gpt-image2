import { useState } from 'react'
import { jobsApi } from '../api/jobs'

interface Props {
  path: string
  selectFile?: boolean
  label?: string
  size?: 'sm' | 'md'
  variant?: 'subtle' | 'inline'
}

export function OpenFolderButton({ path, selectFile = false, label = 'Open folder', size = 'md', variant = 'subtle' }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const click = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setBusy(true); setError(null)
    try {
      await jobsApi.openFolder(path, selectFile)
    } catch (err: unknown) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const cls = variant === 'inline'
    ? 'text-xs text-blue-600 hover:underline disabled:opacity-50'
    : `${size === 'sm' ? 'text-xs px-2 py-1' : 'text-sm px-3 py-1.5'} rounded border bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-50`

  return (
    <span className="inline-flex items-center gap-1">
      <button onClick={click} disabled={busy} className={cls} title={path}>
        {busy ? '…' : `📂 ${label}`}
      </button>
      {error && <span className="text-xs text-rose-600" title={error}>!</span>}
    </span>
  )
}
