import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { jobsApi, type ExcelParseResult } from '../api/jobs'
import { ExcelPreviewTable } from '../components/ExcelPreviewTable'
import { ExcelUpload } from '../components/ExcelUpload'
import { PromptPicker } from '../components/PromptPicker'
import { RefInputHybrid } from '../components/RefInputHybrid'
import { useCreateJob } from '../hooks/useJobs'

type Tab = 'template' | 'excel'
const PRICE_PER_IMAGE = 0.07

export function NewJob() {
  const [tab, setTab] = useState<Tab>('template')
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-semibold">New Job</h1>
      <div className="flex border-b border-slate-200">
        {(['template', 'excel'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === t ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {t === 'template' ? 'Mode A: Template + Refs' : 'Mode B: Excel'}
          </button>
        ))}
      </div>
      {tab === 'template' ? <TemplateForm /> : <ExcelForm />}
    </div>
  )
}

function TemplateForm() {
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const [refs, setRefs] = useState<string[]>([])
  const create = useCreateJob()
  const nav = useNavigate()

  const canSubmit = name.trim() && prompt.trim() && refs.length > 0 && !create.isPending
  const submit = async () => {
    const job = await create.mutateAsync({
      name: name.trim(), mode: 'template',
      template_prompt: prompt, ref_paths: refs,
    })
    nav(`/jobs/${job.id}`)
  }
  const estimate = refs.length * PRICE_PER_IMAGE

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Job name</label>
        <input
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={name} onChange={(e) => setName(e.target.value)}
          placeholder="e.g., gift-card-mockups-v1"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Template prompt</label>
        <textarea
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm font-mono min-h-[160px]"
          value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder="One prompt applied to each reference image."
        />
      </div>
      <PromptPicker value={prompt} onChange={setPrompt} />
      <RefInputHybrid paths={refs} onChange={setRefs} />
      <div className="border-t border-slate-200 pt-4 flex items-center justify-between">
        <div className="text-sm text-slate-600">
          {refs.length > 0
            ? <>Will generate <strong>{refs.length}</strong> image(s) · est. <span className="tabular-nums">~${estimate.toFixed(2)}</span></>
            : <span className="text-slate-400">Add at least one reference image</span>}
        </div>
        <button
          disabled={!canSubmit} onClick={submit}
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-md text-sm font-medium disabled:opacity-50"
        >
          {create.isPending ? 'Submitting…' : 'Create Job'}
        </button>
      </div>
      {create.error && <div className="text-sm text-rose-600">Error: {(create.error as Error).message}</div>}
    </div>
  )
}

function ExcelForm() {
  const [name, setName] = useState('')
  const [parsed, setParsed] = useState<ExcelParseResult | null>(null)
  const [skipInvalid, setSkipInvalid] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const nav = useNavigate()

  const validRows = parsed?.rows.filter((r) => r.valid) ?? []
  const willCreate = skipInvalid ? validRows.length : (parsed?.rows.length ?? 0)
  const allValid = parsed && parsed.summary.invalid === 0
  const canSubmit = name.trim() && parsed && (allValid || skipInvalid) && willCreate > 0 && !submitting

  const submit = async () => {
    if (!parsed) return
    setSubmitting(true); setError(null)
    try {
      const rows = (skipInvalid ? validRows : parsed.rows).map((r) => ({
        prompt: r.prompt, refs: r.refs, output_name: r.output_name,
      }))
      const job = await jobsApi.createExcelJob({
        name: name.trim(), mode: 'excel', rows, skip_invalid: skipInvalid,
      })
      nav(`/jobs/${job.id}`)
    } catch (err: unknown) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }
  const estimate = willCreate * PRICE_PER_IMAGE

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Job name</label>
        <input
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          value={name} onChange={(e) => setName(e.target.value)}
          placeholder="e.g., catalog-batch-2026-05"
        />
      </div>
      <ExcelUpload onParsed={setParsed} />
      {parsed && <ExcelPreviewTable result={parsed} skipInvalid={skipInvalid} onSkipChange={setSkipInvalid} />}
      {parsed && (
        <div className="border-t border-slate-200 pt-4 flex items-center justify-between">
          <div className="text-sm text-slate-600">
            Will create <strong>{willCreate}</strong> image(s) · est. <span className="tabular-nums">~${estimate.toFixed(2)}</span>
          </div>
          <button
            disabled={!canSubmit} onClick={submit}
            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-md text-sm font-medium disabled:opacity-50"
          >
            {submitting ? 'Submitting…' : 'Create Job'}
          </button>
        </div>
      )}
      {error && <div className="text-sm text-rose-600">Error: {error}</div>}
    </div>
  )
}
