import { useState } from 'react'
import api from '../lib/api'

export default function Import() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const upload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await api.post('/ingest/csv', form)
      setResult(res.data)
    } catch (err: any) {
      setResult({ error: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Data Import</h1>
        <p className="text-sm text-muted">Upload CSS/CPGRAMS CSV extracts</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-5">
        <form onSubmit={upload} className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm mb-1 text-heading">CSV File</label>
            <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} className="w-full text-sm" />
          </div>
          <button disabled={loading || !file} className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-60">{loading ? 'Uploading...' : 'Upload & Ingest'}</button>
        </form>
      </div>
      {result && (
        <div className="bg-card-bg border border-card-border rounded-card p-5">
          <div className="font-medium text-heading mb-2">Ingestion Result</div>
          <pre className="text-sm text-muted">{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
