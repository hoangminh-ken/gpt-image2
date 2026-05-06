import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { settingsApi, type SettingsOut, type SettingsUpdate } from '../api/jobs'
import { ApiKeysManager } from '../components/ApiKeysManager'

interface FormState {
  openai_api_key: string
  openai_admin_key: string
  openai_image_model: string
  default_concurrency: number
  max_ref_dimension: number
}

const EMPTY_FORM: FormState = {
  openai_api_key: '',
  openai_admin_key: '',
  openai_image_model: 'gpt-image-2',
  default_concurrency: 5,
  max_ref_dimension: 2048,
}

export function SettingsPage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
  })

  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [editingApi, setEditingApi] = useState(false)
  const [editingAdmin, setEditingAdmin] = useState(false)
  const [savedNotice, setSavedNotice] = useState<string | null>(null)
  const [restartNotice, setRestartNotice] = useState<string[] | null>(null)
  const [testResult, setTestResult] = useState<{ ok: boolean; error?: string; models_sample?: string[] } | null>(null)

  useEffect(() => {
    if (data) {
      setForm((f) => ({
        ...f,
        openai_image_model: data.openai_image_model,
        default_concurrency: data.default_concurrency,
        max_ref_dimension: data.max_ref_dimension,
      }))
    }
  }, [data])

  const save = useMutation({
    mutationFn: (body: SettingsUpdate) => settingsApi.update(body),
    onSuccess: (res: SettingsOut) => {
      qc.invalidateQueries({ queryKey: ['settings'] })
      setSavedNotice('Saved.')
      setTimeout(() => setSavedNotice(null), 3000)
      setRestartNotice(res.restart_required_for.length > 0 ? res.restart_required_for : null)
      setForm((f) => ({ ...f, openai_api_key: '', openai_admin_key: '' }))
      setEditingApi(false)
      setEditingAdmin(false)
    },
  })

  const test = useMutation({
    mutationFn: settingsApi.testKey,
    onSuccess: (r) => setTestResult(r),
    onError: (e: Error) => setTestResult({ ok: false, error: e.message }),
  })

  const saveApiKey = () => {
    if (!form.openai_api_key.trim()) return
    save.mutate({ openai_api_key: form.openai_api_key.trim() })
  }
  const clearApiKey = () => {
    if (!confirm('Clear OPENAI_API_KEY? You will not be able to generate images until you set a new one.')) return
    save.mutate({ openai_api_key: '' })
  }
  const saveAdminKey = () => {
    save.mutate({ openai_admin_key: form.openai_admin_key })
  }
  const clearAdminKey = () => {
    save.mutate({ openai_admin_key: '' })
  }
  const saveOther = () => {
    save.mutate({
      openai_image_model: form.openai_image_model,
      default_concurrency: form.default_concurrency,
      max_ref_dimension: form.max_ref_dimension,
    })
  }

  if (isLoading || !data) return <div className="text-slate-500 text-sm">Loading…</div>

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <div className="bg-blue-50 border border-blue-200 text-blue-900 text-xs rounded p-3">
        Stored in <code className="text-[11px]">{data.env_file_path}</code>. API key changes apply immediately.
        Concurrency requires app restart to take effect on the worker pool.
      </div>

      {savedNotice && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded p-2">
          ✓ {savedNotice}
        </div>
      )}
      {restartNotice && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 text-sm rounded p-2">
          ⚠ Restart required for: <strong>{restartNotice.join(', ')}</strong>
        </div>
      )}

      <Section title="API keys (multi-key parallelism)">
        <ApiKeysManager />
        <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-100">
          💡 Add multiple keys to multiply parallel capacity. Worker pool concurrency =
          enabled keys × per-key concurrency. Keys getting 429 are auto-cooled for 60s.
          Single-key fallback (.env) is used when no keys are added here.
        </div>
      </Section>

      <Section title="Single key fallback (legacy / .env)">
        <Field label="API key">

          {!editingApi ? (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm">
                {data.openai_api_key_set
                  ? data.openai_api_key_masked
                  : <em className="text-rose-600">unset — generation will fail</em>}
              </span>
              <Btn onClick={() => setEditingApi(true)}>{data.openai_api_key_set ? 'Edit' : 'Set'}</Btn>
              {data.openai_api_key_set && <>
                <Btn onClick={() => test.mutate()} disabled={test.isPending}>
                  {test.isPending ? 'Testing…' : 'Test'}
                </Btn>
                <Btn variant="danger" onClick={clearApiKey} disabled={save.isPending}>Clear</Btn>
              </>}
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="password"
                autoFocus
                placeholder="sk-proj-..."
                className="border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono flex-1 min-w-[280px]"
                value={form.openai_api_key}
                onChange={(e) => setForm({ ...form, openai_api_key: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') saveApiKey() }}
              />
              <Btn variant="primary" onClick={saveApiKey} disabled={!form.openai_api_key.trim() || save.isPending}>
                Save
              </Btn>
              <Btn onClick={() => { setEditingApi(false); setForm({ ...form, openai_api_key: '' }) }}>Cancel</Btn>
            </div>
          )}
          {testResult && (
            <div className={`text-xs mt-2 rounded p-2 ${testResult.ok ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
              {testResult.ok
                ? <>✓ Key valid · sample models: {testResult.models_sample?.slice(0, 3).join(', ')}</>
                : <>✗ {testResult.error}</>}
            </div>
          )}
        </Field>

        <Field label="Admin key (optional, for Cost reconcile)">
          {!editingAdmin ? (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-sm">
                {data.openai_admin_key_set
                  ? data.openai_admin_key_masked
                  : <em className="text-slate-400">unset — Cost reconcile disabled</em>}
              </span>
              <Btn onClick={() => setEditingAdmin(true)}>{data.openai_admin_key_set ? 'Edit' : 'Set'}</Btn>
              {data.openai_admin_key_set && <Btn variant="danger" onClick={clearAdminKey} disabled={save.isPending}>Clear</Btn>}
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="password"
                autoFocus
                placeholder="sk-admin-..."
                className="border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono flex-1 min-w-[280px]"
                value={form.openai_admin_key}
                onChange={(e) => setForm({ ...form, openai_admin_key: e.target.value })}
                onKeyDown={(e) => { if (e.key === 'Enter') saveAdminKey() }}
              />
              <Btn variant="primary" onClick={saveAdminKey} disabled={save.isPending}>Save</Btn>
              <Btn onClick={() => { setEditingAdmin(false); setForm({ ...form, openai_admin_key: '' }) }}>Cancel</Btn>
            </div>
          )}
        </Field>
      </Section>

      <Section title="Worker & model">
        <Field label="Image model">
          <input
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm font-mono w-full max-w-md"
            value={form.openai_image_model}
            onChange={(e) => setForm({ ...form, openai_image_model: e.target.value })}
          />
          <div className="text-[11px] text-slate-500 mt-1">
            Default: <code>gpt-image-2</code>. Pin a snapshot like <code>gpt-image-2-2026-04-21</code> for reproducibility.
          </div>
        </Field>
        <Field label="Default concurrency (1–20)">
          <input
            type="number"
            min={1}
            max={20}
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm w-32 tabular-nums"
            value={form.default_concurrency}
            onChange={(e) => setForm({ ...form, default_concurrency: Number(e.target.value) })}
          />
          <span className="text-[11px] text-amber-700 ml-2">restart required</span>
        </Field>
        <Field label="Max ref image dimension (512–4096 px, longest side)">
          <input
            type="number"
            min={512}
            max={4096}
            step={256}
            className="border border-slate-300 rounded-md px-3 py-1.5 text-sm w-32 tabular-nums"
            value={form.max_ref_dimension}
            onChange={(e) => setForm({ ...form, max_ref_dimension: Number(e.target.value) })}
          />
          <span className="text-[11px] text-slate-500 ml-2">larger refs auto-resized before API call</span>
        </Field>
        <div className="pt-2">
          <Btn variant="primary" onClick={saveOther} disabled={save.isPending}>
            Save model & worker
          </Btn>
        </div>
      </Section>

      <Section title="Storage (read-only)">
        <Field label="Output dir"><code className="text-xs">{data.output_dir}</code></Field>
        <Field label="Upload dir"><code className="text-xs">{data.upload_dir}</code></Field>
      </Section>

      {save.error && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 text-sm rounded p-2">
          Save error: {(save.error as Error).message}
        </div>
      )}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200">
      <div className="px-4 py-2 border-b border-slate-200 text-sm font-medium text-slate-700">{title}</div>
      <div className="p-4 space-y-3">{children}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-slate-600 mb-1">{label}</label>
      <div>{children}</div>
    </div>
  )
}

function Btn({
  children, variant = 'default', ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'primary' | 'danger' }) {
  const cls =
    variant === 'primary'
      ? 'bg-blue-600 hover:bg-blue-700 text-white border-blue-600'
      : variant === 'danger'
        ? 'bg-white hover:bg-rose-50 text-rose-700 border-rose-300'
        : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300'
  return (
    <button {...rest} className={`px-3 py-1.5 text-xs font-medium border rounded disabled:opacity-50 disabled:cursor-not-allowed ${cls}`}>
      {children}
    </button>
  )
}
