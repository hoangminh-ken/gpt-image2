import { api } from './client'

export interface WindowCost {
  local_usd: number
  openai_usd: number
  drift_pct: number | null
}

export interface CostSummary {
  today: WindowCost
  week: WindowCost
  month: WindowCost
  by_day: { date: string; local: number; openai: number }[]
  admin_key_configured: boolean
}

export const costApi = {
  summary: () => api.get<CostSummary>('/api/cost'),
  reconcile: () => api.post<{ updated_dates: string[]; count: number; fetched_at: string }>('/api/cost/reconcile'),
}
