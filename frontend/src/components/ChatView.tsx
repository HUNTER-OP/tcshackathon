import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowUp, Cloud, HardDrive, ShieldCheck } from 'lucide-react'
import type { ChatMessage, Lang } from '../lib/types'
import { LANG_LABEL, SPEECH_LANG, intentLabel, modelLabel } from '../lib/format'
import { GREETING, PROMPTS } from '../lib/prompts'
import { RenderCard } from '../cards'
import PipelineTicker from './PipelineTicker'
import VoiceButton from './VoiceButton'

type Props = {
  messages: ChatMessage[]
  pending: boolean
  lang: Lang
  customerName?: string
  selectedId: string | null
  onSelect: (id: string) => void
  onSend: (text: string) => void
}

export default function ChatView({ messages, pending, lang, customerName, selectedId, onSelect, onSend }: Props) {
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)
  const box = useRef<HTMLTextAreaElement>(null)
  const reduce = useReducedMotion()
  useEffect(() => { end.current?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'end' }) }, [messages.length, pending, reduce])

  const submit = (t = text) => {
    if (!t.trim() || pending) return
    onSend(t.trim())
    setText('')
  }
  const last = [...messages].reverse().find((m) => m.role === 'assistant' && m.result)
  const g = GREETING[lang]

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto scroll-quiet">
        <div className="mx-auto flex w-full max-w-[760px] flex-col gap-6 px-4 pb-6 pt-8 sm:px-6">
          {messages.length === 0 && (
            <div className="pt-[6vh]">
              <p className="mb-3 text-[14px] font-semibold tracking-[0.01em] text-teal">Every Rupee, Explained.</p>
              <h1 className="font-display text-[38px] font-bold leading-[1.15] tracking-[-0.02em] sm:text-[52px]">{g.title}</h1>
              <p className="mt-4 max-w-[52ch] text-[17px] text-ink-2">{g.line}</p>
              {customerName && <p className="mt-2 text-[14px] text-ink-3">Signed in as {customerName}.</p>}
              <ul className="mt-8 grid gap-2 sm:grid-cols-2">
                {PROMPTS[lang].map((p) => (
                  <li key={p}>
                    <button type="button" onClick={() => submit(p)}
                      className="w-full rounded-2xl border border-line bg-surface px-4 py-3 text-left text-[15px] font-medium text-ink transition-all hover:bg-surface-3">{p}</button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m) => (
              <motion.div key={m.id} initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}>
                {m.role === 'user' ? (
                  <div className="flex justify-end">
                    <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md border border-line bg-ground px-4 py-2.5 text-[15px] text-white">{m.content}</p>
                  </div>
                ) : (
                  <AssistantMessage m={m} selected={selectedId === m.id} onSelect={() => onSelect(m.id)} />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          {pending && <div className="pl-1"><PipelineTicker /></div>}
          <div ref={end} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-[760px] px-4 pb-4 sm:px-6">
        {!pending && last?.result?.suggestions && last.result.suggestions.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5" aria-label="Suggested questions">
            {last.result.suggestions.map((s) => (
              <button key={s} type="button" onClick={() => submit(s)} className="rounded-full border border-line bg-surface px-3 py-1 text-[13px] font-medium text-ink transition-colors hover:bg-accent">{s}</button>
            ))}
          </div>
        )}
        <form onSubmit={(e) => { e.preventDefault(); submit() }} className="flex items-end gap-2 rounded-2xl border border-line bg-surface p-2 transition-colors focus-within:border-ground">
          <label htmlFor="composer" className="sr-only">Ask Hisab Kitab</label>
          <textarea id="composer" ref={box} rows={1} value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
            placeholder={`Ask in ${LANG_LABEL[lang]} or any language…`}
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-[15px] text-ink outline-none placeholder:text-ink-3" />
          <VoiceButton lang={SPEECH_LANG[lang]} onText={setText} onFinal={(t) => submit(t)} />
          <button type="submit" disabled={!text.trim() || pending} aria-label="Send"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line bg-accent text-accent-ink transition-opacity disabled:opacity-40">
            <ArrowUp size={18} />
          </button>
        </form>
        <p className="mt-2 text-center text-[12px] text-ink-3">Card, Aadhaar, PAN and phone numbers are hidden before any AI model sees them.</p>
      </div>
    </div>
  )
}

function AssistantMessage({ m, selected, onSelect }: { m: ChatMessage; selected: boolean; onSelect: () => void }) {
  const r = m.result
  const model = r ? modelLabel(r.model_used) : null
  const reduce = useReducedMotion()
  return (
    <div className="flex gap-3">
      <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full border border-line bg-ground font-display text-[13px] font-bold text-accent" aria-hidden>हि</span>
      <div className="min-w-0 flex-1 space-y-3">
        <div className={clsx('md text-[15px] leading-relaxed', m.error ? 'text-debit' : 'text-ink')}>
          <Markdown remarkPlugins={[remarkGfm]}>{m.content}</Markdown>
        </div>
        {r?.cards?.map((c, i) => (
          <motion.div key={i} initial={reduce ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 + i * 0.07, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}>
            <RenderCard card={c} />
          </motion.div>
        ))}
        {r && (
          <button type="button" onClick={onSelect} aria-pressed={selected}
            className={clsx('flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md px-1.5 py-1 text-[12px] transition-colors', selected ? 'bg-surface-3 text-ink-2' : 'text-ink-3 hover:text-ink-2')}>
            <span className="font-medium text-ink-2">{intentLabel(r.intent)} · {Math.round(r.confidence * 100)}%</span>
            <span className="inline-flex items-center gap-1">{model?.local ? <HardDrive size={12} /> : <Cloud size={12} />}{model?.label}</span>
            <span className="tabular">{(r.latency_ms / 1000).toFixed(2)} s</span>
            {r.redactions > 0 && <span className="inline-flex items-center gap-1 text-credit"><ShieldCheck size={12} />{r.redactions} hidden</span>}
            <span className="underline decoration-dotted underline-offset-2">Why this answer</span>
          </button>
        )}
      </div>
    </div>
  )
}
