import { Fragment, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { ChevronDown, ChevronUp, Search } from 'lucide-react'
import api from '../lib/api'
import SourceBadge from '../components/SourceBadge'
import QueryChips from '../components/QueryChips'

const PAGE_SIZE = 50
const label = (value?: string | null) => (value || '—').replace(/_/g, ' ').toLowerCase()

function csvCell(value: unknown) {
  return `"${String(value ?? '').replace(/"/g, '""')}"`
}

function exportRowsToCsv(rows: any[], institutions: boolean) {
  if (!rows.length) return
  const headers = institutions
    ? ['Institution', 'AICTE ID', 'Region', 'Source']
    : ['Case ID', 'Subject', 'Institution', 'Complainant', 'Bureau', 'Category', 'Sub-type', 'Status', 'Last action', 'Days open', 'Source']
  const body = rows.map((row) => institutions
    ? [row.name, row.aicte_permanent_id, row.region, row.source_type]
    : [row.case_id, row.subject || row.narrative_preview, row.institution_name || row.raw_institution_text, label(row.complainant_type), row.bureau_code, label(row.category), label(row.category_subtype), label(row.status), row.last_action_text, row.days_open, `${row.source_type || ''}${row.source_name ? ` / ${row.source_name}` : ''}`])
  const csv = [headers, ...body].map((line) => line.map(csvCell).join(',')).join('\r\n')
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${institutions ? 'institutions' : 'cases'}-export-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export default function CaseTracking() {
  const [searchParams, setSearchParams] = useSearchParams()
  const urlSearch = searchParams.get('search') || ''
  const [input, setInput] = useState('')
  const [submitted, setSubmitted] = useState('')
  const [search, setSearch] = useState(urlSearch)
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<number | null>(null)
  const { data, isFetching: casesFetching } = useQuery({
    queryKey: ['cases', page, search],
    queryFn: async () => (await api.get('/cases', { params: { page, limit: PAGE_SIZE, ...(search ? { q: search } : {}) } })).data,
    enabled: !submitted,
  })
  const { data: nl, isFetching: nlFetching } = useQuery({
    queryKey: ['case-query', submitted],
    queryFn: async () => (await api.post('/innovations/query/execute', { query: submitted })).data,
    enabled: !!submitted,
  })

  useEffect(() => {
    setSearch(urlSearch)
    setPage(1)
  }, [urlSearch])

  useEffect(() => {
    setPage(1)
  }, [submitted])

  const submit = (text: string) => {
    setInput(text)
    setSubmitted(text.trim())
  }

  const clearSearch = () => {
    setSearch('')
    setSearchParams({})
    setPage(1)
  }

  const showNl = !!submitted && !!nl
  const showInstitutions = showNl && nl.target === 'institutions'
  const allRows = showNl ? nl.results || [] : data?.items || []
  const total = showNl ? nl.result_count || allRows.length : data?.total || 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const rows = showNl ? allRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : allRows
  const isFetching = showNl ? nlFetching : casesFetching

  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-heading">Case Tracking</h1>
          <p className="text-sm text-muted">Track, filter and query all cases</p>
        </div>
        <button onClick={() => exportRowsToCsv(rows, showInstitutions)} disabled={!rows.length} title="Exports the rows currently shown" className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">CSV Export</button>
      </div>

      {search && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-card-border bg-card-bg px-4 py-3 text-sm">
          <span className="text-muted">Filtering by <span className="text-heading font-medium">{search}</span></span>
          <button onClick={clearSearch} className="text-xs text-muted hover:text-heading">Clear search</button>
        </div>
      )}

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
        {isFetching && <div className="text-xs text-muted">{showNl ? 'Interpreting query…' : 'Loading cases…'}</div>}
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

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
        <span>
          {total} {showInstitutions ? 'institution(s)' : 'case(s)'} total
          {total > 0 ? ` · showing ${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, total)}` : ''}
        </span>
        <div className="flex items-center gap-2">
          <button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} className="px-3 py-1.5 rounded-lg border border-card-border disabled:opacity-40">Previous</button>
          <span>Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))} className="px-3 py-1.5 rounded-lg border border-card-border disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  )
}
