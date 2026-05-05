import type { ItemStatus, JobStatus } from '../api/jobs'

export function jobBadge(s: JobStatus): { label: string; cls: string } {
  switch (s) {
    case 'pending': return { label: 'pending', cls: 'bg-slate-200 text-slate-700' }
    case 'running': return { label: 'running', cls: 'bg-blue-100 text-blue-700 animate-pulse' }
    case 'paused':  return { label: 'paused',  cls: 'bg-yellow-100 text-yellow-800' }
    case 'done':    return { label: 'done',    cls: 'bg-emerald-100 text-emerald-800' }
    case 'failed':  return { label: 'failed',  cls: 'bg-rose-100 text-rose-700' }
    case 'cancelled': return { label: 'cancelled', cls: 'bg-slate-200 text-slate-500' }
  }
}

export function itemBadge(s: ItemStatus): { label: string; cls: string; icon: string } {
  switch (s) {
    case 'pending':           return { label: 'pending',  cls: 'bg-slate-200 text-slate-700', icon: '○' }
    case 'running':           return { label: 'running',  cls: 'bg-blue-100 text-blue-700',   icon: '◐' }
    case 'done':              return { label: 'done',     cls: 'bg-emerald-100 text-emerald-800', icon: '✓' }
    case 'failed_retryable':  return { label: 'retrying', cls: 'bg-amber-100 text-amber-800', icon: '↻' }
    case 'failed_permanent':  return { label: 'failed',   cls: 'bg-rose-100 text-rose-700',   icon: '✗' }
    case 'cancelled':         return { label: 'cancelled', cls: 'bg-slate-200 text-slate-500', icon: '⊘' }
  }
}
