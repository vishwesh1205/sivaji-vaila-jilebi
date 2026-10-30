import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import RiskGauge from '../components/RiskGauge'

const REGIONS = ['Chennai', 'Bhopal', 'Kolkata', 'Chandigarh', 'Kanpur', 'Pune', 'Hyderabad', 'Guwahati', 'Jaipur', 'Bengaluru']
const PAGE_SIZE = 50

export default function Institutions() {
  const [query, setQuery] = useState('')
  const [region, setRegion] = useState('')
  const [page, setPage] = useState(1)
  const { data, isFetching } = useQuery({
    queryKey: ['institutions', query, region, page],
    queryFn: async () => (await api.get('/institutions', { params: { q: query || undefined, region: region || undefined, page, limit: PAGE_SIZE } })).data,
  })
  const totalPages = Math.max(1, Math.ceil((data?.total || 0) / PAGE_SIZE))
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-heading">Institutions</h1>
        <p className="text-sm text-muted">Search and filter institutions</p>
      </div>
      <div className="bg-card-bg border border-card-border rounded-card p-4 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-[240px] border border-card-border rounded-lg px-3 py-2 bg-white">
          <Search size={16} className="text-muted" />
          <input value={query} onChange={(e) => { setQuery(e.target.value); setPage(1) }} placeholder="Search by institution name or AICTE ID" className="flex-1 bg-transparent text-sm focus:outline-none" aria-label="Search institutions" />
        </div>
        <select value={region} onChange={(e) => { setRegion(e.target.value); setPage(1) }} className="border border-card-border rounded-lg px-3 py-2 text-sm bg-white" aria-label="Filter by region">
          <option value="">All regions</option>
          {REGIONS.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
        <div className="text-xs text-muted">{isFetching ? 'Searching…' : `${data?.total || 0} institution(s)`}</div>
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
            {!data?.items?.length && <tr><td colSpan={9} className="px-5 py-6 text-sm text-muted">No institutions match the current search.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-muted">
        <span>Page {page} of {totalPages}</span>
        <div className="flex items-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="px-3 py-1.5 rounded-lg border border-card-border disabled:opacity-40">Previous</button>
          <button disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} className="px-3 py-1.5 rounded-lg border border-card-border disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  )
}
