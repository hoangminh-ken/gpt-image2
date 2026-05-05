import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefInputHybrid } from '../components/RefInputHybrid'
import { useCreateJob } from '../hooks/useJobs'

export function NewJob() {
  const [name, setName] = useState('')
  const [prompt, setPrompt] = useState('')
  const [refs, setRefs] = useState<string[]>([])
  const create = useCreateJob()
  const nav = useNavigate()

  const canSubmit = name.trim() && prompt.trim() && refs.length > 0 && !create.isPending

  const submit = async () => {
    const job = await create.mutateAsync({
      name: name.trim(),
      mode: 'template',
      template_prompt: prompt,
      ref_paths: refs,
    })
    nav(`/jobs/${job.id}`)
  }

  // Rough estimate: $0.07 per medium 1024x1024 (observed in Phase 1 smoke)
  const estimateUsd = refs.length * 0.07

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-semibold">New Job — Mode A (template + refs broadcast)</h1>

      <div className="bg-white rounded-lg border border-slate-200 p-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Job name</label>
          <input
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            placeholder="e.g., gift-card-mockups-v1"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Template prompt</label>
          <textarea
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm font-mono min-h-[160px]"
            placeholder="Describe the desired transformation. Each reference image gets this same prompt."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </div>

        <RefInputHybrid paths={refs} onChange={setRefs} />

        <div className="border-t border-slate-200 pt-4 flex items-center justify-between">
          <div className="text-sm text-slate-600">
            {refs.length > 0 ? (
              <>Will generate <strong>{refs.length}</strong> image(s) · est. <span className="tabular-nums">~${estimateUsd.toFixed(2)}</span></>
            ) : (
              <span className="text-slate-400">Add at least one reference image</span>
            )}
          </div>
          <button
            disabled={!canSubmit}
            onClick={submit}
            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-md text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {create.isPending ? 'Submitting…' : 'Create Job'}
          </button>
        </div>
        {create.error && (
          <div className="text-sm text-rose-600">Error: {(create.error as Error).message}</div>
        )}
      </div>
    </div>
  )
}
