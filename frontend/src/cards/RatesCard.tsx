import { useState } from 'react'
import clsx from 'clsx'
import { rupees } from '../lib/format'
import { Shell, useSend } from './Shell'

type Deposits = { savings?: { rate: number; min_balance: number; note?: string }; fd?: { tenor: string; rate: number }[]; senior_citizen_bonus?: number; rd?: { rate: number; min_monthly: number } }
type Loans = Record<string, { name: string; rate: number; max_tenure_months: number; processing_fee_pct?: number }>

export default function RatesCard({ data }: { data: { deposits?: Deposits; loans?: Loans } }) {
  const send = useSend()
  const tabs = [data.deposits && 'Deposits', data.loans && 'Loans'].filter(Boolean) as string[]
  const [tab, setTab] = useState(tabs[0] ?? 'Deposits')
  const [senior, setSenior] = useState(false)
  const bonus = senior ? data.deposits?.senior_citizen_bonus ?? 0 : 0
  const best = Math.max(...(data.deposits?.fd ?? [{ rate: 0 }]).map((f) => f.rate))
  return (
    <Shell title="Interest rates today"
      aside={tabs.length > 1 && (
        <div className="flex rounded-full bg-surface-3 p-0.5" role="tablist">
          {tabs.map((t) => (
            <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
              className={clsx('rounded-full px-3 py-1 text-[12px] font-medium transition-colors', tab === t ? 'bg-ground text-white' : 'text-ink-2 hover:text-ink')}>{t}</button>
          ))}
        </div>
      )}>
      {tab === 'Deposits' && data.deposits && (
        <div>
          {data.deposits.fd && (
            <table className="w-full text-[14px]">
              <thead><tr className="text-left text-[12px] text-ink-3"><th className="pb-2 font-normal">Fixed deposit tenor</th><th className="pb-2 text-right font-normal">Rate a year</th></tr></thead>
              <tbody>
                {data.deposits.fd.map((f) => (
                  <tr key={f.tenor} className="border-t border-edge/60">
                    <td className="py-2 text-ink">{f.tenor}</td>
                    <td className={clsx('tabular py-2 text-right font-medium', f.rate === best ? 'text-accent' : 'text-ink')}>{(f.rate + bonus).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-ink-2">
            {data.deposits.savings && <span>Savings <b className="tabular text-ink">{data.deposits.savings.rate}%</b> · min balance {rupees(data.deposits.savings.min_balance)}</span>}
            {data.deposits.rd && <span>Recurring deposit <b className="tabular text-ink">{data.deposits.rd.rate}%</b> from {rupees(data.deposits.rd.min_monthly)}/month</span>}
            {!!data.deposits.senior_citizen_bonus && (
              <label className="inline-flex cursor-pointer items-center gap-2">
                <input type="checkbox" checked={senior} onChange={(e) => setSenior(e.target.checked)} className="accent-[var(--accent)]" />
                Senior citizen (+{data.deposits.senior_citizen_bonus}%)
              </label>
            )}
          </div>
        </div>
      )}
      {tab === 'Loans' && data.loans && (
        <ul className="divide-y divide-edge/60">
          {Object.entries(data.loans).map(([k, l]) => (
            <li key={k} className="flex items-center justify-between gap-3 py-2.5">
              <div>
                <p className="text-[14px] text-ink">{l.name}</p>
                <p className="text-[12px] text-ink-3">Up to {Math.round(l.max_tenure_months / 12)} years{l.processing_fee_pct != null ? ` · ${l.processing_fee_pct}% processing fee` : ''}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="tabular font-display text-[22px] text-ink">{l.rate}%</span>
                <button type="button" onClick={() => send(`Am I eligible for a ${k} loan?`)} className="rounded-full border-[1.5px] border-line bg-surface px-3 py-1 text-[12px] font-medium text-ink hover:bg-accent">Check eligibility</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Shell>
  )
}
