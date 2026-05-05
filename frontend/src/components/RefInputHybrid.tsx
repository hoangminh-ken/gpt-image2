import { useCallback, useState } from 'react'
import { jobsApi } from '../api/jobs'
import { Thumbnail } from './Thumbnail'

interface Props {
  paths: string[]
  onChange: (paths: string[]) => void
}

export function RefInputHybrid({ paths, onChange }: Props) {
  const [text, setText] = useState(paths.join('\n'))
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const syncFromText = useCallback((value: string) => {
    setText(value)
    const lines = value.split('\n').map((l) => l.trim()).filter(Boolean)
    onChange(lines)
  }, [onChange])

  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files).filter((f) => f.type.startsWith('image/'))
    if (files.length === 0) {
      setError('Drop image files only')
      return
    }
    setError(null)
    setUploading(true)
    try {
      const res = await jobsApi.uploadRefs(files)
      const newPaths = res.files.map((f) => f.abs_path)
      const merged = [...paths, ...newPaths]
      onChange(merged)
      setText(merged.join('\n'))
    } catch (err: unknown) {
      setError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }, [paths, onChange])

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-700">
        Reference image paths
      </label>
      <textarea
        className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm font-mono min-h-[120px]"
        placeholder="Paste absolute paths, one per line. e.g.:&#10;C:\Users\me\refs\hero.png"
        value={text}
        onChange={(e) => syncFromText(e.target.value)}
      />
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        className="border-2 border-dashed border-slate-300 rounded-md p-6 text-center text-sm text-slate-500 bg-slate-50 hover:border-blue-400 transition"
      >
        {uploading ? 'Uploading…' : '📥 Drag image files here to upload (alternative to typing paths)'}
      </div>
      {error && <div className="text-xs text-rose-600">{error}</div>}
      {paths.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2">
          {paths.map((p, i) => (
            <div key={p + i} title={p}>
              <Thumbnail path={p} size={48} />
            </div>
          ))}
          <span className="text-xs text-slate-500 self-center">{paths.length} image(s)</span>
        </div>
      )}
    </div>
  )
}
