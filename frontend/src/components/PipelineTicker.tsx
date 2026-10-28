import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'
import { Check } from 'lucide-react'

const STEPS = ['Detecting language', 'Hiding personal numbers', 'Understanding your question', 'Checking your account', 'Writing the answer']
const AT = [0, 250, 550, 900, 1300]

export default function PipelineTicker() {
  const [i, setI] = useState(0)
  const reduce = useReducedMotion()
  useEffect(() => {
    const ts = AT.map((t, k) => setTimeout(() => setI(k), t))
    return () => ts.forEach(clearTimeout)
  }, [])
  return (
    <div className="flex flex-col gap-1.5 py-1" role="status" aria-live="polite" aria-label={STEPS[i]}>
      {STEPS.map((s, k) => (
        <motion.div key={s} initial={reduce ? false : { opacity: 0, x: -6 }} animate={{ opacity: k <= i ? 1 : 0.35, x: 0 }} transition={{ duration: 0.25 }}
          className="flex items-center gap-2 text-[13px]">
          <span className={clsx('grid h-4 w-4 place-items-center rounded-full', k < i ? 'bg-credit text-white' : k === i ? 'bg-accent' : 'bg-surface-3')}>
            {k < i && <Check size={10} strokeWidth={3} />}
            {k === i && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent-ink" />}
          </span>
          <span className={k === i ? 'text-ink' : 'text-ink-3'}>{s}</span>
        </motion.div>
      ))}
    </div>
  )
}
