import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { Download, Fingerprint } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import RiskGauge from '../components/RiskGauge'
import ProvenanceDrawer from '../components/ProvenanceDrawer'

export default function Institution360() {
  const { id } = useParams()
  const [traceCase, setTraceCase] = useState<number | null>(null)
  const [downloading, setDownloading] = useState(false)
  const { data } = useQuery({ queryKey: ['inst360', id], queryFn: async () => (await api.get(`/institutions/${id}/360`)).data })
  if (!data) return <div>Loading...</div>
  const downloadBrief = async () => {
    setDownloading(true)
    try {
      const res = await api.get(`/institutions/${id}/brief`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `institution-brief-${data.institution.aicte_permanent_id}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-semibold text-heading">{data.institution.name}</h1>
            <SourceBadge type={data.institution.source_type} />
          </div>
          <p className="text-sm text-muted">{data.institution.aicte_permanent_id} · {data.institution.address} · {data.institution.region}</p>
        </div>
        <button onClick={downloadBrief} disabled={downloading} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm bg-primary text-white disabled:opacity-50">
          <Download size={16} /> {downloading ? 'Building…' : 'Institution brief PDF'}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
        <div className="bg-card-bg border border-card-border rounded-card p-4"><div className="text-sm text-muted">Total Cases</div><div className="text-xl font-semibold">{data.regulatory_posture.total_cases}</div></div>
        <div className="bg-card-bg border border-card-border rounded-card p-4"><div className="text-sm text-muted">Active</div><div className="text-xl font-semibold">{data.regulatory_posture.active}</div></div>
        <div className="bg-card-bg border border-card-border rounded-card p-4"><div className="text-sm text-muted">Disposed</div><div className="text-xl font-semibold">{data.regulatory_posture.disposed}</div></div>
        <div className="bg-card-bg border border-card-border rounded-card p-4"><div className="text-sm text-muted">Overlap Alerts</div><div className="text-xl font-semibold">{data.regulatory_posture.overlap_alerts}</div></div>
        <div className="bg-card-bg border border-card-border rounded-card p-4"><div className="text-sm text-muted">First GRC resolution</div><div className="text-xl font-semibold">{data.institution.grc_first_resolution_days != null ? `${data.institution.grc_first_resolution_days} days` : 'Unknown'}</div></div>
        <div className="bg-card-bg border border-card-border rounded-card p-4 flex items-center gap-3"><RiskGauge score={data.risk.score} size={62} /><div><div className="text-sm text-muted">Risk score</div><div className="text-xs text-muted">Transparent weighted</div></div></div>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card">
        <div className="px-5 py-4 border-b border-card-border">
          <div className="font-medium text-heading">Risk score breakdown</div>
          <div className="text-xs text-muted">{data.risk.note}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg"><tr><th className="text-left px-5 py-2 text-muted font-medium">Component</th><th className="text-left px-5 py-2 text-muted font-medium">Raw value</th><th className="text-left px-5 py-2 text-muted font-medium">Weight</th><th className="text-left px-5 py-2 text-muted font-medium">Points</th></tr></thead>
            <tbody>
              {data.risk.breakdown.map((b: any) => (
                <tr key={b.component} className="border-t border-card-border"><td className="px-5 py-2">{b.component}</td><td className="px-5 py-2">{b.raw_value}</td><td className="px-5 py-2">{b.weight}</td><td className="px-5 py-2">{b.points}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card">
        <div className="px-5 py-4 border-b border-card-border font-medium text-heading">All Cases (Cross-bureau)</div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg">
              <tr><th className="text-left px-5 py-2 text-muted">Case ID</th><th className="text-left px-5 py-2 text-muted">Source</th><th className="text-left px-5 py-2 text-muted">Bureau</th><th className="text-left px-5 py-2 text-muted">Category</th><th className="text-left px-5 py-2 text-muted">Status</th><th className="text-left px-5 py-2 text-muted">Received</th><th className="text-left px-5 py-2 text-muted">Trace</th></tr>
            </thead>
            <tbody>
              {data.cases.map((c: any) => (
                <tr key={c.id} className="border-t border-card-border"><td className="px-5 py-3">{c.case_id}</td><td className="px-5 py-3"><SourceBadge type={c.source_type} name={c.source_name} compact /></td><td className="px-5 py-3">{c.bureau_code}</td><td className="px-5 py-3">{c.category}</td><td className="px-5 py-3">{c.status}</td><td className="px-5 py-3 text-muted">{c.date_received?.slice(0,10)}</td><td className="px-5 py-3"><button onClick={() => setTraceCase(c.id)} className="inline-flex items-center gap-1 text-xs text-heading hover:underline"><Fingerprint size={13} /> Trace</button></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card">
        <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Timeline (Merged)</div>
        <div className="p-5 space-y-3">
          {data.timeline?.map((t: any, idx: number) => (
            <div key={idx} className="flex gap-4">
              <div className="w-32 text-xs text-muted">{t.created_at?.replace('T',' ').slice(0,16)}</div>
              <div className="flex-1">
                <div className="text-sm text-heading">{t.action_type} · {t.bureau || ''}</div>
                <div className="text-sm text-muted">{t.remarks}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <ProvenanceDrawer caseId={traceCase} onClose={() => setTraceCase(null)} />
    </div>
  )
}
