import { useState } from 'react'
import api from '../lib/api'

const reports = ['bureau-wise', 'region-wise', 'institution-wise', 'status-wise', 'ageing', 'disposal-rate', 'overlaps', 'monthly-performance']

export default function Reports() {
  const [type, setType] = useState('bureau-wise')
  const [format, setFormat] = useState('json')
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')

  const fetchReport = async () => {
    setError('')
    try {
      if (format === 'json') {
        const res = await api.get(`/reports/${type}?format=json`)
        setData(res.data)
      } else {
        const res = await api.get(`/reports/${type}?format=${format}`, { responseType: 'blob' })
        const url = window.URL.createObjectURL(new Blob([res.data]))
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `${type}.${format}`)
        document.body.appendChild(link)
        link.click()
        link.remove()
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not generate this report.')
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Reports & Analytics</h1>
        <p className="text-sm text-muted">Generate and export reports</p>
        <p className="text-xs text-muted mt-1">Aggregates use all stored sources. Per-record provenance is available on each case and in Data Sources.</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-5 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm mb-1 text-heading">Report Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)} className="border border-card-border rounded-lg px-3 py-2 text-sm">
            {reports.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm mb-1 text-heading">Format</label>
          <select value={format} onChange={(e) => setFormat(e.target.value)} className="border border-card-border rounded-lg px-3 py-2 text-sm">
            <option value="json">JSON (Preview)</option>
            <option value="csv">CSV</option>
            <option value="xlsx">Excel</option>
            <option value="pdf">PDF</option>
          </select>
        </div>
        <button onClick={fetchReport} className="bg-primary text-white px-4 py-2 rounded-lg text-sm">Generate</button>
      </div>
      {error && <div className="text-sm text-red-700">{error}</div>}
      {data && format === 'json' && (
        <div className="bg-card-bg border border-card-border rounded-card overflow-x-auto">
          <pre className="p-5 text-xs overflow-auto">{JSON.stringify(data.data, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
