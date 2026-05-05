export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || JSON.stringify(data)
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(p: string) => request<T>('GET', p),
  post: <T>(p: string, body?: unknown) => request<T>('POST', p, body),
  put: <T>(p: string, body?: unknown) => request<T>('PUT', p, body),
  upload: async <T>(p: string, files: File[], field = 'files'): Promise<T> => {
    const fd = new FormData()
    for (const f of files) fd.append(field, f)
    const res = await fetch(p, { method: 'POST', body: fd })
    if (!res.ok) {
      let detail = res.statusText
      try { const d = await res.json(); detail = d.detail || JSON.stringify(d) } catch { /* */ }
      throw new ApiError(res.status, detail)
    }
    return res.json() as Promise<T>
  },
}
