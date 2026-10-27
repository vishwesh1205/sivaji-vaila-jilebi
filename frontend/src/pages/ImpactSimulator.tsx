import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../lib/api'

export default function ImpactSimulator() {
  const [delay, setDelay] = useState(14)
  const [hours, setHours] = useState(6)
  const [seed, setSeed] = useState(42)
  const { data, isLoading } = useQuery({
    queryKey: ['impact', delay, hours, seed],
    queryFn: async () => (await api.get('/innovations/impact-simulator', { params: { discovery_delay_days: delay, duplicate_hours_saved: hours, seed } })).data,
  })
  const chart = data ? [
    { metric: 'Avg days to detect', baseline: data.baseline.avg_days_to_detect, system: data.system.avg_days_to_detect },
    { metric: 'Duplicate days avoided', baseline: data.baseline.estimated_duplicate_fact_finding_days_avoided, system: data.system.estimated_duplicate_fact_finding_days_avoided },
    { metric: 'Early warnings', baseline: data.baseline.cases_with_early_warning, system: data.system.cases_with_early_warning },
    { metric: 'Breached 90 days', baseline: data.baseline.breached_90_days, system: data.system.breached_90_days },
  ] : []
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-heading">Impact Simulator</h1>
        <p className="text-sm text-muted">Deterministic replay of existing cases with editable assumptions</p>
      </div>
      <div className="bg-amber-50 border border-amber-200 rounded-card px-4 py-3 text-sm text-amber-900">
        <strong>Model output, not a measured claim.</strong> Baseline discovery delay and duplicate effort are assumptions you can change. Results replay stored cases, including simulator records.
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-5 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <label className="text-sm"><span className="text-muted block mb-1">Manual discovery delay (days)</span><input type="number" min={1} max={90} value={delay} onChange={(e) => setDelay(Number(e.target.value))} className="w-full border border-card-border rounded-lg px-3 py-2" /></label>
        <label className="text-sm"><span className="text-muted block mb-1">Duplicate hours saved</span><input type="number" min={0} max={40} step={0.5} value={hours} onChange={(e) => setHours(Number(e.target.value))} className="w-full border border-card-border rounded-lg px-3 py-2" /></label>
        <label className="text-sm"><span className="text-muted block mb-1">Replay seed</span><input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} className="w-full border border-card-border rounded-lg px-3 py-2" /></label>
        <div className="text-xs text-muted">Replay cases: {data?.replay_case_count ?? '—'} · deterministic: {data?.deterministic ? 'yes' : '—'}</div>
      </div>
      {isLoading && <div className="text-sm text-muted">Replaying cases…</div>}
      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Metric label="Overlap opportunities" value={data.system.overlaps_detected} />
            <Metric label="Manual avg days to detect" value={data.baseline.avg_days_to_detect} />
            <Metric label="Coordinated avg days to detect" value={data.system.avg_days_to_detect} />
          </div>
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Baseline vs system</div>
            <div className="p-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E7ECF1" />
                  <XAxis dataKey="metric" stroke="#667585" fontSize={11} />
                  <YAxis stroke="#667585" fontSize={11} />
                  <Tooltip />
                  <Bar dataKey="baseline" name="Assumed baseline" fill="#B54708" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="system" name="Coordinated layer" fill="#1E8E73" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="bg-card-bg border border-card-border rounded-card">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Replay assumptions</div>
            <div className="p-5 text-sm text-muted space-y-1">
              <div>{data.assumptions.note}</div>
              <div>System detection: {data.assumptions.system_detection_days} days · Seed: {data.assumptions.seed} · Manual delay: {data.assumptions.discovery_delay_days} days</div>
            </div>
          </div>
          <div className="bg-card-bg border border-card-border rounded-card overflow-x-auto">
            <div className="px-5 py-4 border-b border-card-border font-medium text-heading">Detected overlap opportunities (first 100)</div>
            <table className="w-full text-sm">
              <thead className="bg-page-bg"><tr><th className="text-left px-4 py-2 text-muted font-medium">Institution</th><th className="text-left px-4 py-2 text-muted font-medium">Bureaus</th><th className="text-left px-4 py-2 text-muted font-medium">Opportunity at</th><th className="text-left px-4 py-2 text-muted font-medium">Baseline days</th><th className="text-left px-4 py-2 text-muted font-medium">System days</th></tr></thead>
              <tbody>
                {data.opportunities.map((o: any, i: number) => (
                  <tr key={`${o.institution_id}-${i}`} className="border-t border-card-border">
                    <td className="px-4 py-2 text-heading">{o.institution_name}</td>
                    <td className="px-4 py-2">{o.bureaus.join(', ')}</td>
                    <td className="px-4 py-2 text-muted">{o.opportunity_at?.slice(0, 10)}</td>
                    <td className="px-4 py-2">{o.baseline_days_to_detect}</td>
                    <td className="px-4 py-2">{o.system_days_to_detect}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="bg-card-bg border border-card-border rounded-card p-5"><div className="text-sm text-muted">{label}</div><div className="text-2xl font-semibold text-heading mt-1">{value}</div></div>
}
