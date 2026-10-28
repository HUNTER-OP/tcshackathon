import type { ReactNode } from 'react'
import { createContext, useContext } from 'react'
import clsx from 'clsx'

export const SendContext = createContext<(text: string) => void>(() => {})
export const useSend = () => useContext(SendContext)

export function Shell({ title, aside, children, className }: { title: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('nb-card p-4 sm:p-5', className)}>
      <header className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-[13px] font-semibold text-ink"><span className="hl rounded-sm">{title}</span></h3>
        {aside}
      </header>
      {children}
    </section>
  )
}

export function ActionButton({ children, onClick, tone = 'quiet' }: { children: ReactNode; onClick: () => void; tone?: 'quiet' | 'accent' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'rounded-full border-2 border-line px-3.5 py-1.5 text-[13px] font-semibold transition-all active:translate-x-[1px] active:translate-y-[1px]',
        tone === 'accent' ? 'bg-accent text-accent-ink shadow-[2px_2px_0_var(--line)] hover:brightness-105' : 'bg-white text-ink hover:bg-surface-3',
      )}
    >
      {children}
    </button>
  )
}
