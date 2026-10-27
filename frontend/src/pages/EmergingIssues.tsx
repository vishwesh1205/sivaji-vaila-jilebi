import { useQuery } from '@tanstack/react-query'
import { TrendingUp } from 'lucide-react'
import api from '../lib/api'

export default function EmergingIssues() {
  const { data, isLoading } = useQuery({ queryKey: ['emerging'], queryFn: async () => (await api.get('/innovations/emerging-issues')).data, refetchInterval: 60000 })
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-heading">Emerging Issues</h1>
        <p className="text-sm text-muted">Weekly spike detection by complaint category and region</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-4 text-sm text-muted">
        Detection compares the current week with an 8-week baseline. A card appears only when the count is at least the configured minimum and z-score exceeds the threshold. This is a statistical alert, not a finding of wrongdoing. Demo records are labeled <span className="font-medium text-heading">SIMULATOR</span>.
      </div>
      {isLoading && <div className="text-sm text-muted">Computing spikes…</div>}
      {!isLoading && !data?.length && <div className="bg-card-bg border border-card-border rounded-card p-6 text-sm text-muted">No significant spike in the current window.</div>}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data?.map((row: any) => {
          const max = Math.max(...row.sparkline, 1)
          return (
            <div key={`${row.category}-${row.region}`} className="bg-card-bg border border-alert-border rounded-card p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <TrendingUp size={16} className="text-alert-badge" />
                    <span className="font-medium text-heading">{row.category.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="text-sm text-muted mt-1">{row.region} region · current week {row.current_week_count} complaints</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-semibold text-alert-text">{row.ratio.toFixed(1)}×</div>
                  <div className="text-xs text-muted">z = {row.z_score}</div>
                </div>
              </div>
              <div className="mt-4 flex items-end gap-1 h-16">
                {row.sparkline.map((value: number, i: number) => (
                  <div key={i} className={`flex-1 rounded-t ${i === row.sparkline.length - 1 ? 'bg-alert-badge' : 'bg-alert-border'}`} style={{ height: `${Math.max(4, (value / max) * 100)}%` }} title={`${value}`} />
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-muted mt-1"><span>8 weeks ago</span><span>This week</span></div>
              <div className="text-sm text-heading mt-3">{row.message}</div>
              <div className="text-xs text-muted mt-1">Baseline weekly mean: {row.baseline_weekly_mean}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
