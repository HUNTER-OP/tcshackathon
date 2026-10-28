import { useEffect, useState } from 'react'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Metrics } from '../lib/types'
import { getMetrics } from '../lib/api'
import { LANG_LABEL, humanize, modelLabel } from '../lib/format'

const tooltip = { contentStyle: { background: 'var(--surface)', border: '2px solid var(--line)', borderRadius: 10, color: 'var(--ink)', fontSize: 13 }, itemStyle: { color: 'var(--ink)' }, cursor: { fill: 'var(--surface-2)' } }
const SHADES = ['var(--ground)', 'var(--mint)', 'var(--accent)', 'var(--teal)', 'var(--navy)', 'var(--lime)']

export default function Dashboard() {
  const [m, setM] = useState<Metrics | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    let live = true
    const load = () => getMetrics().then((d) => { if (live) { setM(d); setErr(false) } }).catch(() => live && setErr(true))
    load()
    const t = setInterval(load, 5000)
    return () => { live = false; clearInterval(t) }
  }, [])

  const rate = m && m.total ? Math.round((m.resolved / m.total) * 100) : 0
  const intents = m ? Object.entries(m.by_intent).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ name: humanize(k), v })) : []
  const langs = m ? Object.entries(m.by_language).map(([k, v]) => ({ name: LANG_LABEL[k] ?? k, v })) : []
  const models = m ? Object.entries(m.by_model).map(([k, v]) => ({ name: modelLabel(k).label, v })) : []
  const modelTotal = models.reduce((s, x) => s + x.v, 0) || 1

  return (
    <div className="h-full overflow-y-auto scroll-quiet">
      <div className="mx-auto max-w-[1100px] px-4 py-8 sm:px-8">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-[34px] font-bold leading-tight tracking-[-0.02em]"><span className="hl">Operations dashboard</span></h1>
            <p className="text-[15px] text-ink-2">Every question Hisab Kitab has answered since the server started. Refreshes every 5 seconds.</p>
          </div>
          {err && <p className="rounded-md bg-debit/15 px-3 py-1.5 text-[13px] text-debit">Can't reach the server.</p>}
        </div>

        {!m ? <p className="text-ink-3">Loading…</p> : m.total === 0 ? (
          <p className="nb-card p-6 text-[15px] text-ink-2">No questions yet. Ask something in the assistant and this page fills in.</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              <Kpi label="Questions answered" value={String(m.total)} />
              <Kpi label="Resolved without a person" value={`${rate}%`} note={rate >= 80 ? 'Above the 80% target' : 'Below the 80% target'} good={rate >= 80} />
              <Kpi label="Handed to an agent" value={String(m.handoffs)} />
              <Kpi label="Average response" value={`${(m.avg_latency_ms / 1000).toFixed(2)} s`} />
              <Kpi label="95th percentile" value={`${(m.p95_latency_ms / 1000).toFixed(2)} s`} note={m.p95_latency_ms < 15000 ? 'Under the 15 s target' : 'Over the 15 s target'} good={m.p95_latency_ms < 15000} />
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-[1.6fr_1fr]">
              <Panel title="What customers ask about">
                <ResponsiveContainer width="100%" height={Math.max(180, intents.length * 30)}>
                  <BarChart data={intents} layout="vertical" margin={{ left: 0, right: 16, top: 0, bottom: 0 }}>
                    <XAxis type="number" hide allowDecimals={false} />
                    <YAxis type="category" dataKey="name" width={140} tick={{ fill: 'var(--ink-2)', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip {...tooltip} formatter={(v) => [v, 'Questions']} />
                    <Bar dataKey="v" radius={[0, 4, 4, 0]} barSize={16} isAnimationActive={false}>
                      {intents.map((_, i) => <Cell key={i} fill={i === 0 ? 'var(--ground)' : 'var(--mint)'} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Panel>
              <div className="grid gap-4">
                <Panel title="Languages">
                  <div className="flex items-center gap-4">
                    <ResponsiveContainer width={130} height={130}>
                      <PieChart>
                        <Pie data={langs} dataKey="v" nameKey="name" innerRadius={38} outerRadius={60} stroke="none" paddingAngle={2} isAnimationActive={false}>
                          {langs.map((_, i) => <Cell key={i} fill={SHADES[i % SHADES.length]} />)}
                        </Pie>
                        <Tooltip {...tooltip} />
                      </PieChart>
                    </ResponsiveContainer>
                    <ul className="space-y-1.5 text-[13px]">
                      {langs.map((l, i) => (
                        <li key={l.name} className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SHADES[i % SHADES.length] }} /><span className="text-ink">{l.name}</span><span className="tabular text-ink-3">{l.v}</span></li>
                      ))}
                    </ul>
                  </div>
                </Panel>
                <Panel title="Which AI wrote the answer">
                  <div className="flex h-3 overflow-hidden rounded-full bg-surface-3">
                    {models.map((x, i) => <span key={x.name} style={{ width: `${(x.v / modelTotal) * 100}%`, background: SHADES[i % SHADES.length] }} />)}
                  </div>
                  <ul className="mt-3 space-y-1 text-[13px]">
                    {models.map((x, i) => (
                      <li key={x.name} className="flex justify-between"><span className="inline-flex items-center gap-2 text-ink"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: SHADES[i % SHADES.length] }} />{x.name}</span><span className="tabular text-ink-3">{Math.round((x.v / modelTotal) * 100)}%</span></li>
                    ))}
                  </ul>
                </Panel>
              </div>
            </div>

            {m.recent && m.recent.length > 0 && (
              <Panel title="Latest questions" className="mt-4">
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[620px] text-[13px]">
                    <thead><tr className="text-left text-ink-3"><th className="pb-2 font-normal">Question</th><th className="pb-2 font-normal">Intent</th><th className="pb-2 font-normal">Language</th><th className="pb-2 font-normal">Model</th><th className="pb-2 text-right font-normal">Time</th></tr></thead>
                    <tbody>
                      {m.recent.slice(0, 12).map((r, i) => (
                        <tr key={i} className="border-t border-edge/60">
                          <td className="max-w-[320px] truncate py-2 pr-3 text-ink">{r.message}</td>
                          <td className="py-2 pr-3 text-ink-2">{humanize(r.intent)}</td>
                          <td className="py-2 pr-3 text-ink-2">{LANG_LABEL[r.language] ?? r.language}</td>
                          <td className="py-2 pr-3 text-ink-2">{modelLabel(r.model_used).label}</td>
                          <td className="tabular py-2 text-right text-ink-2">{(r.latency_ms / 1000).toFixed(2)} s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function Kpi({ label, value, note, good }: { label: string; value: string; note?: string; good?: boolean }) {
  return (
    <div className="nb-card p-4">
      <p className="text-[13px] text-ink-3">{label}</p>
      <p className="font-display tabular mt-1 text-[30px] leading-tight tracking-[-0.02em]">{value}</p>
      {note && <p className={good ? 'text-[12px] text-credit' : 'text-[12px] text-debit'}>{note}</p>}
    </div>
  )
}

function Panel({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`nb-card p-5 ${className}`}>
      <h2 className="mb-3 text-[14px] font-medium text-ink-2">{title}</h2>
      {children}
    </section>
  )
}
