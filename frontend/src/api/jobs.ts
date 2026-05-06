import { api } from './client'

export type JobStatus = 'pending' | 'running' | 'paused' | 'done' | 'failed' | 'cancelled'
export type ItemStatus = 'pending' | 'running' | 'done' | 'failed_retryable' | 'failed_permanent' | 'cancelled'

export interface Job {
  id: number
  name: string
  mode: string
  status: JobStatus
  created_at: string
  started_at: string | null
  completed_at: string | null
  total: number
  done: number
  failed: number
}

export interface JobItem {
  id: number
  row_idx: number
  prompt: string
  refs: string[]
  output_name: string | null
  status: ItemStatus
  attempts: number
  error: string | null
  output_path: string | null
  input_tokens: number
  output_tokens: number
  cost_usd: number
  started_at: string | null
  finished_at: string | null
  next_retry_at: string | null
}

export interface JobDetail extends Job {
  items: JobItem[]
}

export interface CreateTemplateJob {
  name: string
  mode: 'template'
  template_prompt: string
  ref_paths: string[]
}

export interface ExcelRow {
  prompt: string
  refs: string[]
  output_name: string | null
}

export interface ExcelRowDiagnostic extends ExcelRow {
  row_idx: number
  valid: boolean
  errors: string[]
}

export interface ExcelParseResult {
  headers: string[]
  rows: ExcelRowDiagnostic[]
  summary: { total: number; valid: number; invalid: number; error?: string }
}

export interface CreateExcelJob {
  name: string
  mode: 'excel'
  rows: ExcelRow[]
  skip_invalid: boolean
}

export const jobsApi = {
  list: () => api.get<Job[]>('/api/jobs'),
  detail: (id: number) => api.get<JobDetail>(`/api/jobs/${id}`),
  create: (body: CreateTemplateJob) => api.post<Job>('/api/jobs', body),
  pause: (id: number) => api.post<Job>(`/api/jobs/${id}/pause`),
  resume: (id: number) => api.post<Job>(`/api/jobs/${id}/resume`),
  cancel: (id: number) => api.post<Job>(`/api/jobs/${id}/cancel`),
  retryItem: (jobId: number, itemId: number) =>
    api.post<JobItem>(`/api/jobs/${jobId}/items/${itemId}/retry`),
  uploadRefs: (files: File[]) =>
    api.upload<{ files: { name: string; path: string; abs_path: string; size: number }[] }>(
      '/api/uploads/refs', files,
    ),
  parseExcel: async (file: File): Promise<ExcelParseResult> => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch('/api/jobs/parse-excel', { method: 'POST', body: fd })
    if (!res.ok) {
      let detail = res.statusText
      try { const d = await res.json(); detail = d.detail || JSON.stringify(d) } catch { /* */ }
      throw new Error(detail)
    }
    return res.json() as Promise<ExcelParseResult>
  },
  createExcelJob: (body: CreateExcelJob) => api.post<Job>('/api/jobs/excel', body),
  openFolder: (path: string, selectFile = false) =>
    api.post<{ ok: boolean; opened: string }>('/api/system/open-folder', { path, select_file: selectFile }),
}

export interface SettingsOut {
  openai_api_key_masked: string
  openai_admin_key_masked: string
  openai_api_key_set: boolean
  openai_admin_key_set: boolean
  openai_image_model: string
  default_concurrency: number
  max_ref_dimension: number
  output_dir: string
  upload_dir: string
  env_file_path: string
  restart_required_for: string[]
}

export interface SettingsUpdate {
  openai_api_key?: string | null
  openai_admin_key?: string | null
  openai_image_model?: string | null
  default_concurrency?: number | null
  max_ref_dimension?: number | null
}

export const settingsApi = {
  get: () => api.get<SettingsOut>('/api/settings'),
  update: (body: SettingsUpdate) => api.put<SettingsOut>('/api/settings', body),
  testKey: () => api.get<{ ok: boolean; error?: string; models_sample?: string[] }>('/api/settings/test-key'),
}

export interface SavedPrompt {
  id: number
  name: string
  content: string
  used_count: number
  created_at: string
  updated_at: string
}

export const promptsApi = {
  list: () => api.get<SavedPrompt[]>('/api/prompts'),
  create: (body: { name: string; content: string }) => api.post<SavedPrompt>('/api/prompts', body),
  update: (id: number, body: { name: string; content: string }) =>
    api.put<SavedPrompt>(`/api/prompts/${id}`, body),
  delete: (id: number) => fetch(`/api/prompts/${id}`, { method: 'DELETE' }).then((r) => {
    if (!r.ok && r.status !== 204) throw new Error(`HTTP ${r.status}`)
  }),
  use: (id: number) => api.post<SavedPrompt>(`/api/prompts/${id}/use`),
}

export interface ApiKeyOut {
  id: number
  name: string
  key_masked: string
  enabled: boolean
  last_used_at: string | null
  rate_limited_until: string | null
  created_at: string
}

export const keysApi = {
  list: () => api.get<ApiKeyOut[]>('/api/keys'),
  create: (body: { name: string; key: string }) => api.post<ApiKeyOut>('/api/keys', body),
  update: (id: number, body: { name?: string; enabled?: boolean }) =>
    api.put<ApiKeyOut>(`/api/keys/${id}`, body),
  delete: (id: number) => fetch(`/api/keys/${id}`, { method: 'DELETE' }).then((r) => {
    if (!r.ok && r.status !== 204) throw new Error(`HTTP ${r.status}`)
  }),
  test: (id: number) => api.post<{ ok: boolean; error?: string; models_sample?: string[] }>(`/api/keys/${id}/test`),
}
