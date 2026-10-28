import { Fragment } from 'react'
import clsx from 'clsx'
import { Cloud, HardDrive, ShieldCheck, X } from 'lucide-react'
import type { ChatResult } from '../lib/types'
import { LANG_LABEL, humanize, lakh, modelLabel } from '../lib/format'

const STAGE_LABEL: Record<string, string> = {
  language: 'Language', privacy: 'Privacy filter', intent: 'Intent model', translate: 'Translation', entities: 'Details',
  tools: 'Bank API', rag: 'Help search', reply: 'AI reply', llm: 'AI reply', handoff: 'Handoff',
}

export default function TracePanel({ result, onClose }: { result: ChatResult | null; onClose?: () => void }) {
  return (
    <aside className="flex h-full flex-col overflow-y-auto bg-surface p-5 scroll-quiet" aria-labelledby="trace-h">
      <div className="mb-5 flex items-center justify-between">
        <h2 id="trace-h" className="font-display text-[20px] tracking-[-0.01em]">Why this answer</h2>
        {onClose && <button type="button" onClick={onClose} className="rounded-md p-1.5 text-ink-2 hover:bg-surface-2" aria-label="Close panel"><X size={16} /></button>}
      </div>
      {!result ? (
        <p className="text-[14px] text-ink-2">Ask a question. Each step Hisab Kitab took to answer it shows up here: the language it heard, what it understood, which bank records it read and which AI model wrote the reply.</p>
      ) : <Trace r={result} />}
    </aside>
  )
}

function Trace({ r }: { r: ChatResult }) {
  const model = modelLabel(r.model_used)
  const stages = r.stages ?? []
  const total = Math.max(1, stages.reduce((s, x) => s + x.ms, 0))
  const ents = Object.entries(r.entities || {})
  return (
    <div className="space-y-6 text-[14px]">
      <Row label="Understood as">
        <p className="text-[16px] font-medium text-ink">{humanize(r.intent)}</p>
        <div className="mt-2 flex items-center gap-2">
          <span className="relative h-1.5 flex-1 rounded-full bg-surface-3">
            <span className={clsx('absolute inset-y-0 left-0 rounded-full', r.confidence >= 0.6 ? 'bg-credit' : r.confidence >= 0.45 ? 'bg-warn' : 'bg-debit')} style={{ width: `${r.confidence * 100}%` }} />
          </span>
          <span className="tabular text-[12px] text-ink-2">{Math.round(r.confidence * 100)}% sure</span>
        </div>
      </Row>

      <Row label="Language heard"><p className="text-ink">{LANG_LABEL[r.language] ?? r.language}</p></Row>

      <Row label="Details picked out">
        {ents.length === 0 ? <p className="text-ink-3">None needed</p> : (
          <div className="flex flex-wrap gap-1.5">
            {ents.map(([k, v]) => (
              <span key={k} className="rounded-md bg-surface-2 px-2 py-1 text-[12px]">
                <span className="text-ink-3">{humanize(k.replace('_inr', ''))} </span>
                <span className="tabular text-ink">{k === 'amount_inr' ? lakh(Number(v)) : k === 'tenure_months' ? `${v} months` : String(v)}</span>
              </span>
            ))}
          </div>
        )}
      </Row>

      <Row label="Privacy filter">
        <p className={clsx('inline-flex items-center gap-1.5', r.redactions ? 'text-credit' : 'text-ink-2')}>
          <ShieldCheck size={15} aria-hidden />
          {r.redactions ? `${r.redactions} personal number${r.redactions > 1 ? 's' : ''} hidden before the AI saw it` : 'Nothing sensitive found'}
        </p>
        {r.redactions > 0 && r.redacted_text && (
          <p className="mt-2 rounded-md bg-surface-2 p-2.5 text-[13px] text-ink-2">
            {r.redacted_text.split(/(\[[A-Z/]+\])/).map((s, i) => /^\[[A-Z/]+\]$/.test(s)
              ? <mark key={i} className="rounded bg-credit/20 px-1 text-credit">{s}</mark> : <Fragment key={i}>{s}</Fragment>)}
          </p>
        )}
      </Row>

      <Row label="Bank records read">
        {r.tool_calls.length === 0 ? <p className="text-ink-3">None</p> : (
          <ul className="space-y-1.5">
            {r.tool_calls.map((t, i) => (
              <li key={i} className="flex items-baseline justify-between gap-3 rounded-md bg-surface-2 px-2.5 py-1.5">
                <span className="min-w-0">
                  <span className="text-ink">{humanize(t.tool)}</span>
                  {t.args && Object.keys(t.args).length > 0 && (
                    <span className="block truncate text-[12px] text-ink-3">{Object.entries(t.args).filter(([, v]) => v != null && v !== '').map(([k, v]) => `${humanize(k)}: ${v}`).join(', ')}</span>
                  )}
                </span>
                {t.ms != null && <span className="tabular shrink-0 text-[12px] text-ink-3">{t.ms} ms</span>}
              </li>
            ))}
          </ul>
        )}
      </Row>

      <Row label="Answer written by">
        <span className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[13px] font-medium', model.local ? 'bg-credit/15 text-credit' : 'bg-accent/15 text-accent')}>
          {model.local ? <HardDrive size={14} /> : <Cloud size={14} />}{model.label}
        </span>
        <p className="mt-1.5 text-[12px] text-ink-3">{r.model_used}</p>
      </Row>

      {r.handoff && (
        <Row label="Handed to a person">
          <p className="text-ink">Ticket {r.handoff.ticket_id}, {r.handoff.priority} priority</p>
        </Row>
      )}

      <Row label={`Time taken: ${(r.latency_ms / 1000).toFixed(2)} s`}>
        {stages.length === 0 ? null : (
          <div className="space-y-1.5">
            <div className="flex h-2.5 overflow-hidden rounded-full bg-surface-3" aria-hidden>
              {stages.map((s, i) => (
                <span key={i} style={{ width: `${(s.ms / total) * 100}%` }} className={clsx(i % 2 ? 'bg-ink-3' : 'bg-accent', s.ms === 0 && 'hidden')} />
              ))}
            </div>
            <ul className="space-y-1 text-[12px]">
              {stages.map((s, i) => (
                <li key={i} className="flex justify-between gap-3">
                  <span className="inline-flex items-center gap-2 text-ink-2"><span className={clsx('h-2 w-2 rounded-full', i % 2 ? 'bg-ink-3' : 'bg-accent')} />{STAGE_LABEL[s.name] ?? humanize(s.name)}{s.detail ? <span className="text-ink-3">· {s.detail}</span> : null}</span>
                  <span className="tabular text-ink-3">{s.ms} ms</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Row>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-[12px] text-ink-3">{label}</h3>
      {children}
    </section>
  )
}
