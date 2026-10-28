import { useMemo, useState } from 'react'
import clsx from 'clsx'
import { humanize, rupees, shortDate } from '../lib/format'
import { catIcon } from './categories'
import { Shell } from './Shell'

type Tx = { date: string; description: string; category: string; amount: number; balance_after: number }

export default function TransactionsCard({ data }: { data: { items: Tx[] } }) {
  const items = data.items ?? []
  const cats = useMemo(() => Array.from(new Set(items.map((t) => t.category))), [items])
  const [cat, setCat] = useState<string | null>(null)
  const shown = cat ? items.filter((t) => t.category === cat) : items
  const net = shown.reduce((s, t) => s + t.amount, 0)
  return (
    <Shell title={`${items.length} transactions`} aside={<span className={clsx('tabular text-[13px] font-medium', net >= 0 ? 'text-credit' : 'text-debit')}>Net {net >= 0 ? '+' : '−'}{rupees(Math.abs(net))}</span>}>
      {cats.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filter by category">
          <Chip on={!cat} onClick={() => setCat(null)}>All</Chip>
          {cats.map((c) => <Chip key={c} on={cat === c} onClick={() => setCat(cat === c ? null : c)}>{humanize(c)}</Chip>)}
        </div>
      )}
      <ul className="divide-y divide-edge/60">
        {shown.map((t, i) => {
          const Icon = catIcon(t.category)
          return (
            <li key={i} className="flex items-center gap-3 py-2.5">
              <Icon size={18} className="shrink-0 text-ink-3" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] text-ink">{t.description}</p>
                <p className="text-[12px] text-ink-3">{shortDate(t.date)} · {humanize(t.category)}</p>
              </div>
              <div className="text-right">
                <p className={clsx('tabular text-[14px] font-medium', t.amount >= 0 ? 'text-credit' : 'text-ink')}>{t.amount >= 0 ? '+' : '−'}{rupees(Math.abs(t.amount))}</p>
                <p className="tabular text-[12px] text-ink-3">{rupees(t.balance_after)}</p>
              </div>
            </li>
          )
        })}
      </ul>
    </Shell>
  )
}

function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" aria-pressed={on} onClick={onClick}
      className={clsx('rounded-full px-2.5 py-1 text-[12px] transition-colors', on ? 'bg-ground text-white' : 'bg-surface-3 text-ink-2 hover:text-ink')}>
      {children}
    </button>
  )
}
