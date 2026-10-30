import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { AlertTriangle, Fingerprint, History, Scale, ThumbsDown, ThumbsUp } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import ProvenanceDrawer from '../components/ProvenanceDrawer'

const OUTCOMES = ['DEFICIENCY_CONFIRMED', 'NO_DEFICIENCY', 'PENALTY_PROPOSED', 'APPROVAL_ACTION_PROPOSED', 'CLOSED_NO_ACTION']

export default function CaseDetail() {
  const { id } = useParams()
  const qc = useQueryClient()
  const [traceOpen, setTraceOpen] = useState(false)
  const [outcome, setOutcome] = useState('')
  const [conflicts, setConflicts] = useState<any[]>([])
  const [remarks, setRemarks] = useState('')
  const [error, setError] = useState('')
  const [showOriginal, setShowOriginal] = useState(false)
  const [sameCategory, setSameCategory] = useState(false)
  const [sameInstitution, setSameInstitution] = useState(false)
  const { data } = useQuery({ queryKey: ['case', id], queryFn: async () => (await api.get(`/cases/${id}`)).data })
  const precedents = useQuery({
    queryKey: ['precedents', id, sameCategory, sameInstitution],
    queryFn: async () => (await api.get(`/cases/${id}/precedents`, { params: { limit: 5, same_category: sameCategory, same_institution: sameInstitution } })).data,
    enabled: !!id,
  })
  const precedentFeedback = useMutation({
    mutationFn: async ({ precedentId, feedback }: { precedentId: number; feedback: string }) => (await api.post(`/cases/${id}/precedents/${precedentId}/feedback`, { feedback })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['precedents', id] })
      qc.invalidateQueries({ queryKey: ['case', id] })
    },
  })
  const setOutcomeMutation = useMutation({
    mutationFn: async (payload: { outcome_tag: string; acknowledge_conflict: boolean; remarks: string }) => (await api.post(`/cases/${id}/outcome`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['case', id] })
      setConflicts([])
      setRemarks('')
      setOutcome('')
      setError('')
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409 && detail?.conflicts) {
        setConflicts(detail.conflicts)
        setError('')
      } else {
        setError(typeof detail === 'string' ? detail : 'Could not save outcome')
      }
    },
  })
  const needsTranslation = useMemo(() => data?.narrative_original && data?.narrative_translated && data.narrative_original !== data.narrative_translated, [data])
  if (!data) return <div>Loading...</div>

  const submitOutcome = () => {
    if (!outcome) return
    setOutcomeMutation.mutate({ outcome_tag: outcome, acknowledge_conflict: conflicts.length > 0, remarks })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-xl font-semibold text-heading">{data.case_id}</h1>
            <SourceBadge type={data.source_type} name={data.source_name} />
            {data.is_synthetic && <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200">SYNTHETIC DATA</span>}
          </div>
          <p className="text-sm text-heading mt-1">{data.subject || 'Untitled grievance'}</p>
          <p className="text-sm text-muted">{data.category?.replace(/_/g, ' ')} {data.category_subtype ? `· ${data.category_subtype.replace(/_/g, ' ')}` : ''} · {data.status} · Bureau: {data.bureau?.code}</p>
          {data.complainant_type && <span className="inline-block mt-2 px-2 py-0.5 rounded-full text-xs bg-page-bg border border-card-border text-muted">{data.complainant_type.replace(/_/g, ' ')}</span>}
        </div>
        <button onClick={() => setTraceOpen(true)} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm border border-card-border hover:bg-page-bg">
          <Fingerprint size={16} /> View evidence trail
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Case Details</div>
            <div className="p-5 grid grid-cols-2 gap-4 text-sm">
              <div><div className="text-muted">Source</div><div className="text-heading">{data.source_channel}</div></div>
              <div><div className="text-muted">Source record</div><div className="text-heading">{data.source_record_id || '—'}</div></div>
              <div><div className="text-muted">Date Received</div><div className="text-heading">{data.date_received?.slice(0,10)}</div></div>
              <div><div className="text-muted">Language</div><div className="text-heading uppercase">{data.language || 'en'}</div></div>
              <div><div className="text-muted">Institution</div><div className="text-heading">{data.institution?.name || data.raw_institution_text}</div></div>
              <div><div className="text-muted">AICTE ID</div><div className="text-heading">{data.institution?.aicte_permanent_id || '-'}</div></div>
              <div className="col-span-2"><div className="text-muted">Subject</div><div className="text-heading">{data.subject || '—'}</div></div>
              <div><div className="text-muted">Category</div><div className="text-heading">{data.category?.replace(/_/g, ' ')}</div></div>
              <div><div className="text-muted">Sub-type</div><div className="text-heading">{data.category_subtype?.replace(/_/g, ' ') || '—'}</div></div>
              <div><div className="text-muted">Complainant</div><div className="text-heading">{data.complainant_type?.replace(/_/g, ' ') || '—'}</div></div>
              <div><div className="text-muted">Synthetic</div><div className="text-heading">{data.is_synthetic ? 'Yes — SYNTHETIC DATA' : 'No'}</div></div>
              <div className="col-span-2 border-t border-card-border pt-4">
                {needsTranslation && (
                  <div className="flex items-center gap-2 mb-2">
                    <button onClick={() => setShowOriginal(false)} className={`px-2 py-1 rounded-lg text-xs border ${!showOriginal ? 'bg-primary text-white border-primary' : 'border-card-border'}`}>English translation</button>
                    <button onClick={() => setShowOriginal(true)} className={`px-2 py-1 rounded-lg text-xs border ${showOriginal ? 'bg-primary text-white border-primary' : 'border-card-border'}`}>Original ({data.language})</button>
                  </div>
                )}
                <div className="text-muted">{needsTranslation && showOriginal ? `Original (${data.language})` : 'Narrative'}</div>
                <div className="text-heading whitespace-pre-wrap">{needsTranslation && showOriginal ? data.narrative_original : data.narrative}</div>
              </div>
              <div><div className="text-muted">Last Action</div><div className="text-heading">{data.last_action_text}</div></div>
              <div><div className="text-muted">Next Action</div><div className="text-heading">{data.next_action_text || '-'}</div></div>
            </div>
          </div>

          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Outcome tagging</div>
            <div className="p-5 space-y-3">
              <div className="text-sm text-muted">Current outcome: <span className="text-heading font-medium">{data.outcome_tag || 'Not tagged'}</span></div>
              <div className="flex flex-wrap items-center gap-2">
                <select value={outcome} onChange={(e) => { setOutcome(e.target.value); setError('') }} className="border border-card-border rounded-lg px-3 py-2 text-sm bg-white">
                  <option value="">Select outcome…</option>
                  {OUTCOMES.map((tag) => <option key={tag} value={tag}>{tag.replace(/_/g, ' ')}</option>)}
                </select>
                <button onClick={submitOutcome} disabled={!outcome || setOutcomeMutation.isPending} className="px-4 py-2 rounded-lg bg-primary text-white text-sm disabled:opacity-50">Save outcome</button>
              </div>
              {error && <div className="text-sm text-red-700">{error}</div>}
            </div>
          </div>

          {conflicts.length > 0 && (
            <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
              <div className="bg-white rounded-card border border-alert-border max-w-lg w-full p-5 space-y-3">
                <div className="font-semibold text-alert-text">Conflicting Outcome Warning</div>
                <div className="text-sm text-muted">This outcome contradicts a linked case in another bureau. Both must be preserved and the conflict acknowledged with a remark.</div>
                <div className="space-y-2">
                  {conflicts.map((c) => (
                    <div key={c.case_id} className="text-sm border border-alert-border bg-alert-bg rounded-lg px-3 py-2">
                      <div className="font-medium text-heading">{c.case_id} · {c.bureau_code}</div>
                      <div className="text-muted">Existing outcome: {c.outcome_tag}</div>
                    </div>
                  ))}
                </div>
                <label className="text-sm block"><span className="text-muted block mb-1">Acknowledgement remark (mandatory)</span><textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} rows={3} className="w-full border border-card-border rounded-lg px-3 py-2" placeholder="Explain why the contradictory outcomes are both being retained…" /></label>
                <div className="flex justify-end gap-2">
                  <button onClick={() => { setConflicts([]); setError('') }} className="px-3 py-2 rounded-lg border border-card-border text-sm">Cancel</button>
                  <button onClick={submitOutcome} disabled={!remarks.trim() || setOutcomeMutation.isPending} className="px-4 py-2 rounded-lg bg-alert-badge text-white text-sm disabled:opacity-50">Acknowledge & save</button>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Linked cases</div>
            <div className="p-5 space-y-2">
              {data.links?.length ? data.links.map((l: any) => (
                <div key={l.id} className="text-sm">
                  <div className="text-heading">{l.other_case_number}</div>
                  <div className="text-xs text-muted">{l.other_bureau} · {l.link_type} · score {l.similarity_score}</div>
                </div>
              )) : <div className="text-sm text-muted">No linked cases.</div>}
            </div>
          </div>
          {data.status !== 'DISPOSED' && (
            <div className="bg-card-bg border border-card-border rounded-card">
              <div className="px-5 py-4 border-b border-card-border flex items-center justify-between gap-2">
                <div className="font-medium text-heading flex items-center gap-2"><Scale size={16} /> Precedents <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-page-bg border border-card-border text-muted">ADVISORY</span></div>
                <button onClick={() => precedents.refetch()} disabled={precedents.isFetching} className="text-xs text-muted hover:text-heading disabled:opacity-50">{precedents.isFetching ? 'Searching…' : 'Refresh'}</button>
              </div>
              <div className="p-5 space-y-3">
                <p className="text-xs text-muted">Similar resolved complaints provide context only. They do not set or recommend an automatic outcome.</p>
                <div className="flex flex-wrap gap-4 text-xs text-muted">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={sameCategory} onChange={(event) => setSameCategory(event.target.checked)} /> Same category</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={sameInstitution} onChange={(event) => setSameInstitution(event.target.checked)} disabled={!data.institution} /> Same institution</label>
                </div>
                {precedents.data?.outcome_conflict && (
                  <div className="rounded-lg border border-alert-border bg-alert-bg p-3 text-xs text-alert-text flex items-start gap-2">
                    <AlertTriangle size={15} className="mt-0.5 shrink-0" />
                    <span>{precedents.data.outcome_conflict_note}</span>
                  </div>
                )}
                {precedents.data?.candidates?.map((candidate: any) => (
                  <div key={candidate.case_id} className="rounded-lg border border-card-border p-3 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <Link to={`/cases/${candidate.case_id}`} className="text-sm font-medium text-heading hover:underline">{candidate.case_number}</Link>
                        <div className="text-xs text-muted mt-0.5">
                          {candidate.category?.replace(/_/g, ' ')}
                          {candidate.category_subtype ? ` · ${candidate.category_subtype.replace(/_/g, ' ')}` : ''}
                          {candidate.institution?.name ? ` · ${candidate.institution.name}` : ''}
                          {candidate.cross_language ? ' · cross-language' : ''}
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-xs text-muted">Similarity</div>
                        <div className="text-sm font-semibold text-heading">{Math.round(candidate.score * 100)}%</div>
                      </div>
                    </div>
                    <div className="text-sm text-heading">{candidate.subject || 'Untitled grievance'}</div>
                    <div className="text-xs text-muted">Recorded outcome: <span className="text-heading">{candidate.outcome_tag?.replace(/_/g, ' ') || 'Not recorded'}</span> · {candidate.status?.replace(/_/g, ' ')} · {candidate.date_received?.slice(0, 10)}</div>
                    {(candidate.why_similar?.length || 0) > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {candidate.why_similar.map((term: string) => <span key={term} className="px-1.5 py-0.5 rounded bg-page-bg border border-card-border text-[10px] text-muted">{term}</span>)}
                      </div>
                    )}
                    <p className="text-xs text-muted line-clamp-3">{candidate.narrative_excerpt}</p>
                    <div className="flex items-center gap-2 text-[11px] text-muted">
                      <span>Was this precedent useful?</span>
                      <button onClick={() => precedentFeedback.mutate({ precedentId: candidate.case_id, feedback: 'HELPFUL' })} disabled={precedentFeedback.isPending} className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${candidate.feedback?.my_feedback === 'HELPFUL' ? 'bg-success text-white border-success' : 'border-card-border hover:bg-page-bg'}`}><ThumbsUp size={12} /> Helpful</button>
                      <button onClick={() => precedentFeedback.mutate({ precedentId: candidate.case_id, feedback: 'NOT_HELPFUL' })} disabled={precedentFeedback.isPending} className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${candidate.feedback?.my_feedback === 'NOT_HELPFUL' ? 'bg-alert-badge text-white border-alert-badge' : 'border-card-border hover:bg-page-bg'}`}><ThumbsDown size={12} /> Not useful</button>
                      <button onClick={() => precedentFeedback.mutate({ precedentId: candidate.case_id, feedback: 'WRONG_MATCH' })} disabled={precedentFeedback.isPending} className={`inline-flex items-center gap-1 px-2 py-1 rounded border ${candidate.feedback?.my_feedback === 'WRONG_MATCH' ? 'bg-alert-badge text-white border-alert-badge' : 'border-card-border hover:bg-page-bg'}`}>Wrong match</button>
                    </div>
                  </div>
                ))}
                {!precedents.isFetching && !precedents.data?.candidates?.length && <div className="text-sm text-muted">No resolved precedents matched these filters.</div>}
                {precedents.data?.semantic_note && <div className="text-[11px] text-muted">{precedents.data.semantic_note}</div>}
                {precedentFeedback.isError && <div className="text-xs text-red-700">Could not save precedent feedback.</div>}
              </div>
            </div>
          )}
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Attachments</div>
            <div className="p-5 space-y-2">
              {data.actions?.filter((a: any) => a.document_url).length ? data.actions.filter((a: any) => a.document_url).map((a: any) => (
                <a key={`doc-${a.id}`} href={a.document_url} className="block text-sm text-heading hover:underline break-all">{a.document_url.split('/').pop()}</a>
              )) : <div className="text-sm text-muted">No attachments on record.</div>}
            </div>
          </div>
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading flex items-center gap-2"><History size={16} /> Timeline</div>
            <div className="p-5 space-y-3">
              {data.actions?.map((a: any) => (
                <div key={a.id}>
                  <div className="text-sm text-heading">{a.action_type}</div>
                  <div className="text-xs text-muted">{a.created_at?.replace('T',' ').slice(0,16)} · {a.actor} · {a.bureau_code}</div>
                  <div className="text-sm text-muted mt-1">{a.remarks}</div>
                  {a.document_url && <a href={a.document_url} className="text-xs text-heading hover:underline">{a.document_url.split('/').pop()}</a>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <ProvenanceDrawer caseId={traceOpen ? Number(id) : null} onClose={() => setTraceOpen(false)} />
    </div>
  )
}
