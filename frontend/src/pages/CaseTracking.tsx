import { Fragment, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronUp, Search } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import QueryChips from '../components/QueryChips'

const label = (value?: string | null) => (value || '—').replace(/_/g, ' ').toLowerCase()

export default function CaseTracking() {
  const [input, setInput] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const { data } = useQuery({ queryKey: ['cases'], queryFn: async () => (await api.get('/cases')).data })
  const { data: nl, isFetching } = useQuery({
    queryKey: ['case-query', submitted],
    queryFn: async () => (await api.post('/innovations/query/execute', { query: submitted })).data,
    enabled: !!submitted,
  })

  const submit = (text: string) => {
    setInput(text)
    setSubmitted(text.trim())
  }

  const showNl = !!submitted && !!nl
  const showInstitutions = showNl && nl.target === 'institutions'
  const rows = showNl ? nl.results : data?.items || []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-heading">Case Tracking</h1>
          <p className="text-sm text-muted">Track, filter and query all cases</p>
        </div>
        <button className="bg-primary text-white px-4 py-2 rounded-lg text-sm">CSV Export</button>
      </div>

      <div className="bg-card-bg border border-card-border rounded-card p-4 space-y-3">
        <form onSubmit={(e) => { e.preventDefault(); submit(input) }} className="flex items-center gap-2">
          <Search size={18} className="text-muted" />
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask naturally: cases with RB and PGRC overlap in southern region older than 60 days" className="flex-1 bg-transparent text-sm focus:outline-none" />
          <button type="submit" className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm">Run</button>
          {submitted && <button type="button" onClick={() => { setInput(''); setSubmitted('') }} className="text-xs text-muted hover:text-heading">Clear</button>}
        </form>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-muted">Try:</span>
          {['fee cases older than 60 days', 'institutions with RB and PGRC overlap', 'disposed approval violation cases'].map((sample) => (
            <button key={sample} onClick={() => submit(sample)} className="text-xs px-2 py-1 rounded-full bg-page-bg border border-card-border text-muted hover:text-heading">{sample}</button>
          ))}
        </div>
        {showNl && (
          <div className="border-t border-card-border pt-3 space-y-2">
            <div className="text-sm text-heading">{nl.interpreted_as}</div>
            <QueryChips chips={nl.chips} />
            <div className="text-xs text-muted">Target: {nl.target} · {nl.result_count} result(s)</div>
          </div>
        )}
        {isFetching && <div className="text-xs text-muted">Interpreting query…</div>}
      </div>

      {showInstitutions ? (
        <div className="bg-card-bg border border-card-border rounded-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg">
              <tr>
                <th className="text-left px-5 py-2 text-muted">Institution</th>
                <th className="text-left px-5 py-2 text-muted">AICTE ID</th>
                <th className="text-left px-5 py-2 text-muted">Region</th>
                <th className="text-left px-5 py-2 text-muted">Source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((inst: any) => (
                <tr key={inst.id} className="border-t border-card-border">
                  <td className="px-5 py-3"><Link to={`/institutions/${inst.id}`} className="text-heading hover:underline">{inst.name}</Link></td>
                  <td className="px-5 py-3 text-muted">{inst.aicte_permanent_id}</td>
                  <td className="px-5 py-3 text-muted">{inst.region}</td>
                  <td className="px-5 py-3"><SourceBadge type={inst.source_type} compact /></td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={4} className="px-5 py-6 text-sm text-muted">No matching institutions.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-card-bg border border-card-border rounded-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-page-bg">
              <tr>
                <th className="text-left px-4 py-2 text-muted">Case ID</th>
                <th className="text-left px-4 py-2 text-muted">Subject</th>
                <th className="text-left px-4 py-2 text-muted">Institution</th>
                <th className="text-left px-4 py-2 text-muted">Complainant</th>
                <th className="text-left px-4 py-2 text-muted">Bureau</th>
                <th className="text-left px-4 py-2 text-muted">Category</th>
                <th className="text-left px-4 py-2 text-muted">Status</th>
                <th className="text-left px-4 py-2 text-muted">Last action</th>
                {!showNl && <th className="text-left px-4 py-2 text-muted">Days</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((c: any) => {
                const open = expanded === c.id
                return (
                  <Fragment key={c.id}>
                    <tr className={`border-t border-card-border ${c.is_overdue ? 'bg-red-50/30' : ''}`}>
                      <td className="px-4 py-3 align-top">
                        <Link to={`/cases/${c.id}`} className="text-heading hover:underline">{c.case_id}</Link>
                        <div className="mt-1"><SourceBadge type={c.source_type} name={c.source_name} compact /></div>
                      </td>
                      <td className="px-4 py-3 align-top">
                        <button onClick={() => setExpanded(open ? null : c.id)} className="flex items-start gap-1 text-left text-heading hover:underline">
                          <span className="max-w-[280px] truncate">{c.subject || c.narrative_preview || '—'}</span>
                          {open ? <ChevronUp size={14} className="mt-0.5 shrink-0" /> : <ChevronDown size={14} className="mt-0.5 shrink-0" />}
                        </button>
                      </td>
                      <td className="px-4 py-3 align-top text-muted max-w-[220px] truncate">{c.institution_name || c.raw_institution_text}</td>
                      <td className="px-4 py-3 align-top text-muted">{label(c.complainant_type)}</td>
                      <td className="px-4 py-3 align-top">{c.bureau_code}</td>
                      <td className="px-4 py-3 align-top text-muted">
                        <div>{label(c.category)}</div>
                        {c.category_subtype && <div className="text-[11px] opacity-70">{label(c.category_subtype)}</div>}
                      </td>
                      <td className="px-4 py-3 align-top text-muted">{label(c.status)}</td>
                      <td className="px-4 py-3 align-top text-muted max-w-[220px] truncate">{c.last_action_text || '—'}</td>
                      {!showNl && <td className="px-4 py-3 align-top text-muted">{c.days_open}{c.is_overdue && ' ⚠'}</td>}
                    </tr>
                    {open && (
                      <tr key={`${c.id}-detail`} className="border-t border-card-border bg-page-bg/60">
                        <td colSpan={showNl ? 8 : 9} className="px-4 py-4">
                          <div className="text-sm font-medium text-heading">{c.subject || 'No subject'}</div>
                          <div className="text-xs text-muted mt-1">
                            Received {c.date_received?.slice(0, 10)} · {label(c.category)}{c.category_subtype ? ` / ${label(c.category_subtype)}` : ''} · {label(c.complainant_type)}
                          </div>
                          <p className="text-sm text-muted mt-2 max-w-4xl whitespace-pre-wrap">{c.narrative_preview || c.narrative || 'No narrative preview available.'}</p>
                          <Link to={`/cases/${c.id}`} className="inline-block text-xs text-heading mt-2 hover:underline">Open full case →</Link>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
              {!rows.length && <tr><td colSpan={showNl ? 8 : 9} className="px-5 py-6 text-sm text-muted">No matching cases.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {!showNl && <div className="text-xs text-muted">{data?.total || 0} cases total · showing first {data?.items?.length || 0}</div>}
    </div>
  )
}
