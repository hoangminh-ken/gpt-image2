import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api/client'

interface SettingsOut {
  openai_api_key_masked: string
  openai_admin_key_masked: string
  openai_api_key_set: boolean
  openai_admin_key_set: boolean
  default_concurrency: number
  max_ref_dimension: number
  output_dir: string
  upload_dir: string
}

interface TestKeyResult { ok: boolean; error?: string; models_sample?: string[] }

export function SettingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<SettingsOut>('/api/settings'),
  })
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestKeyResult | null>(null)

  const runTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const r = await api.get<TestKeyResult>('/api/settings/test-key')
      setTestResult(r)
    } catch (err: unknown) {
      setTestResult({ ok: false, error: (err as Error).message })
    } finally {
      setTesting(false)
    }
  }

  if (isLoading || !data) return <div className="text-slate-500 text-sm">Loading…</div>

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <div className="bg-amber-50 border border-amber-200 text-amber-900 text-sm rounded p-3">
        Settings are read from <code>backend/.env</code>. To change values, edit the file and restart the backend.
        This page is read-only for safety (writing API keys via UI deferred to a future improvement).
      </div>

      <Section title="OpenAI">
        <Row label="API key">
          <span className="font-mono text-sm">
            {data.openai_api_key_set ? data.openai_api_key_masked : <em className="text-rose-600">unset</em>}
          </span>
          {data.openai_api_key_set && (
            <button
              onClick={runTest}
              disabled={testing}
              className="ml-3 px-3 py-1 text-xs border border-slate-300 rounded hover:bg-slate-100"
            >
              {testing ? 'Testing…' : 'Test key'}
            </button>
          )}
        </Row>
        <Row label="Admin key (Usage API)">
          <span className="font-mono text-sm">
            {data.openai_admin_key_set
              ? data.openai_admin_key_masked
              : <em className="text-slate-400">unset (cost reconcile disabled)</em>}
          </span>
        </Row>
        {testResult && (
          <div className={`text-sm rounded p-2 mt-2 ${testResult.ok ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
            {testResult.ok
              ? <>OK · sample models: {testResult.models_sample?.slice(0, 3).join(', ')}</>
              : <>Error: {testResult.error}</>}
          </div>
        )}
      </Section>

      <Section title="Worker">
        <Row label="Default concurrency"><span className="tabular-nums">{data.default_concurrency}</span></Row>
        <Row label="Max ref dimension"><span className="tabular-nums">{data.max_ref_dimension}px</span></Row>
      </Section>

      <Section title="Storage">
        <Row label="Output dir"><code className="text-xs">{data.output_dir}</code></Row>
        <Row label="Upload dir"><code className="text-xs">{data.upload_dir}</code></Row>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200">
      <div className="px-4 py-2 border-b border-slate-200 text-sm font-medium text-slate-700">{title}</div>
      <div className="p-4 space-y-2">{children}</div>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-600">{label}</span>
      <span>{children}</span>
    </div>
  )
}
