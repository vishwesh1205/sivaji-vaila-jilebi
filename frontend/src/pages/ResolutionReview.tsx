import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'

export default function ResolutionReview() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['review'], queryFn: async () => (await api.get('/review-queue')).data })
  const evaluation = useQuery({ queryKey: ['resolution-evaluation'], queryFn: async () => (await api.get('/review-queue/evaluation')).data })
  const confirm = useMutation({
    mutationFn: async ({ id, institutionId }: { id: number; institutionId?: number }) => (await api.post(`/review-queue/${id}/confirm`, { institution_id: institutionId })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['review'] }); qc.invalidateQueries({ queryKey: ['cases'] }) },
  })
  const reject = useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks: string }) => (await api.post(`/review-queue/${id}/reject`, { remarks })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['review'] }); qc.invalidateQueries({ queryKey: ['cases'] }) },
  })
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Resolution Review</h1>
        <p className="text-sm text-muted">Ambiguous institution matches requiring human review</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-heading">Resolution benchmark</div>
            <div className="text-xs text-muted mt-1">Deterministic offline test over messy synthetic ticket references.</div>
          </div>
          <button onClick={() => evaluation.refetch()} disabled={evaluation.isFetching} className="px-3 py-1.5 rounded-lg text-xs border border-card-border disabled:opacity-50">{evaluation.isFetching ? 'Running…' : 'Re-run benchmark'}</button>
        </div>
        {evaluation.data && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
              {[
                ['Precision', `${Math.round(evaluation.data.precision * 100)}%`],
                ['Recall', `${Math.round(evaluation.data.recall * 100)}%`],
                ['F1', `${Math.round(evaluation.data.f1 * 100)}%`],
                ['Samples', evaluation.data.sample_size],
                ['Seed', evaluation.data.seed],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-page-bg border border-card-border p-3">
                  <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
                  <div className="text-lg font-semibold text-heading mt-1">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted">
              <span>TP {evaluation.data.true_positive} · FP {evaluation.data.false_positive} · FN {evaluation.data.false_negative}</span>
              <span>Auto-link coverage {Math.round(evaluation.data.coverage * 100)}%</span>
              <span>Run {new Date(evaluation.data.generated_at + 'Z').toLocaleString()}</span>
            </div>
          </>
        )}
        {!evaluation.data && <div className="text-sm text-muted mt-4">{evaluation.isError ? 'Benchmark unavailable.' : 'Running benchmark…'}</div>}
      </div>
      <div className="space-y-3">
        {data?.map((r: any) => (
          <div key={r.id} className="bg-card-bg border border-card-border rounded-card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-medium text-heading flex items-center gap-2">{r.case_number} <SourceBadge type={r.source_type} name={r.source_name} /></div>
                <div className="text-sm text-muted mt-1">Raw text: {r.raw_institution_text}</div>
                <div className="text-sm text-muted mt-1">Category: {r.category} · Bureau: {r.bureau_code}</div>
                <div className="text-sm text-muted mt-1 line-clamp-2">{r.narrative}</div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => confirm.mutate({ id: r.id })} disabled={confirm.isPending || !r.candidate_institutions?.length} className="px-3 py-1.5 rounded-lg text-sm bg-success text-white disabled:opacity-50">Confirm top match</button>
                <button onClick={() => { const remarks = window.prompt('Reason for rejecting this review'); if (remarks) reject.mutate({ id: r.id, remarks }) }} className="px-3 py-1.5 rounded-lg text-sm border border-card-border">Reject</button>
              </div>
            </div>
            <div className="mt-4">
              <div className="text-sm font-medium text-heading mb-2">Top Candidates</div>
              <div className="space-y-2">
                {r.candidate_institutions?.map((c: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between p-3 border border-card-border rounded-lg">
                    <div>
                      <div className="text-sm text-heading">{c.name}</div>
                      <div className="text-xs text-muted">{c.aicte_permanent_id}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-sm text-muted">{Math.round(c.score * 100)}%</div>
                      <div className="w-24 h-2 bg-page-bg rounded-full overflow-hidden"><div className="h-2 bg-success" style={{ width: `${c.score * 100}%` }}></div></div>
                      <button onClick={() => confirm.mutate({ id: r.id, institutionId: c.institution_id })} disabled={confirm.isPending} className="text-xs px-2 py-1 rounded border border-card-border hover:bg-page-bg">Use</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
        {!data?.length && <div className="bg-card-bg border border-card-border rounded-card p-6 text-sm text-muted">No pending reviews.</div>}
      </div>
    </div>
  )
}
