import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, Fingerprint, MessageSquare, Send } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import ProvenanceDrawer from '../components/ProvenanceDrawer'

const STOP = new Set(['that', 'with', 'this', 'have', 'from', 'were', 'been', 'they', 'their', 'which', 'there', 'would', 'could', 'institution', 'college', 'students', 'student', 'complaint', 'regarding', 'about', 'kindly', 'please', 'under', 'also', 'into', 'more', 'than', 'such', 'only', 'same', 'very', 'shall'])

function tokens(text: string) {
  return new Set((text || '').toLowerCase().match(/[a-z]{5,}/g)?.filter((w) => !STOP.has(w)) || [])
}

function HighlightedText({ text, shared }: { text: string; shared: Set<string> }) {
  const parts = (text || '').split(/(\b)/)
  return (
    <div className="text-sm text-muted mt-2 max-h-56 overflow-y-auto whitespace-pre-wrap pr-1">
      {parts.map((part, index) => {
        const isWord = /^[A-Za-z]{5,}$/.test(part) && shared.has(part.toLowerCase())
        return isWord ? <mark key={index} className="bg-amber-200/70 text-heading rounded-sm px-0.5">{part}</mark> : <span key={index}>{part}</span>
      })}
    </div>
  )
}

export default function OverlapAlerts() {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState<number | null>(null)
  const [traceCase, setTraceCase] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const { data } = useQuery({ queryKey: ['overlaps'], queryFn: async () => (await api.get('/overlaps')).data })
  const { data: detail } = useQuery({ queryKey: ['overlap', expanded], queryFn: async () => (await api.get(`/overlaps/${expanded}`)).data, enabled: !!expanded })
  const sharedTokens = useMemo(() => {
    const caseList = detail?.cases || []
    if (caseList.length < 2) return new Set<string>()
    const sets = caseList.map((c: any) => tokens(c.narrative))
    return new Set([...sets[0]].filter((word: string) => sets.every((set: Set<string>) => set.has(word))))
  }, [detail])
  const ack = useMutation({
    mutationFn: async (id: number) => (await api.post(`/overlaps/${id}/acknowledge`, { remarks: 'Reviewed in coordination view' })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['overlaps'] }); qc.invalidateQueries({ queryKey: ['overlap'] }) },
  })
  const review = useMutation({
    mutationFn: async ({ id, reason }: { id: number; reason: string }) => (await api.post(`/overlaps/${id}/review-no-action`, { reason })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['overlaps'] }); qc.invalidateQueries({ queryKey: ['overlap'] }) },
  })
  const postMessage = useMutation({
    mutationFn: async ({ id, text }: { id: number; text: string }) => (await api.post(`/overlaps/${id}/thread`, { message: text })).data,
    onSuccess: () => {
      setMessage('')
      qc.invalidateQueries({ queryKey: ['overlap', expanded] })
    },
  })
  const download = async (id: number) => {
    const res = await api.get(`/overlaps/${id}/evidence-pack`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `evidence-pack-alert-${id}.pdf`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Overlap Alerts</h1>
        <p className="text-sm text-muted">Cross-bureau coordination required</p>
      </div>
      <div className="space-y-3">
        {data?.map((a: any) => (
          <div key={a.id} className="bg-card-bg border border-alert-border rounded-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-medium text-heading">{a.institution?.name} ({a.institution?.aicte_permanent_id})</div>
                <div className="text-sm text-muted mt-1">{a.why_flagged}</div>
                <div className="text-sm text-muted mt-1">Bureaus: {a.bureaus_involved?.join(', ')} · Cases: {a.case_ids?.length}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2 py-0.5 rounded-full text-xs bg-alert-bg text-alert-text border border-alert-border">{a.status}</span>
                {a.escalated_at && <span className="px-2 py-0.5 rounded-full text-xs bg-red-50 text-red-700 border border-red-200">ESCALATED TO MANAGEMENT · {a.escalated_at.slice(0, 10)}</span>}
                <button onClick={() => { setExpanded(expanded === a.id ? null : a.id); setMessage('') }} className="px-3 py-1.5 rounded-lg text-sm border border-card-border">{expanded === a.id ? 'Hide' : 'Open'} cases</button>
                <button onClick={() => download(a.id)} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-card-border"><Download size={14} /> Evidence PDF</button>
                <button onClick={() => ack.mutate(a.id)} disabled={ack.isPending} className="px-3 py-1.5 rounded-lg text-sm bg-primary text-white disabled:opacity-50">Acknowledge</button>
                <button onClick={() => { const reason = window.prompt('Mandatory reason for no coordination action'); if (reason) review.mutate({ id: a.id, reason }) }} className="px-3 py-1.5 rounded-lg text-sm border border-card-border">Reviewed – no action</button>
              </div>
            </div>
            {expanded === a.id && detail && (
              <div className="mt-4 border-t border-card-border pt-4 space-y-3">
                <div className="text-xs text-muted">Audit chain across cases: <span className={detail.audit_chain_valid ? 'text-success-text font-medium' : 'text-red-700 font-medium'}>{detail.audit_chain_valid ? 'VALID' : 'CHECK REQUIRED'}</span></div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  {detail.cases?.map((c: any) => (
                    <div key={c.id} className="border border-card-border rounded-lg p-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-heading">{c.case_id}</div>
                        <SourceBadge type={c.source_type} name={c.source_name} />
                      </div>
                      <div className="text-xs text-muted mt-1">{c.bureau_code} · {c.category?.replace(/_/g, ' ')}{c.category_subtype ? ` / ${c.category_subtype.replace(/_/g, ' ')}` : ''} · {c.status} · {c.date_received?.slice(0, 10)}</div>
                      <div className="text-xs text-muted mt-1">{c.subject || 'No subject'} · {c.complainant_type?.replace(/_/g, ' ') || 'unknown complainant'}</div>
                      <HighlightedText text={c.narrative} shared={sharedTokens} />
                      <div className="flex items-center justify-between mt-2">
                        <div className="text-xs text-muted">Outcome: {c.outcome_tag || 'not tagged'}</div>
                        <button onClick={() => setTraceCase(c.id)} className="inline-flex items-center gap-1 text-xs text-heading hover:underline"><Fingerprint size={13} /> Trace</button>
                      </div>
                    </div>
                  ))}
                </div>
                {detail.why_flagged && <div className="text-sm text-muted">Why flagged: {detail.why_flagged}</div>}
                <div className="border-t border-card-border pt-4 space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-heading"><MessageSquare size={15} /> Coordination thread</div>
                  <div className="space-y-2">
                    {detail.thread?.length ? detail.thread.map((entry: any) => (
                      <div key={entry.id} className="rounded-lg border border-card-border bg-page-bg/50 px-3 py-2">
                        <div className="text-xs text-muted">{entry.author || 'Unknown user'}{entry.bureau_code ? ` · ${entry.bureau_code}` : ''} · {entry.created_at?.replace('T', ' ').slice(0, 16)}</div>
                        <div className="text-sm text-heading mt-1 whitespace-pre-wrap">{entry.message}</div>
                      </div>
                    )) : <div className="text-sm text-muted">No coordination notes yet.</div>}
                  </div>
                  <form onSubmit={(event) => { event.preventDefault(); if (message.trim()) postMessage.mutate({ id: a.id, text: message.trim() }) }} className="space-y-2">
                    <textarea value={message} onChange={(event) => setMessage(event.target.value)} rows={2} placeholder="Post a coordination note for the involved bureaus…" className="w-full border border-card-border rounded-lg px-3 py-2 text-sm bg-white" />
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs text-muted">Visible to all officers handling this alert.</div>
                      <button type="submit" disabled={!message.trim() || postMessage.isPending} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary text-white text-sm disabled:opacity-50"><Send size={13} /> {postMessage.isPending ? 'Posting…' : 'Post note'}</button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        ))}
        {!data?.length && <div className="bg-card-bg border border-card-border rounded-card p-6 text-sm text-muted">No overlap alerts. Use the demo scenario on Data Sources to create a cross-bureau overlap through the ingestion pipeline.</div>}
      </div>
      <ProvenanceDrawer caseId={traceCase} onClose={() => setTraceCase(null)} />
    </div>
  )
}
