import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import api from '../lib/api'

export default function ProvenanceDrawer({ caseId, onClose }: { caseId: number | null; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['provenance', caseId],
    queryFn: async () => (await api.get(`/provenance/case/${caseId}`)).data,
    enabled: !!caseId,
  })
  if (!caseId) return null
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div className="w-full max-w-xl h-full bg-white overflow-y-auto shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 bg-white border-b border-card-border px-5 py-4 flex items-center justify-between">
          <div>
            <div className="font-semibold text-heading">Evidence trail</div>
            <div className="text-xs text-muted">Raw payload → normalization → resolution → overlap</div>
          </div>
          <button onClick={onClose} aria-label="Close evidence trail" className="p-1.5 rounded-lg hover:bg-page-bg"><X size={18} /></button>
        </div>
        {isLoading && <div className="p-5 text-sm text-muted">Loading trace…</div>}
        {error && <div className="p-5 text-sm text-red-700">Could not load trace.</div>}
        {data && (
          <div className="p-5 space-y-4 text-sm">
            <TraceStage title="1. Raw payload" subtitle={data.stage_1_raw_payload?.available ? 'As received, immutable' : 'No raw payload retained'}>
              <div className="text-xs text-muted break-all">SHA-256: {data.stage_1_raw_payload?.payload_sha256 || '—'}</div>
              {data.stage_1_raw_payload?.payload && <pre className="mt-2 text-[11px] bg-page-bg p-3 rounded-lg overflow-x-auto">{JSON.stringify(data.stage_1_raw_payload.payload, null, 2)}</pre>}
            </TraceStage>
            <TraceStage title="2. Normalized record" subtitle="Canonical fields after mapping">
              <pre className="text-[11px] bg-page-bg p-3 rounded-lg overflow-x-auto">{JSON.stringify(data.stage_2_normalized, null, 2)}</pre>
            </TraceStage>
            <TraceStage title="3. Institution resolution" subtitle={`Auto-link ${data.stage_3_resolution?.thresholds?.auto_link ?? '—'} · review ${data.stage_3_resolution?.thresholds?.review ?? '—'}`}>
              <pre className="text-[11px] bg-page-bg p-3 rounded-lg overflow-x-auto">{JSON.stringify(data.stage_3_resolution, null, 2)}</pre>
            </TraceStage>
            <TraceStage title="4. Overlap decision" subtitle="Rule fired and bureaus involved">
              <pre className="text-[11px] bg-page-bg p-3 rounded-lg overflow-x-auto">{JSON.stringify(data.stage_4_overlap, null, 2)}</pre>
            </TraceStage>
            <div className="text-xs text-muted">Audit chain: {data.audit_chain_valid ? 'VALID' : 'CHECK REQUIRED'}</div>
          </div>
        )}
      </div>
    </div>
  )
}

function TraceStage({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="border border-card-border rounded-card p-4">
      <div className="font-medium text-heading">{title}</div>
      {subtitle && <div className="text-xs text-muted mb-2">{subtitle}</div>}
      {children}
    </div>
  )
}
