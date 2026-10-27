import { useEffect, useState, type ReactNode } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, Database, RefreshCw, Zap } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'

type FeedEvent = { type?: string; message?: string; source_name?: string; source_type?: string; at?: string }

export default function DataSources() {
  const qc = useQueryClient()
  const [feed, setFeed] = useState<FeedEvent[]>([])
  const [rawId, setRawId] = useState<number | null>(null)
  const { data: sources } = useQuery({ queryKey: ['sources'], queryFn: async () => (await api.get('/sources')).data, refetchInterval: 15000 })
  const { data: quality } = useQuery({ queryKey: ['source-quality'], queryFn: async () => (await api.get('/sources/quality')).data })
  const { data: stats } = useQuery({ queryKey: ['public-stats'], queryFn: async () => (await api.get('/sources/public-stats')).data })
  const { data: raw } = useQuery({ queryKey: ['raw-payloads'], queryFn: async () => (await api.get('/sources/raw?limit=12')).data })
  const { data: rawDetail } = useQuery({ queryKey: ['raw-payload', rawId], queryFn: async () => (await api.get(`/sources/raw/${rawId}`)).data, enabled: !!rawId })
  const { data: recentEvents } = useQuery({ queryKey: ['recent-events'], queryFn: async () => (await api.get('/sources/events/recent')).data })

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    const es = new EventSource(`/api/events/stream?token=${encodeURIComponent(token)}`)
    es.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        setFeed((prev) => [parsed, ...prev].slice(0, 12))
        qc.invalidateQueries({ queryKey: ['sources'] })
        qc.invalidateQueries({ queryKey: ['raw-payloads'] })
      } catch {
        return
      }
    }
    return () => es.close()
  }, [qc])

  const sync = useMutation({
    mutationFn: async (name: string) => (await api.post(`/sources/${name}/sync`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['source-quality'] })
    },
  })
  const toggle = useMutation({
    mutationFn: async ({ name, enabled }: { name: string; enabled: boolean }) => (await api.patch(`/sources/${name}/enabled`, { enabled })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
  const scenario = useMutation({
    mutationFn: async () => (await api.post('/sources/scenario-trigger')).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sources'] })
      qc.invalidateQueries({ queryKey: ['source-quality'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-heading">Data Sources</h1>
          <p className="text-sm text-muted">Connector status, ingestion quality and payload lineage</p>
        </div>
        <button onClick={() => scenario.mutate()} disabled={scenario.isPending} className="inline-flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-60">
          <Zap size={16} /> Trigger demo scenario
        </button>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-card px-4 py-3 text-sm text-amber-900">
        <strong>SIMULATOR – synthetic data.</strong> CSS and CPGRAMS feeds below are generated mock services for demonstration. They are never presented as live public data. Public statistics use bundled snapshots when no live API key is configured.
      </div>

      {scenario.data && (
        <div className="bg-card-bg border border-card-border rounded-card p-4 text-sm">
          <div className="font-medium text-heading">{scenario.data.banner}</div>
          <div className="text-muted mt-1">Injected into both simulators and synced through the real ingestion pipeline. {JSON.stringify(scenario.data.sync)}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {sources?.map((s: any) => (
          <div key={s.id} className="bg-card-bg border border-card-border rounded-card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Database size={16} className="text-muted" />
                  <span className="font-medium text-heading capitalize">{s.name.replace(/_/g, ' ')}</span>
                  <SourceBadge type={s.source_type} />
                  {s.is_synthetic && <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200">SYNTHETIC DATA</span>}
                </div>
                <div className="text-xs text-muted mt-1">{s.kind} · mode {s.mode} · every {s.interval_seconds}s</div>
                <div className="text-xs text-muted mt-1 break-all">{s.base_url_masked}</div>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${s.last_status === 'SUCCESS' ? 'bg-success-bg text-success-text border-emerald-200' : s.last_status === 'FAILED' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-page-bg text-muted border-card-border'}`}>
                {s.last_status || 'PENDING'}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
              <div><div className="text-muted text-xs">Records</div><div className="font-medium">{s.records_total}</div></div>
              <div><div className="text-muted text-xs">Today</div><div className="font-medium">{s.records_today}</div></div>
              <div><div className="text-muted text-xs">Errors</div><div className="font-medium">{s.error_count}</div></div>
            </div>
            <div className="text-xs text-muted mt-3">Last success: {s.last_success_at ? s.last_success_at.replace('T', ' ').slice(0, 19) : '—'}</div>
            {s.last_error && <div className="text-xs text-red-700 mt-1">{s.last_error}</div>}
            <div className="flex items-center gap-2 mt-4">
              <button onClick={() => sync.mutate(s.name)} disabled={sync.isPending} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-card-border hover:bg-page-bg disabled:opacity-50">
                <RefreshCw size={14} /> Sync now
              </button>
              <label className="inline-flex items-center gap-2 text-xs text-muted">
                <input type="checkbox" checked={s.enabled} onChange={(e) => toggle.mutate({ name: s.name, enabled: e.target.checked })} />
                Enabled
              </label>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Ingestion quality" subtitle="Computed from stored records, not vendor claims">
          <table className="w-full text-sm">
            <thead className="bg-page-bg"><tr><th className="text-left px-4 py-2 text-muted font-medium">Source</th><th className="text-left px-4 py-2 text-muted font-medium">Total</th><th className="text-left px-4 py-2 text-muted font-medium">Institution linked</th><th className="text-left px-4 py-2 text-muted font-medium">Needs review</th><th className="text-left px-4 py-2 text-muted font-medium">Visible in</th></tr></thead>
            <tbody>
              {quality?.map((q: any) => (
                <tr key={q.source} className="border-t border-card-border">
                  <td className="px-4 py-2 uppercase">{q.source}</td>
                  <td className="px-4 py-2">{q.total}</td>
                  <td className="px-4 py-2">{q.clean_institution_pct}%</td>
                  <td className="px-4 py-2">{q.needs_review_pct}%</td>
                  <td className="px-4 py-2">{q.avg_ingest_to_visible_seconds}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Live event feed" subtitle="Server-sent events from ingestion and audit actions">
          <div className="p-4 space-y-2 max-h-72 overflow-y-auto">
            {(feed.length ? feed : recentEvents || []).length === 0 && <div className="text-sm text-muted">Waiting for events…</div>}
            {(feed.length ? feed : recentEvents || []).map((event: FeedEvent, i: number) => (
              <div key={`${event.at}-${i}`} className="flex items-start gap-2 text-sm">
                <Activity size={14} className="text-success mt-0.5 shrink-0" />
                <div>
                  <div className="text-heading">{event.message || event.type || 'Event'}</div>
                  <div className="text-xs text-muted">{event.source_name || 'system'} · {event.at ? event.at.replace('T', ' ').slice(0, 19) : 'now'}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="Public statistics" subtitle="Bundled snapshots are explicitly labeled; no live claim is made">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg"><tr><th className="text-left px-4 py-2 text-muted font-medium">Source</th><th className="text-left px-4 py-2 text-muted font-medium">Dataset</th><th className="text-left px-4 py-2 text-muted font-medium">Period</th><th className="text-left px-4 py-2 text-muted font-medium">Mode</th><th className="text-left px-4 py-2 text-muted font-medium">Fetched</th></tr></thead>
            <tbody>
              {stats?.map((s: any) => (
                <tr key={s.id} className="border-t border-card-border">
                  <td className="px-4 py-2 uppercase">{s.source}</td>
                  <td className="px-4 py-2">{s.dataset_key}</td>
                  <td className="px-4 py-2">{s.period || '—'}</td>
                  <td className="px-4 py-2">{s.is_snapshot ? <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">SNAPSHOT</span> : <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">LIVE</span>}</td>
                  <td className="px-4 py-2 text-muted">{s.fetched_at?.replace('T', ' ').slice(0, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel title="Recent raw payloads" subtitle="Immutable input retained before normalization">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg"><tr><th className="text-left px-4 py-2 text-muted font-medium">Source</th><th className="text-left px-4 py-2 text-muted font-medium">Record</th><th className="text-left px-4 py-2 text-muted font-medium">Type</th><th className="text-left px-4 py-2 text-muted font-medium">SHA-256</th><th className="text-left px-4 py-2 text-muted font-medium">Fetched</th></tr></thead>
            <tbody>
              {raw?.map((r: any) => (
                <tr key={r.id} onClick={() => setRawId(r.id)} className="border-t border-card-border cursor-pointer hover:bg-page-bg/60">
                  <td className="px-4 py-2 uppercase">{r.source}</td>
                  <td className="px-4 py-2">{r.source_record_id}</td>
                  <td className="px-4 py-2"><SourceBadge type={r.source_type} compact /></td>
                  <td className="px-4 py-2 text-xs text-muted">{r.payload_sha256?.slice(0, 14)}…</td>
                  <td className="px-4 py-2 text-muted">{r.fetched_at?.replace('T', ' ').slice(0, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rawDetail && (
          <div className="border-t border-card-border p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-heading">Raw payload #{rawDetail.id} · {rawDetail.source_record_id}</div>
              <button onClick={() => setRawId(null)} className="text-xs text-muted hover:text-heading">Close</button>
            </div>
            <pre className="text-[11px] bg-page-bg p-3 rounded-lg overflow-x-auto max-h-72">{JSON.stringify(rawDetail.payload, null, 2)}</pre>
          </div>
        )}
      </Panel>
    </div>
  )
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="bg-card-bg border border-card-border rounded-card">
      <div className="px-5 py-4 border-b border-card-border">
        <div className="font-medium text-heading">{title}</div>
        {subtitle && <div className="text-xs text-muted">{subtitle}</div>}
      </div>
      {children}
    </div>
  )
}
