import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import RiskGauge from '../components/RiskGauge'

function KpiCard({ label, value, sub }: { label: string, value: number | string, sub?: string }) {
  return (
    <div className="bg-card-bg border border-card-border rounded-card p-5">
      <div className="text-sm text-muted">{label}</div>
      <div className="text-2xl font-semibold text-heading mt-1">{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: async () => (await api.get('/dashboard/summary')).data, refetchInterval: 30000 })
  const { data: bureau } = useQuery({ queryKey: ['bureau'], queryFn: async () => (await api.get('/dashboard/bureau-workload')).data })
  const { data: ageing } = useQuery({ queryKey: ['ageing'], queryFn: async () => (await api.get('/dashboard/ageing')).data })
  const { data: trends } = useQuery({ queryKey: ['trends'], queryFn: async () => (await api.get('/dashboard/trends')).data })
  const { data: instWise } = useQuery({ queryKey: ['instwise'], queryFn: async () => (await api.get('/dashboard/institution-wise')).data })
  const { data: overlaps } = useQuery({ queryKey: ['overlaps'], queryFn: async () => (await api.get('/overlaps')).data })
  const { data: proof } = useQuery({ queryKey: ['proof'], queryFn: async () => (await api.get('/dashboard/proof-summary')).data, refetchInterval: 30000 })
  const { data: topRisk } = useQuery({ queryKey: ['top-risk'], queryFn: async () => (await api.get('/dashboard/top-risk?limit=5')).data })
  const { data: emerging } = useQuery({ queryKey: ['emerging-dashboard'], queryFn: async () => (await api.get('/dashboard/emerging-issues')).data, refetchInterval: 60000 })

  const topOverlap = overlaps?.find((o: any) => o.status === 'OPEN' || o.status === 'ACKNOWLEDGED')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-heading">Dashboard</h1>
          <p className="text-sm text-muted">Institution-centric complaint monitoring overview</p>
        </div>
        <button onClick={() => navigate('/cases')} className="bg-primary text-white px-4 py-2 rounded-lg text-sm">New Case Entry</button>
      </div>

      {topOverlap && (
        <div className="bg-alert-bg border border-alert-border rounded-card p-4 flex items-center justify-between">
          <div>
            <div className="font-medium text-alert-text">Potential Overlapping Cases – Coordination Required</div>
            <div className="text-sm text-alert-text/80 mt-1">{topOverlap.institution?.name} ({topOverlap.institution?.aicte_permanent_id}) · Bureaus: {topOverlap.bureaus_involved?.join(', ')}</div>
          </div>
          <button onClick={() => navigate('/overlaps')} className="text-sm font-medium text-alert-text underline">Review & Coordinate →</button>
        </div>
      )}

      {proof && (
        <div className="bg-card-bg border border-card-border rounded-card p-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
            <div className="font-medium text-heading">Last 24h source proof</div>
            <div className="text-muted">CSS <span className="text-heading font-medium">{proof.css}</span> <SourceBadge type="SIMULATOR" compact /></div>
            <div className="text-muted">CPGRAMS <span className="text-heading font-medium">{proof.cpgrams}</span> <SourceBadge type="SIMULATOR" compact /></div>
            <div className="text-muted">Seed <span className="text-heading font-medium">{proof.seed_simulator}</span> <SourceBadge type="SIMULATOR" compact /></div>
            <div className="text-muted">Manual <span className="text-heading font-medium">{proof.manual}</span></div>
            <div className="text-muted">Public stats <span className="text-heading font-medium">{proof.public_stats_mode}</span></div>
            <div className="text-xs text-muted w-full">{proof.note}</div>
          </div>
        </div>
      )}

      {emerging?.[0] && (
        <div className="bg-card-bg border border-alert-border rounded-card p-4 flex items-center justify-between">
          <div>
            <div className="font-medium text-alert-text">Emerging issue: {emerging[0].category.replace(/_/g, ' ')} in {emerging[0].region}</div>
            <div className="text-sm text-alert-text/80 mt-1">{emerging[0].message} · z = {emerging[0].z_score}</div>
          </div>
          <button onClick={() => navigate('/emerging')} className="text-sm font-medium text-alert-text underline">View emerging issues →</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total cases" value={summary?.total || 0} />
        <KpiCard label="Pending beyond 90 days" value={summary?.beyond_timeline || 0} />
        <KpiCard label="Overlap alerts active" value={summary?.overlap_alerts_active || 0} />
        <KpiCard label="Disposal rate" value={`${summary?.disposal_rate || 0}%`} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KpiCard label="Pending" value={summary?.pending || 0} />
        <KpiCard label="Under Process" value={summary?.under_process || 0} />
        <KpiCard label="Disposed" value={summary?.disposed || 0} />
        <KpiCard label="Transferred" value={summary?.transferred || 0} />
        <KpiCard label="Escalated" value={summary?.escalated || 0} />
      </div>

      <div className="bg-card-bg border border-card-border rounded-card">
        <div className="px-5 py-4 border-b border-card-border flex items-center justify-between">
          <div className="font-medium text-heading">Top risk institutions</div>
          <div className="text-xs text-muted">Transparent weighted score · weights shown on institution page</div>
        </div>
        <div className="divide-y divide-card-border">
          {topRisk?.map((row: any) => (
            <div key={row.institution_id} className="px-5 py-3 flex items-center gap-4">
              <RiskGauge score={row.score} size={56} />
              <div className="flex-1">
                <button onClick={() => navigate(`/institutions/${row.institution_id}`)} className="text-sm font-medium text-heading hover:underline">{row.institution_name}</button>
                <div className="text-xs text-muted">{row.aicte_permanent_id} · score {row.score}/100</div>
              </div>
              <div className="hidden md:flex flex-wrap gap-1 max-w-xl justify-end">
                {row.breakdown?.filter((b: any) => b.points > 0).slice(0, 3).map((b: any) => (
                  <span key={b.component} className="text-[11px] px-2 py-0.5 rounded-full bg-page-bg border border-card-border text-muted">{b.component}: {b.points}</span>
                ))}
              </div>
            </div>
          ))}
          {!topRisk?.length && <div className="px-5 py-4 text-sm text-muted">No risk data yet.</div>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card-bg border border-card-border rounded-card">
          <div className="px-5 py-4 border-b border-card-border">
            <div className="font-medium text-heading">Institutions – Active Cases</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-page-bg">
                <tr>
                  <th className="text-left px-5 py-2 text-muted font-medium">Institution</th>
                  <th className="text-left px-5 py-2 text-muted font-medium">AICTE ID</th>
                  <th className="text-left px-5 py-2 text-muted font-medium">Bureaus</th>
                  <th className="text-left px-5 py-2 text-muted font-medium">Status</th>
                  <th className="text-left px-5 py-2 text-muted font-medium">Active</th>
                </tr>
              </thead>
              <tbody>
                {instWise?.slice(0, 10).map((row: any, idx: number) => (
                  <tr key={idx} className="border-t border-card-border">
                    <td className="px-5 py-3 text-heading">{row.institution}</td>
                    <td className="px-5 py-3 text-muted">{row.aicte_permanent_id}</td>
                    <td className="px-5 py-3">{row.bureaus?.map((b: string) => <span key={b} className={`inline-block px-2 py-0.5 rounded-full text-xs mr-1 ${b === 'RB' ? 'bg-rb-bg text-rb-text' : b === 'PGRC' ? 'bg-pgrc-bg text-pgrc-text' : 'bg-page-bg text-muted'}`}>{b}</span>)}</td>
                    <td className="px-5 py-3 text-muted">{row.status}</td>
                    <td className="px-5 py-3 text-muted">{row.active}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="bg-card-bg border border-card-border rounded-card">
          <div className="px-5 py-4 border-b border-card-border">
            <div className="font-medium text-heading">Bureau-wise Workload</div>
          </div>
          <div className="p-5 space-y-3">
            {bureau?.map((b: any) => (
              <div key={b.bureau_code}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-heading">{b.bureau_code}</span>
                  <span className="text-muted">{b.total}</span>
                </div>
                <div className="w-full h-2 bg-page-bg rounded-full overflow-hidden">
                  <div className="h-2 bg-sidebar-active" style={{ width: `${Math.min(100, (b.total / Math.max(1, summary?.total || 1)) * 100)}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card-bg border border-card-border rounded-card">
          <div className="px-5 py-4 border-b border-card-border">
            <div className="font-medium text-heading">Monthly Trend</div>
          </div>
          <div className="p-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends || []}>
                <XAxis dataKey="month" stroke="#667585" fontSize={12} />
                <YAxis stroke="#667585" fontSize={12} />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#1E8E73" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="bg-card-bg border border-card-border rounded-card">
          <div className="px-5 py-4 border-b border-card-border">
            <div className="font-medium text-heading">Ageing Buckets (Open Cases)</div>
          </div>
          <div className="p-5 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={Object.entries(ageing || {}).map(([k,v]) => ({ bucket: k, count: v }))}>
                <XAxis dataKey="bucket" stroke="#667585" fontSize={12} />
                <YAxis stroke="#667585" fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#102A43" radius={[6,6,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
