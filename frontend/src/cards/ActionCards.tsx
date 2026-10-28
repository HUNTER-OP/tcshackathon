import { useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'
import { CheckCircle2, ChevronDown, Headset, Lock, PhoneCall, ShieldOff, XCircle } from 'lucide-react'
import { humanize, rupees } from '../lib/format'
import { ActionButton, Shell, useSend } from './Shell'

export function CardActionCard({ data }: { data: { card: string; type: string; status: string; reference: string; replacement_eta_days?: number } }) {
  const send = useSend()
  const reduce = useReducedMotion()
  const blocked = data.status === 'blocked'
  return (
    <Shell title={`${humanize(data.type)} card`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative aspect-[1.586] w-full max-w-[260px] overflow-hidden rounded-xl bg-bahi p-4 text-[#f6efe0]">
          <p className="font-display text-[15px]">Hisab Kitab</p>
          <div className="mt-4 h-6 w-9 rounded-[4px] bg-[#e3a72f]" aria-hidden />
          <p className="tabular mt-4 text-[17px] tracking-[0.12em]">{data.card.replace('XXXX', '•••• •••• •••• ')}</p>
          <p className="mt-1 text-[11px] opacity-80">{humanize(data.type)}</p>
          {blocked && (
            <motion.div initial={reduce ? false : { opacity: 0, scale: 1.3, rotate: -14 }} animate={{ opacity: 1, scale: 1, rotate: -10 }}
              transition={{ type: 'spring', stiffness: 260, damping: 18, delay: 0.15 }}
              className="absolute inset-0 grid place-items-center bg-black/35">
              <span className="rounded-md border-[3px] border-[#f6efe0] px-3 py-1 font-display text-[22px] font-semibold tracking-[0.06em]">Blocked</span>
            </motion.div>
          )}
        </div>
        <div className="space-y-1.5 text-[14px]">
          <p className="inline-flex items-center gap-2 text-ink"><ShieldOff size={16} className="text-debit" aria-hidden />No one can use this card now.</p>
          <p className="text-ink-2">Reference <span className="tabular text-ink">{data.reference}</span></p>
          {data.replacement_eta_days != null && <p className="text-ink-2">A new card reaches you in about {data.replacement_eta_days} days.</p>}
          <div className="pt-2"><ActionButton onClick={() => send('I want to dispute a transaction on this card')}>Report a fraudulent payment</ActionButton></div>
        </div>
      </div>
    </Shell>
  )
}

export function TransferCard({ data }: { data: { status: string; ref?: string; amount?: number; to?: string; balance_after?: number; reason?: string } }) {
  const ok = data.status === 'success'
  return (
    <Shell title="Transfer receipt">
      <div className="flex items-start gap-3">
        {ok ? <CheckCircle2 className="mt-1 text-credit" aria-hidden /> : <XCircle className="mt-1 text-debit" aria-hidden />}
        <div className="flex-1">
          <p className="font-display tabular text-[28px] leading-tight">{data.amount != null ? rupees(data.amount) : '—'}</p>
          <p className="text-[14px] text-ink-2">{ok ? `Sent to ${data.to}` : `Not sent: ${data.reason ?? 'failed'}`}</p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[13px]">
            {data.ref && <><dt className="text-ink-3">UTR</dt><dd className="tabular text-ink">{data.ref}</dd></>}
            {data.balance_after != null && <><dt className="text-ink-3">Balance after</dt><dd className="tabular text-ink">{rupees(data.balance_after)}</dd></>}
          </dl>
        </div>
      </div>
    </Shell>
  )
}

export function HandoffCard({ data }: { data: { ticket_id: string; summary: string; sentiment: string; priority: string } }) {
  const tone = data.sentiment === 'negative' || data.priority === 'high' ? 'text-debit' : 'text-ink'
  return (
    <Shell title={`Ticket ${data.ticket_id}`} aside={<span className="inline-flex items-center gap-1.5 text-[12px] text-credit"><span className="relative flex h-2 w-2"><span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-credit opacity-60" /><span className="relative inline-flex h-2 w-2 rounded-full bg-credit" /></span>Agent assigned</span>}>
      <div className="flex gap-3">
        <Headset className="mt-0.5 shrink-0 text-accent" aria-hidden />
        <div className="space-y-2">
          <p className="text-[14px] text-ink">{data.summary}</p>
          <p className="text-[13px] text-ink-2">Priority <b className={clsx('font-medium', tone)}>{humanize(data.priority)}</b> · mood <b className={clsx('font-medium', tone)}>{humanize(data.sentiment)}</b></p>
          <p className="inline-flex items-center gap-2 text-[13px] text-ink-2"><PhoneCall size={14} aria-hidden />An agent will call your registered number. The conversation so far goes with the ticket, so you won't repeat yourself.</p>
        </div>
      </div>
    </Shell>
  )
}

export function ConsentCard({ data }: { data: { message: string } }) {
  return (
    <Shell title="Personal data is locked">
      <div className="flex gap-3">
        <Lock className="mt-0.5 shrink-0 text-warn" aria-hidden />
        <div className="space-y-1.5 text-[14px]">
          <p className="text-ink">{data.message}</p>
          <p className="text-ink-2">You can still ask about rates, loans, fees and branches.</p>
        </div>
      </div>
    </Shell>
  )
}

export function FollowupCard({ data }: { data: { missing: string[]; question: string; options: string[] } }) {
  const send = useSend()
  return (
    <Shell title={data.question}>
      <div className="flex flex-wrap gap-2">
        {data.options.map((o) => <ActionButton key={o} onClick={() => send(o)}>{o}</ActionButton>)}
      </div>
      {data.missing.length > 0 && <p className="mt-3 text-[12px] text-ink-3">Needed: {data.missing.map((m) => humanize(m.replace('_inr', ''))).join(', ')}</p>}
    </Shell>
  )
}

export function FaqCard({ data }: { data: { items: { q: string; a: string; score?: number }[] } }) {
  const [open, setOpen] = useState<number | null>(0)
  return (
    <Shell title="From our help pages">
      <ul className="divide-y divide-edge/60">
        {data.items.map((it, i) => (
          <li key={i}>
            <button type="button" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-center justify-between gap-3 py-2.5 text-left text-[14px] text-ink">
              {it.q}
              <ChevronDown size={16} className={clsx('shrink-0 text-ink-3 transition-transform', open === i && 'rotate-180')} aria-hidden />
            </button>
            {open === i && <p className="pb-3 text-[14px] text-ink-2">{it.a}</p>}
          </li>
        ))}
      </ul>
    </Shell>
  )
}
