import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { promptsApi, type SavedPrompt } from '../api/jobs'

interface Props {
  value: string
  onChange: (content: string) => void
  /** When user picks a saved prompt, also fires for "use count" tracking. */
  onApplied?: (prompt: SavedPrompt) => void
}

export function PromptPicker({ value, onChange, onApplied }: Props) {
  const qc = useQueryClient()
  const { data: prompts } = useQuery({
    queryKey: ['prompts'],
    queryFn: promptsApi.list,
  })
  const [picking, setPicking] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveName, setSaveName] = useState('')

  const create = useMutation({
    mutationFn: promptsApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  })
  const useMut = useMutation({
    mutationFn: promptsApi.use,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  })
  const del = useMutation({
    mutationFn: promptsApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  })

  const apply = (p: SavedPrompt) => {
    onChange(p.content)
    useMut.mutate(p.id)
    onApplied?.(p)
    setPicking(false)
  }

  const saveCurrent = () => {
    if (!value.trim() || !saveName.trim()) return
    create.mutate({ name: saveName.trim(), content: value }, {
      onSuccess: () => {
        setSaving(false)
        setSaveName('')
      },
    })
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        <label className="block text-sm font-medium text-slate-700">Saved prompts</label>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => setPicking((v) => !v)}
          className="text-xs px-3 py-1 border border-slate-300 rounded hover:bg-slate-50"
        >
          📚 Library ({prompts?.length ?? 0})
        </button>
        <button
          type="button"
          onClick={() => setSaving(true)}
          disabled={!value.trim()}
          className="text-xs px-3 py-1 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50"
        >
          💾 Save current as…
        </button>
      </div>

      {saving && (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 flex items-center gap-2 flex-wrap">
          <input
            autoFocus
            placeholder="Name for this prompt (e.g. 'concrete-bg-v1')"
            className="border border-slate-300 rounded px-3 py-1.5 text-sm flex-1 min-w-[240px]"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') saveCurrent() }}
          />
          <button
            onClick={saveCurrent}
            disabled={!saveName.trim() || create.isPending}
            className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50"
          >
            {create.isPending ? 'Saving…' : 'Save'}
          </button>
          <button
            onClick={() => { setSaving(false); setSaveName('') }}
            className="text-xs px-3 py-1.5 border border-slate-300 rounded hover:bg-slate-50"
          >
            Cancel
          </button>
          {create.error && <span className="text-xs text-rose-600 w-full">{(create.error as Error).message}</span>}
        </div>
      )}

      {picking && (
        <div className="border border-slate-200 rounded max-h-72 overflow-y-auto bg-white">
          {!prompts || prompts.length === 0 ? (
            <div className="p-4 text-sm text-slate-500 text-center">
              No saved prompts yet. Type one above and click "Save current as…".
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {prompts.map((p) => (
                <li key={p.id} className="p-3 hover:bg-slate-50">
                  <div className="flex items-start gap-2">
                    <button
                      type="button"
                      onClick={() => apply(p)}
                      className="flex-1 text-left"
                    >
                      <div className="font-medium text-sm text-slate-800">{p.name}</div>
                      <div className="text-xs text-slate-500 line-clamp-2 mt-0.5">{p.content}</div>
                      <div className="text-[10px] text-slate-400 mt-1">used {p.used_count}× · {p.content.length} chars</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Delete "${p.name}"?`)) del.mutate(p.id)
                      }}
                      className="text-xs px-2 py-1 text-rose-600 hover:bg-rose-50 rounded"
                      title="Delete"
                    >
                      ✕
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
