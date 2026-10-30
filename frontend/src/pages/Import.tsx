import { useState } from 'react'
import api from '../lib/api'

type ImportResult = { target: string; data?: any; error?: string }

function ResultPanel({ result }: { result: ImportResult | null }) {
  if (!result) return null
  return (
    <div className={`bg-card-bg border rounded-card p-5 ${result.error ? 'border-red-200' : 'border-card-border'}`}>
      <div className="font-medium text-heading mb-2">{result.target} result</div>
      <pre className="text-sm text-muted whitespace-pre-wrap">{JSON.stringify(result.error ? { error: result.error } : result.data, null, 2)}</pre>
    </div>
  )
}

export default function Import() {
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [jsonFile, setJsonFile] = useState<File | null>(null)
  const [masterFile, setMasterFile] = useState<File | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [loading, setLoading] = useState('')

  const uploadCsv = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!csvFile) return
    setLoading('csv')
    const form = new FormData()
    form.append('file', csvFile)
    try {
      const res = await api.post('/ingest/csv', form)
      setResult({ target: 'CSS/CPGRAMS CSV ingestion', data: res.data })
    } catch (err: any) {
      setResult({ target: 'CSS/CPGRAMS CSV ingestion', error: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setLoading('')
    }
  }

  const uploadJson = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!jsonFile) return
    setLoading('json')
    try {
      const parsed = JSON.parse(await jsonFile.text())
      const items = Array.isArray(parsed) ? parsed : parsed.items
      if (!Array.isArray(items)) throw new Error('JSON must be an array of cases or an object with an items array')
      const res = await api.post('/ingest/json', { items })
      setResult({ target: 'JSON case ingestion', data: res.data })
    } catch (err: any) {
      setResult({ target: 'JSON case ingestion', error: err.response?.data?.detail || err.message || 'Upload failed' })
    } finally {
      setLoading('')
    }
  }

  const uploadMaster = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!masterFile) return
    setLoading('master')
    const form = new FormData()
    form.append('file', masterFile)
    try {
      const res = await api.post('/sources/institution_master/upload', form)
      setResult({ target: 'Institution master upload', data: res.data })
    } catch (err: any) {
      setResult({ target: 'Institution master upload', error: err.response?.data?.detail || 'Upload failed' })
    } finally {
      setLoading('')
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Data Import</h1>
        <p className="text-sm text-muted">Upload case extracts, JSON batches or the institution master</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <form onSubmit={uploadCsv} className="bg-card-bg border border-card-border rounded-card p-5 space-y-3">
          <div>
            <div className="font-medium text-heading">CSS/CPGRAMS CSV</div>
            <div className="text-xs text-muted mt-1">Case-level extract with case_id, institution, narrative, category and bureau columns.</div>
          </div>
          <input type="file" accept=".csv" onChange={(event) => setCsvFile(event.target.files?.[0] || null)} className="w-full text-sm" />
          <button disabled={loading === 'csv' || !csvFile} className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-60">{loading === 'csv' ? 'Uploading…' : 'Upload & ingest CSV'}</button>
        </form>

        <form onSubmit={uploadJson} className="bg-card-bg border border-card-border rounded-card p-5 space-y-3">
          <div>
            <div className="font-medium text-heading">JSON case import</div>
            <div className="text-xs text-muted mt-1">Accepts a JSON array or an object with an <code>items</code> array. Each item needs a <code>case_id</code>.</div>
          </div>
          <input type="file" accept=".json,application/json" onChange={(event) => setJsonFile(event.target.files?.[0] || null)} className="w-full text-sm" />
          <button disabled={loading === 'json' || !jsonFile} className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-60">{loading === 'json' ? 'Uploading…' : 'Upload & ingest JSON'}</button>
        </form>

        <form onSubmit={uploadMaster} className="bg-card-bg border border-card-border rounded-card p-5 space-y-3">
          <div>
            <div className="font-medium text-heading">Institution master</div>
            <div className="text-xs text-muted mt-1">CSV or XLSX master with AICTE Permanent ID, institute name and optional first GRC resolution days.</div>
          </div>
          <input type="file" accept=".csv,.xlsx" onChange={(event) => setMasterFile(event.target.files?.[0] || null)} className="w-full text-sm" />
          <button disabled={loading === 'master' || !masterFile} className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-60">{loading === 'master' ? 'Uploading…' : 'Upload master'}</button>
        </form>
      </div>

      <ResultPanel result={result} />
    </div>
  )
}
