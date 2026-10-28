import type { ReactNode } from 'react'
import { createContext, useContext } from 'react'
import clsx from 'clsx'

export const SendContext = createContext<(text: string) => void>(() => {})
export const useSend = () => useContext(SendContext)

export function Shell({ title, aside, children, className }: { title: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx('rounded-xl bg-surface-2 p-4 sm:p-5', className)}>
      <header className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-[13px] font-medium text-ink-2">{title}</h3>
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
        'rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors active:scale-[0.98]',
        tone === 'accent' ? 'bg-accent text-accent-ink hover:brightness-110' : 'bg-surface-3 text-ink hover:bg-edge',
      )}
    >
      {children}
    </button>
  )
}
