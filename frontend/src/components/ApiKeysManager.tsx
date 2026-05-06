import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { keysApi, type ApiKeyOut } from '../api/jobs'

interface TestResult { ok: boolean; error?: string; models_sample?: string[] }

export function ApiKeysManager() {
  const qc = useQueryClient()
  const { data: keys = [] } = useQuery({ queryKey: ['keys'], queryFn: keysApi.list })
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState('')
  const [keyVal, setKeyVal] = useState('')
  const [testResults, setTestResults] = useState<Record<number, TestResult>>({})

  const create = useMutation({
    mutationFn: keysApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['keys'] }); setAdding(false); setName(''); setKeyVal('') },
  })
  const update = useMutation({
    mutationFn: (args: { id: number; body: { name?: string; enabled?: boolean } }) =>
      keysApi.update(args.id, args.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['keys'] }),
  })
  const del = useMutation({
    mutationFn: keysApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['keys'] }),
  })
  const test = useMutation({
    mutationFn: keysApi.test,
    onSuccess: (r, id) => setTestResults((p) => ({ ...p, [id as number]: r })),
  })

  const enabledCount = keys.filter((k) => k.enabled).length
  const totalCapacity = enabledCount > 0 ? enabledCount * 5 : 5  // 5 = default per-key concurrency

  return (
    <div className="space-y-3">
      <div className="text-xs text-slate-600">
        {enabledCount === 0
          ? <>No keys here yet — using single key from <code>.env</code> (effective concurrency: 5).</>
          : <>{enabledCount} enabled key(s) → effective parallel capacity: <strong>{totalCapacity}</strong> requests
              {' '}(round-robin distribution across keys; each gets ~5 concurrent).</>}
      </div>

      <ul className="divide-y divide-slate-100 border border-slate-200 rounded">
        {keys.length === 0 && (
          <li className="p-4 text-sm text-slate-400 text-center">No keys added.</li>
        )}
        {keys.map((k) => {
          const tr = testResults[k.id]
          const cooled = k.rate_limited_until && new Date(k.rate_limited_until) > new Date()
          return (
            <li key={k.id} className="p-3 flex items-center gap-3 flex-wrap">
              <input
                type="checkbox"
                checked={k.enabled}
                onChange={(e) => update.mutate({ id: k.id, body: { enabled: e.target.checked } })}
                title={k.enabled ? 'Enabled — click to disable' : 'Disabled — click to enable'}
              />
              <NameEditor k={k} onSave={(n) => update.mutate({ id: k.id, body: { name: n } })} />
              <span className="font-mono text-xs text-slate-500">{k.key_masked}</span>
              {cooled && (
                <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
                  cooling down until {new Date(k.rate_limited_until!).toLocaleTimeString()}
                </span>
              )}
              <div className="flex-1" />
              <button
                onClick={() => test.mutate(k.id)}
                disabled={test.isPending}
                className="text-xs px-2 py-1 border border-slate-300 rounded hover:bg-slate-50 disabled:opacity-50"
              >
                {test.isPending && test.variables === k.id ? 'Testing…' : 'Test'}
              </button>
              <button
                onClick={() => { if (confirm(`Delete key "${k.name}"?`)) del.mutate(k.id) }}
                className="text-xs px-2 py-1 border border-rose-300 text-rose-700 hover:bg-rose-50 rounded"
              >
                Delete
              </button>
              {tr && (
                <div className={`w-full text-xs mt-1 px-2 py-1 rounded ${tr.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-rose-50 text-rose-700'}`}>
                  {tr.ok ? <>✓ valid · {tr.models_sample?.slice(0, 3).join(', ')}</> : <>✗ {tr.error}</>}
                </div>
              )}
            </li>
          )
        })}
      </ul>

      {adding ? (
        <div className="bg-blue-50 border border-blue-200 rounded p-3 space-y-2">
          <input
            placeholder="Friendly name (e.g. 'Personal acct A')"
            className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
            value={name} onChange={(e) => setName(e.target.value)} autoFocus
          />
          <input
            type="password"
            placeholder="sk-proj-..."
            className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm font-mono"
            value={keyVal} onChange={(e) => setKeyVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && name.trim() && keyVal.trim()) create.mutate({ name: name.trim(), key: keyVal.trim() }) }}
          />
          <div className="flex gap-2">
            <button
              onClick={() => create.mutate({ name: name.trim(), key: keyVal.trim() })}
              disabled={!name.trim() || !keyVal.trim() || create.isPending}
              className="text-xs px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50"
            >
              {create.isPending ? 'Adding…' : 'Add key'}
            </button>
            <button
              onClick={() => { setAdding(false); setName(''); setKeyVal('') }}
              className="text-xs px-3 py-1.5 border border-slate-300 rounded hover:bg-slate-50"
            >
              Cancel
            </button>
            {create.error && <span className="text-xs text-rose-600 self-center">{(create.error as Error).message}</span>}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="text-xs px-3 py-1.5 border border-slate-300 rounded hover:bg-slate-50"
        >
          + Add API key
        </button>
      )}
    </div>
  )
}

function NameEditor({ k, onSave }: { k: ApiKeyOut; onSave: (n: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [v, setV] = useState(k.name)
  if (!editing) {
    return (
      <button className="font-medium text-sm text-slate-800 hover:underline" onClick={() => { setV(k.name); setEditing(true) }}>
        {k.name}
      </button>
    )
  }
  return (
    <input
      value={v} onChange={(e) => setV(e.target.value)}
      onBlur={() => { setEditing(false); if (v.trim() && v !== k.name) onSave(v.trim()) }}
      onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
      autoFocus
      className="border border-slate-300 rounded px-2 py-0.5 text-sm w-40"
    />
  )
}
