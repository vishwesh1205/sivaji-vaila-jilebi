import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import api from '../lib/api'

const pct = (value?: number | null) => (value == null ? '—' : `${Math.round(value * 100)}%`)

export default function MatchingEvaluation() {
  const { data, isFetching, refetch, isError } = useQuery({
    queryKey: ['matching-evaluation'],
    queryFn: async () => (await api.get('/matching/evaluation')).data,
    staleTime: 5 * 60 * 1000,
  })

  const chart = (data?.methods || []).map((method: any) => ({
    name: method.label,
    'Binary F1': method.test.binary.f1,
    'Macro F1': method.test.three_class.macro_f1,
  }))

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-heading">Matching Evaluation</h1>
          <p className="text-sm text-muted">Complaint-to-complaint matching benchmark with group-safe development and test partitions.</p>
        </div>
        <button onClick={() => refetch()} disabled={isFetching} className="px-3 py-2 rounded-lg text-sm border border-card-border disabled:opacity-50">
          {isFetching ? 'Running…' : 'Re-run benchmark'}
        </button>
      </div>

      {isError && <div className="text-sm text-red-700">Benchmark could not be loaded.</div>}

      {data && (
        <>
          <div className="rounded-card border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            <div className="font-medium">Synthetic benchmark — not a human-annotated evaluation</div>
            <p className="mt-1 text-amber-900">
              Every pair and label is synthetic by construction. No human annotators, adjudicators or inter-annotator agreement were involved.
              Use these metrics as an offline engineering check, not an official accuracy claim.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              ['Dataset', `${data.dataset.dataset_id}@${data.dataset.version}`],
              ['Pairs', data.dataset.counts.pairs],
              ['Development', data.split.development_pairs],
              ['Test', data.split.test_pairs],
              ['Split seed', data.split.seed],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg bg-card-bg border border-card-border p-3">
                <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
                <div className="text-sm font-semibold text-heading mt-1 break-words">{value}</div>
              </div>
            ))}
          </div>

          <div className="bg-card-bg border border-card-border rounded-card p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div>
                <div className="text-sm font-medium text-heading">Method comparison</div>
                <div className="text-xs text-muted mt-1">Thresholds tuned on development data only, then applied unchanged to test data.</div>
              </div>
              <div className="text-xs text-muted">Binary positives = DUPLICATE + RELATED</div>
            </div>
            <div className="h-64 mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart} margin={{ top: 8, right: 8, left: -16, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={60} />
                  <YAxis domain={[0, 1]} tickFormatter={(value) => `${Math.round(value * 100)}%`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: any) => pct(value)} />
                  <Bar dataKey="Binary F1" fill="#1f6f5c" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Macro F1" fill="#b7791f" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-sm">
                <thead className="bg-page-bg text-muted">
                  <tr>
                    <th className="text-left px-3 py-2">Method</th>
                    <th className="text-right px-3 py-2">Thresholds (related / duplicate)</th>
                    <th className="text-right px-3 py-2">Precision</th>
                    <th className="text-right px-3 py-2">Recall</th>
                    <th className="text-right px-3 py-2">Binary F1</th>
                    <th className="text-right px-3 py-2">3-class macro F1</th>
                    <th className="text-right px-3 py-2">Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {data.methods.map((method: any) => (
                    <tr key={method.id} className="border-t border-card-border">
                      <td className="px-3 py-3">
                        <div className="text-heading">{method.label}</div>
                        <div className="text-xs text-muted max-w-xl">{method.description}</div>
                      </td>
                      <td className="px-3 py-3 text-right text-muted">{method.thresholds.related.toFixed(3)} / {method.thresholds.duplicate.toFixed(3)}</td>
                      <td className="px-3 py-3 text-right">{pct(method.test.binary.precision)}</td>
                      <td className="px-3 py-3 text-right">{pct(method.test.binary.recall)}</td>
                      <td className="px-3 py-3 text-right font-medium text-heading">{pct(method.test.binary.f1)}</td>
                      <td className="px-3 py-3 text-right">{pct(method.test.three_class.macro_f1)}</td>
                      <td className="px-3 py-3 text-right">{pct(method.test.three_class.accuracy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <div className="bg-card-bg border border-card-border rounded-card p-5">
              <div className="text-sm font-medium text-heading">Per-class results and confusion matrix</div>
              <div className="text-xs text-muted mt-1">Shown for TF-IDF word n-grams, the best macro-F1 method in this run.</div>
              {data.methods.filter((method: any) => method.id === 'tfidf_word').map((method: any) => (
                <div key={method.id} className="mt-4 space-y-4">
                  <table className="w-full text-sm">
                    <thead className="bg-page-bg text-muted">
                      <tr>
                        <th className="text-left px-3 py-2">Class</th>
                        <th className="text-right px-3 py-2">Precision</th>
                        <th className="text-right px-3 py-2">Recall</th>
                        <th className="text-right px-3 py-2">F1</th>
                        <th className="text-right px-3 py-2">Support</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(method.test.three_class.per_class).map(([label, values]: [string, any]) => (
                        <tr key={label} className="border-t border-card-border">
                          <td className="px-3 py-2 text-heading">{label}</td>
                          <td className="px-3 py-2 text-right">{pct(values.precision)}</td>
                          <td className="px-3 py-2 text-right">{pct(values.recall)}</td>
                          <td className="px-3 py-2 text-right">{pct(values.f1)}</td>
                          <td className="px-3 py-2 text-right text-muted">{values.support}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted mb-2">Confusion matrix · rows = true, columns = predicted</div>
                    <table className="w-full text-xs">
                      <thead>
                        <tr>
                          <th className="text-left px-2 py-1 text-muted">True \ Predicted</th>
                          {method.test.three_class.confusion_matrix.labels.map((label: string) => <th key={label} className="text-right px-2 py-1 text-muted">{label}</th>)}
                        </tr>
                      </thead>
                      <tbody>
                        {method.test.three_class.confusion_matrix.matrix.map((row: number[], index: number) => (
                          <tr key={method.test.three_class.confusion_matrix.labels[index]} className="border-t border-card-border">
                            <td className="px-2 py-2 text-heading">{method.test.three_class.confusion_matrix.labels[index]}</td>
                            {row.map((value, column) => <td key={column} className="px-2 py-2 text-right">{value}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-card-bg border border-card-border rounded-card p-5">
              <div className="text-sm font-medium text-heading">Language groups</div>
              <div className="text-xs text-muted mt-1">Test pairs grouped by same-language code or cross-language pair.</div>
              <div className="overflow-x-auto mt-4">
                <table className="w-full text-sm">
                  <thead className="bg-page-bg text-muted">
                    <tr>
                      <th className="text-left px-3 py-2">Group</th>
                      <th className="text-right px-3 py-2">Pairs</th>
                      <th className="text-right px-3 py-2">Precision</th>
                      <th className="text-right px-3 py-2">Recall</th>
                      <th className="text-right px-3 py-2">Binary F1</th>
                      <th className="text-right px-3 py-2">Macro F1</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.methods.filter((method: any) => method.id === 'tfidf_word').flatMap((method: any) => method.test.by_language.map((group: any) => (
                      <tr key={group.language_group} className="border-t border-card-border">
                        <td className="px-3 py-2 text-heading">{group.language_group}</td>
                        <td className="px-3 py-2 text-right text-muted">{group.pairs}</td>
                        <td className="px-3 py-2 text-right">{pct(group.precision)}</td>
                        <td className="px-3 py-2 text-right">{pct(group.recall)}</td>
                        <td className="px-3 py-2 text-right">{pct(group.binary_f1)}</td>
                        <td className="px-3 py-2 text-right">{pct(group.macro_f1)}</td>
                      </tr>
                    )))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 rounded-lg border border-card-border bg-page-bg p-3 text-xs text-muted">
                Cross-language aggregate binary F1: {pct(data.methods[0]?.test.cross_language.binary?.f1)}. Lexical fallbacks are expected to struggle here; no semantic model was run.
              </div>
            </div>
          </div>

          <div className="bg-card-bg border border-card-border rounded-card p-5">
            <div className="text-sm font-medium text-heading">Ablation results</div>
            <div className="text-xs text-muted mt-1">Hybrid components removed one at a time; the full hybrid and single-signal baselines are shown for context.</div>
            <div className="overflow-x-auto mt-4">
              <table className="w-full text-sm">
                <thead className="bg-page-bg text-muted">
                  <tr>
                    <th className="text-left px-3 py-2">Variant</th>
                    <th className="text-right px-3 py-2">Thresholds</th>
                    <th className="text-right px-3 py-2">Binary F1</th>
                    <th className="text-right px-3 py-2">Macro F1</th>
                    <th className="text-right px-3 py-2">Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ablation.map((variant: any) => (
                    <tr key={variant.id} className="border-t border-card-border">
                      <td className="px-3 py-2 text-heading">{variant.description}</td>
                      <td className="px-3 py-2 text-right text-muted">{variant.thresholds.related.toFixed(3)} / {variant.thresholds.duplicate.toFixed(3)}</td>
                      <td className="px-3 py-2 text-right">{pct(variant.binary_f1)}</td>
                      <td className="px-3 py-2 text-right">{pct(variant.macro_f1)}</td>
                      <td className="px-3 py-2 text-right">{pct(variant.accuracy)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-card-bg border border-card-border rounded-card p-5">
            <div className="text-sm font-medium text-heading">Semantic method status</div>
            {data.unavailable_methods.map((method: any) => (
              <div key={method.id} className="mt-3 rounded-lg border border-alert-border bg-alert-bg p-3">
                <div className="text-sm font-medium text-alert-text">{method.label}: not run</div>
                <p className="text-sm text-muted mt-1">{method.reason}</p>
              </div>
            ))}
            <p className="text-xs text-muted mt-3">The precedent engine therefore uses the documented TF-IDF/fuzzy fallback rather than pretending a semantic model ran.</p>
          </div>

          <div className="text-xs text-muted">
            {data.notes.map((note: string) => <div key={note}>• {note}</div>)}
            <div className="mt-2">Generated {new Date(data.generated_at + 'Z').toLocaleString()} · Dataset {data.dataset.dataset_id}@{data.dataset.version}</div>
          </div>
        </>
      )}
      {!data && !isError && <div className="text-sm text-muted">Running benchmark…</div>}
    </div>
  )
}
