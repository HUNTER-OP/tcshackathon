import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { CheckCircle2, XCircle } from 'lucide-react'
import { getEmi } from '../lib/api'
import { lakh, rupees } from '../lib/format'
import { ActionButton, Shell, useSend } from './Shell'

const MAX_TENURE: Record<string, number> = { home: 360, car: 84, personal: 60, education: 180 }

type Loan = {
  loan_type: string; product: string; requested_amount: number; tenure_months: number; rate: number; emi: number
  eligible: boolean; max_amount: number; affordable_emi: number; existing_emi: number; monthly_income: number
  credit_score: number; foir_after: number; processing_fee: number; reasons: string[]
}

export default function LoanCard({ data }: { data: Loan }) {
  const send = useSend()
  const maxTenure = MAX_TENURE[data.loan_type] ?? Math.max(data.tenure_months, 60)
  const amountMax = Math.max(Math.ceil((Math.max(data.max_amount, data.requested_amount) * 1.5) / 100000) * 100000, 200000)
  const [amount, setAmount] = useState(data.requested_amount)
  const [tenure, setTenure] = useState(data.tenure_months)
  const [emi, setEmi] = useState(data.emi)
  const [busy, setBusy] = useState(false)
  const first = useRef(true)

  useEffect(() => {
    if (first.current) { first.current = false; return }
    setBusy(true)
    const t = setTimeout(() => {
      getEmi(amount, data.rate, tenure).then(setEmi).catch(() => {
        const r = data.rate / 1200, f = (1 + r) ** tenure
        setEmi(Math.round((amount * r * f) / (f - 1)))
      }).finally(() => setBusy(false))
    }, 220)
    return () => clearTimeout(t)
  }, [amount, tenure, data.rate])

  const cap = data.affordable_emi + data.existing_emi // total EMI the bank allows (50% of income)
  const fits = emi <= data.affordable_emi && data.reasons.filter((r) => !r.startsWith('EMI')).length === 0
  const changed = amount !== data.requested_amount || tenure !== data.tenure_months
  const ok = changed ? fits : data.eligible
  const used = Math.min(1, (data.existing_emi + emi) / (data.monthly_income || 1))
  const totalInterest = emi * tenure - amount

  return (
    <Shell title={`${data.product} at ${data.rate}% a year`}
      aside={
        <span className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium', ok ? 'bg-credit/15 text-credit' : 'bg-debit/15 text-debit')}>
          {ok ? <CheckCircle2 size={14} aria-hidden /> : <XCircle size={14} aria-hidden />}
          {ok ? (changed ? 'Fits your budget' : 'You are eligible') : (changed ? 'Over your budget' : 'Not eligible yet')}
        </span>
      }>
      <div className="grid gap-5 sm:grid-cols-[1fr_1fr]">
        <div>
          <p className="text-[12px] text-ink-3">Monthly EMI</p>
          <p className={clsx('font-display tabular text-[44px] leading-none tracking-[-0.02em] transition-opacity', busy && 'opacity-60')}>{rupees(emi)}</p>
          <p className="mt-2 text-[13px] text-ink-2">
            {lakh(amount)} over {tenure} months · total interest {rupees(Math.max(0, totalInterest))}
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-[13px]">
            <dt className="text-ink-3">You can borrow up to</dt><dd className="tabular text-right text-ink">{lakh(data.max_amount)}</dd>
            <dt className="text-ink-3">Affordable EMI</dt><dd className="tabular text-right text-ink">{rupees(data.affordable_emi)}</dd>
            <dt className="text-ink-3">Existing EMIs</dt><dd className="tabular text-right text-ink">{rupees(data.existing_emi)}</dd>
            <dt className="text-ink-3">Processing fee</dt><dd className="tabular text-right text-ink">{rupees(data.processing_fee)}</dd>
            <dt className="text-ink-3">Credit score</dt><dd className="tabular text-right text-ink">{data.credit_score}</dd>
          </dl>
        </div>

        <div className="space-y-4">
          <label className="block">
            <span className="flex justify-between text-[13px]"><span className="text-ink-2">Loan amount</span><span className="tabular text-ink">{lakh(amount)}</span></span>
            <input type="range" min={50000} max={amountMax} step={10000} value={amount} onChange={(e) => setAmount(+e.target.value)} aria-label="Loan amount" />
          </label>
          <label className="block">
            <span className="flex justify-between text-[13px]"><span className="text-ink-2">Tenure</span><span className="tabular text-ink">{tenure} months ({+(tenure / 12).toFixed(1)} yr)</span></span>
            <input type="range" min={6} max={maxTenure} step={6} value={tenure} onChange={(e) => setTenure(+e.target.value)} aria-label="Tenure in months" />
          </label>

          <div>
            <div className="flex justify-between text-[12px] text-ink-3">
              <span>Income going to EMIs</span>
              <span className="tabular">{Math.round(used * 100)}% of {rupees(data.monthly_income)}</span>
            </div>
            <div className="relative mt-1.5 h-3 overflow-hidden rounded-full bg-surface-3" role="img"
              aria-label={`Existing EMIs ${rupees(data.existing_emi)}, new EMI ${rupees(emi)}, limit ${rupees(cap)}`}>
              <span className="absolute inset-y-0 left-0 bg-teal" style={{ width: `${(data.existing_emi / data.monthly_income) * 100}%` }} />
              <span className={clsx('absolute inset-y-0 transition-[width] duration-300', ok ? 'bg-mint' : 'bg-debit')}
                style={{ left: `${(data.existing_emi / data.monthly_income) * 100}%`, width: `${Math.min(100, (emi / data.monthly_income) * 100)}%` }} />
              <span className="absolute inset-y-[-2px] w-0.5 bg-ink" style={{ left: '50%' }} title="Bank limit: 50% of income" />
            </div>
            <p className="mt-1 text-[12px] text-ink-3">The line marks the bank's limit of 50% of income.</p>
          </div>
        </div>
      </div>

      {!changed && data.reasons.length > 0 && (
        <ul className="mt-4 space-y-1 rounded-lg bg-debit/10 p-3 text-[13px] text-ink">
          {data.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      )}
      <div className="mt-4 flex flex-wrap gap-2">
        {changed && <ActionButton tone="accent" onClick={() => send(`Can I afford a ${lakh(amount).replace('₹', '')} ${data.loan_type} loan for ${tenure} months?`)}>Check this amount</ActionButton>}
        <ActionButton onClick={() => send(`What documents do I need for a ${data.loan_type} loan?`)}>Documents needed</ActionButton>
        <ActionButton onClick={() => send('Connect me to a loan officer')}>Talk to a loan officer</ActionButton>
      </div>
    </Shell>
  )
}
