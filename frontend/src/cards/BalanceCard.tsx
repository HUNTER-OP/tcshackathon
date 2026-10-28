import { useEffect, useState } from 'react'
import { animate, useReducedMotion } from 'framer-motion'
import { rupeesExact, humanize } from '../lib/format'
import { ActionButton, Shell, useSend } from './Shell'

export default function BalanceCard({ data }: { data: { account: string; account_type: string; balance: number; as_of: string } }) {
  const send = useSend()
  const reduce = useReducedMotion()
  const [v, setV] = useState(reduce ? data.balance : 0)
  useEffect(() => {
    if (reduce) return
    const c = animate(0, data.balance, { duration: 0.9, ease: [0.16, 1, 0.3, 1], onUpdate: setV })
    return () => c.stop()
  }, [data.balance, reduce])
  const asOf = new Date(data.as_of)
  return (
    <Shell title={`${humanize(data.account_type || 'savings')} account ${data.account}`}
      aside={<span className="text-[12px] text-ink-3">as of {isNaN(asOf.getTime()) ? data.as_of : asOf.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</span>}>
      <p className="font-display tabular text-[40px] leading-none tracking-[-0.02em] text-ink sm:text-[48px]" aria-live="polite">
        {rupeesExact(v)}
      </p>
      <p className="mt-2 text-[13px] text-ink-3">Available balance</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <ActionButton onClick={() => send('Show my last 5 transactions')}>Show transactions</ActionButton>
        <ActionButton onClick={() => send('How much did I spend in the last 30 days?')}>Spending summary</ActionButton>
        <ActionButton onClick={() => send('What are the FD interest rates?')}>Grow it in an FD</ActionButton>
      </div>
    </Shell>
  )
}
