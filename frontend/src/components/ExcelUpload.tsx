import { useState } from 'react'
import { jobsApi, type ExcelParseResult } from '../api/jobs'

interface Props {
  onParsed: (result: ExcelParseResult) => void
}

export function ExcelUpload({ onParsed }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filename, setFilename] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setBusy(true)
    setError(null)
    setFilename(file.name)
    try {
      const result = await jobsApi.parseExcel(file)
      onParsed(result)
    } catch (err: unknown) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-700">
        Excel file (.xlsx)
      </label>
      <div className="flex items-center gap-3">
        <label className="bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded px-3 py-2 text-sm cursor-pointer">
          {busy ? 'Parsing…' : 'Choose .xlsx'}
          <input
            type="file"
            className="hidden"
            accept=".xlsx,.xlsm"
            disabled={busy}
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
        </label>
        {filename && <span className="text-sm text-slate-500">{filename}</span>}
      </div>
      <div className="text-xs text-slate-500">
        Required columns: <code>prompt</code>, <code>refs</code>. Optional: <code>output_name</code>.
        Refs separator: <code>|</code>. Max 1000 rows, 10MB.
      </div>
      {error && <div className="text-xs text-rose-600">{error}</div>}
    </div>
  )
}
