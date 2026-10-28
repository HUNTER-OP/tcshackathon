import { useState } from 'react'
import clsx from 'clsx'
import { humanize, rupees } from '../lib/format'
import { catIcon } from './categories'
import { Shell, useSend } from './Shell'

export default function SpendingCard({ data }: { data: { days: number; total_debit: number; total_credit: number; by_category: Record<string, number> } }) {
  const send = useSend()
  const rows = Object.entries(data.by_category || {}).sort((a, b) => b[1] - a[1])
  const max = rows[0]?.[1] || 1
  const [hover, setHover] = useState<string | null>(null)
  const saved = data.total_credit - data.total_debit
  return (
    <Shell title={`Spending, last ${data.days} days`}>
      <div className="mb-4 grid grid-cols-3 gap-3">
        <Stat label="Spent" value={rupees(data.total_debit)} />
        <Stat label="Received" value={rupees(data.total_credit)} tone="credit" />
        <Stat label={saved >= 0 ? 'Saved' : 'Overspent'} value={rupees(Math.abs(saved))} tone={saved >= 0 ? 'credit' : 'debit'} />
      </div>
      <ul className="space-y-2">
        {rows.map(([cat, amt], i) => {
          const Icon = catIcon(cat)
          const pct = Math.round((amt / (data.total_debit || 1)) * 100)
          return (
            <li key={cat}>
              <button type="button" onClick={() => send(`Show my ${humanize(cat).toLowerCase()} transactions from the last ${data.days} days`)}
                onMouseEnter={() => setHover(cat)} onMouseLeave={() => setHover(null)}
                className="group grid w-full grid-cols-[20px_96px_1fr_auto] items-center gap-3 rounded-md py-1 text-left">
                <Icon size={16} className="text-ink-3" aria-hidden />
                <span className="truncate text-[13px] text-ink">{humanize(cat)}</span>
                <span className="relative h-2.5 rounded-full bg-surface-3">
                  <span className={clsx('absolute inset-y-0 left-0 rounded-full transition-[width,background-color] duration-500', i === 0 || hover === cat ? 'bg-accent' : 'bg-ink-3')}
                    style={{ width: `${(amt / max) * 100}%` }} />
                </span>
                <span className="tabular w-[104px] text-right text-[13px] text-ink">{rupees(amt)} <span className="text-ink-3">{pct}%</span></span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="mt-3 text-[12px] text-ink-3">Select a category to see its transactions.</p>
    </Shell>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'credit' | 'debit' }) {
  return (
    <div className="rounded-lg bg-surface p-3">
      <p className="text-[12px] text-ink-3">{label}</p>
      <p className={clsx('font-display tabular mt-1 text-[20px] leading-tight', tone === 'credit' ? 'text-credit' : tone === 'debit' ? 'text-debit' : 'text-ink')}>{value}</p>
    </div>
  )
}
