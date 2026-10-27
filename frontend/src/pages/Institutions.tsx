import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import RiskGauge from '../components/RiskGauge'

export default function Institutions() {
  const { data } = useQuery({ queryKey: ['institutions'], queryFn: async () => (await api.get('/institutions')).data })
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Institutions</h1>
        <p className="text-sm text-muted">Search and filter institutions</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-page-bg">
            <tr>
              <th className="text-left px-5 py-2 text-muted font-medium">Institution</th>
              <th className="text-left px-5 py-2 text-muted font-medium">AICTE ID</th>
              <th className="text-left px-5 py-2 text-muted font-medium">City/State</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Region</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Cases</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Active</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Risk</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Source</th>
              <th className="text-left px-5 py-2 text-muted font-medium">Overlap</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.map((inst: any) => (
              <tr key={inst.id} className="border-t border-card-border hover:bg-page-bg/50">
                <td className="px-5 py-3"><Link to={`/institutions/${inst.id}`} className="text-heading hover:underline">{inst.name}</Link></td>
                <td className="px-5 py-3 text-muted">{inst.aicte_permanent_id}</td>
                <td className="px-5 py-3 text-muted">{inst.city}, {inst.state}</td>
                <td className="px-5 py-3 text-muted">{inst.region}</td>
                <td className="px-5 py-3 text-muted">{inst.case_count}</td>
                <td className="px-5 py-3 text-muted">{inst.active_count}</td>
                <td className="px-5 py-3"><div className="flex items-center gap-2"><RiskGauge score={inst.risk_score} size={38} /><span className="text-xs text-muted">{inst.risk_score}</span></div></td>
                <td className="px-5 py-3"><SourceBadge type={inst.source_type} compact /></td>
                <td className="px-5 py-3">{inst.has_overlap && <span className="text-xs px-2 py-0.5 rounded-full bg-alert-bg text-alert-text border border-alert-border">Overlap</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
