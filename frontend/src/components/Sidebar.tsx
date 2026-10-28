import clsx from 'clsx'
import { BarChart3, Cloud, HardDrive, Lock, MessageSquarePlus, MessagesSquare, Moon, Sun } from 'lucide-react'
import type { Customer, Lang, Mode } from '../lib/types'
import { LANG_LABEL } from '../lib/format'

type Props = {
  customers: Customer[]
  customerId: string
  onCustomer: (id: string) => void
  mode: Mode
  onMode: (m: Mode) => void
  lang: Lang
  onLang: (l: Lang) => void
  view: 'chat' | 'dashboard'
  onView: (v: 'chat' | 'dashboard') => void
  onNewChat: () => void
  theme: 'dark' | 'light'
  onTheme: () => void
}

const LANGS: Lang[] = ['en', 'hi', 'kn', 'hinglish']

export default function Sidebar(p: Props) {
  return (
    <nav className="flex h-full flex-col gap-6 overflow-y-auto bg-surface p-4 scroll-quiet" aria-label="Main">
      <div className="flex items-center gap-2.5 px-1">
        <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
          <rect width="32" height="32" rx="6" fill="var(--bahi)" />
          <rect x="7" y="7" width="18" height="18" rx="2" fill="none" stroke="#e3a72f" strokeWidth="2" />
          <path d="M11 13h10M11 17h10M11 21h6" stroke="#e3a72f" strokeWidth="2" />
        </svg>
        <div className="leading-tight">
          <p className="font-display text-[19px] font-semibold tracking-[-0.01em]">Hisab Kitab</p>
          <p className="text-[12px] text-ink-3">Your bank, in your language</p>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <NavBtn on={p.view === 'chat'} onClick={() => p.onView('chat')} icon={<MessagesSquare size={16} />}>Assistant</NavBtn>
        <NavBtn on={p.view === 'dashboard'} onClick={() => p.onView('dashboard')} icon={<BarChart3 size={16} />}>Operations dashboard</NavBtn>
        <NavBtn on={false} onClick={p.onNewChat} icon={<MessageSquarePlus size={16} />}>New conversation</NavBtn>
      </div>

      <section aria-labelledby="persona-h">
        <h2 id="persona-h" className="mb-2 px-1 text-[12px] text-ink-3">Signed in as</h2>
        <ul className="flex flex-col gap-1">
          {p.customers.length === 0 && <li className="px-2 text-[13px] text-ink-3">Customers load when the server is running.</li>}
          {p.customers.slice(0, 6).map((c) => {
            const consent = c.consent === undefined ? true : Boolean(c.consent)
            return (
              <li key={c.id}>
                <button type="button" onClick={() => p.onCustomer(c.id)} aria-pressed={p.customerId === c.id}
                  className={clsx('flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition-colors', p.customerId === c.id ? 'bg-surface-3' : 'hover:bg-surface-2')}>
                  <span className={clsx('grid h-8 w-8 shrink-0 place-items-center rounded-full text-[12px] font-semibold', p.customerId === c.id ? 'bg-accent text-accent-ink' : 'bg-surface-3 text-ink-2')}>
                    {c.name.split(' ').map((s) => s[0]).join('').slice(0, 2)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] text-ink">{c.name}</span>
                    <span className="block truncate text-[12px] text-ink-3">{LANG_LABEL[c.preferred_language] ?? c.preferred_language}{c.city ? ` · ${c.city}` : ''}</span>
                  </span>
                  {!consent && <Lock size={14} className="shrink-0 text-warn" aria-label="No data consent" />}
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      <section aria-labelledby="lang-h">
        <h2 id="lang-h" className="mb-2 px-1 text-[12px] text-ink-3">Language for voice and suggestions</h2>
        <div className="grid grid-cols-2 gap-1.5">
          {LANGS.map((l) => (
            <button key={l} type="button" aria-pressed={p.lang === l} onClick={() => p.onLang(l)}
              className={clsx('rounded-lg px-2 py-2 text-[14px] transition-colors', p.lang === l ? 'bg-ink text-ground' : 'bg-surface-2 text-ink-2 hover:text-ink')}>
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="mode-h">
        <h2 id="mode-h" className="mb-2 px-1 text-[12px] text-ink-3">Where the AI runs</h2>
        <div className="flex flex-col gap-1.5">
          <ModeBtn on={p.mode === 'hybrid'} onClick={() => p.onMode('hybrid')} icon={<Cloud size={16} />} title="Hybrid" sub="Our model + Gemini, Groq as backup" />
          <ModeBtn on={p.mode === 'local'} onClick={() => p.onMode('local')} icon={<HardDrive size={16} />} title="Local only" sub="Everything on this machine, works offline" />
        </div>
      </section>

      <div className="mt-auto flex items-center justify-between px-1 pt-2">
        <span className="text-[12px] text-ink-3">Fictional bank, synthetic data</span>
        <button type="button" onClick={p.onTheme} className="rounded-md p-2 text-ink-2 hover:bg-surface-2 hover:text-ink" aria-label={`Switch to ${p.theme === 'dark' ? 'light' : 'dark'} theme`}>
          {p.theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </nav>
  )
}

function NavBtn({ on, onClick, icon, children }: { on: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-current={on ? 'page' : undefined}
      className={clsx('flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[14px] transition-colors', on ? 'bg-surface-3 text-ink' : 'text-ink-2 hover:bg-surface-2 hover:text-ink')}>
      {icon}{children}
    </button>
  )
}

function ModeBtn({ on, onClick, icon, title, sub }: { on: boolean; onClick: () => void; icon: React.ReactNode; title: string; sub: string }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={clsx('flex items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors', on ? 'bg-accent text-accent-ink' : 'bg-surface-2 text-ink-2 hover:text-ink')}>
      <span className="mt-0.5">{icon}</span>
      <span>
        <span className="block text-[14px] font-medium">{title}</span>
        <span className={clsx('block text-[12px]', on ? 'opacity-80' : 'text-ink-3')}>{sub}</span>
      </span>
    </button>
  )
}
