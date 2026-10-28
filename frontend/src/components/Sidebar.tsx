import clsx from 'clsx'
import { BarChart3, Cloud, ExternalLink, HardDrive, Headset, Lock, MessageSquarePlus, MessagesSquare, Moon, Sun } from 'lucide-react'
import type { Customer, Lang, Mode } from '../lib/types'
import { LANG_LABEL } from '../lib/format'
import { API } from '../lib/api'

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
  theme: 'light' | 'dark'
  onToggleTheme: () => void
}

const LANGS: Lang[] = ['en', 'hi', 'kn', 'hinglish']

export default function Sidebar(p: Props) {
  return (
    <nav className="flex h-full flex-col gap-5 overflow-y-auto bg-surface p-4 scroll-quiet" aria-label="Main">
      <div className="px-1">
        <div className="logo-tile rounded-2xl border border-line px-3 py-2.5">
          <img src="/logo.jpeg" alt="Hisab Kitab" className="mix-blend-multiply brightness-[1.1] contrast-[1.15] h-11 w-auto" />
        </div>
        <p className="mt-2.5 text-[13px] font-semibold text-ink-2">Every Rupee, Explained.</p>
      </div>

      <div className="flex flex-col gap-1">
        <NavBtn on={p.view === 'chat'} onClick={() => p.onView('chat')} icon={<MessagesSquare size={16} />}>Assistant</NavBtn>
        <NavBtn on={p.view === 'dashboard'} onClick={() => p.onView('dashboard')} icon={<BarChart3 size={16} />}>Operations dashboard</NavBtn>
        <a href={`${API}/agent/`} target="_blank" rel="noreferrer"
          className="flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[14px] font-medium text-ink-2 transition-colors hover:bg-surface-2 hover:text-ink">
          <Headset size={16} />Agent console<ExternalLink size={13} className="ml-auto text-ink-3" aria-label="opens in a new tab" />
        </a>
        <NavBtn on={false} onClick={p.onNewChat} icon={<MessageSquarePlus size={16} />}>New conversation</NavBtn>
      </div>

      <section aria-labelledby="persona-h">
        <h2 id="persona-h" className="mb-2 px-1 text-[12px] font-semibold text-ink-3">Signed in as</h2>
        <ul className="flex flex-col gap-1">
          {p.customers.length === 0 && <li className="px-2 text-[13px] text-ink-3">Customers load when the server is running.</li>}
          {p.customers.slice(0, 6).map((c) => {
            const consent = c.consent === undefined ? true : Boolean(c.consent)
            const on = p.customerId === c.id
            return (
              <li key={c.id}>
                <button type="button" onClick={() => p.onCustomer(c.id)} aria-pressed={on}
                  className={clsx('flex w-full items-center gap-3 rounded-xl border px-2 py-1.5 text-left transition-colors', on ? 'border-ground bg-surface-3' : 'border-transparent hover:bg-surface-2')}>
                  <span className={clsx('grid h-8 w-8 shrink-0 place-items-center rounded-full border border-line text-[12px] font-bold', on ? 'bg-surface text-ink' : 'bg-surface-3 text-ink')}>
                    {c.name.split(' ').map((s) => s[0]).join('').slice(0, 2)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] font-semibold text-ink">{c.name}</span>
                    <span className={clsx('block truncate text-[12px]', on ? 'text-ink-2' : 'text-ink-3')}>{LANG_LABEL[c.preferred_language] ?? c.preferred_language}{c.city ? ` · ${c.city}` : ''}</span>
                  </span>
                  {!consent && <Lock size={14} className="shrink-0 text-debit" aria-label="No data consent" />}
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      <section aria-labelledby="lang-h">
        <h2 id="lang-h" className="mb-2 px-1 text-[12px] font-semibold text-ink-3">Language for voice and suggestions</h2>
        <div className="grid grid-cols-2 gap-1.5">
          {LANGS.map((l) => (
            <button key={l} type="button" aria-pressed={p.lang === l} onClick={() => p.onLang(l)}
              className={clsx('rounded-xl border px-2 py-1.5 text-[14px] font-medium transition-colors', p.lang === l ? 'border-line bg-ground text-white' : 'border-edge bg-surface-2 text-ink-2 hover:border-line hover:text-ink')}>
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="mode-h">
        <h2 id="mode-h" className="mb-2 px-1 text-[12px] font-semibold text-ink-3">Where the AI runs</h2>
        <div className="flex flex-col gap-1.5">
          <ModeBtn on={p.mode === 'hybrid'} onClick={() => p.onMode('hybrid')} icon={<Cloud size={16} />} title="Hybrid" sub="Our model + Gemini, Groq as backup" />
          <ModeBtn on={p.mode === 'local'} onClick={() => p.onMode('local')} icon={<HardDrive size={16} />} title="Local only" sub="Everything on this machine, works offline" />
        </div>
      </section>

      <div className="mt-auto flex items-center justify-between gap-2 px-1 pt-2">
        <p className="text-[12px] text-ink-3">Fictional bank · synthetic data</p>
        <button type="button" onClick={p.onToggleTheme} aria-pressed={p.theme === 'dark'}
          aria-label={p.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} title={p.theme === 'dark' ? 'Light mode' : 'Dark mode'}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-line bg-surface-2 text-ink transition-colors hover:bg-accent hover:text-accent-ink">
          {p.theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </nav>
  )
}

function NavBtn({ on, onClick, icon, children }: { on: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-current={on ? 'page' : undefined}
      className={clsx('flex items-center gap-2.5 rounded-xl px-2.5 py-2 text-[14px] font-medium transition-colors', on ? 'bg-ground text-white' : 'text-ink-2 hover:bg-surface-2 hover:text-ink')}>
      {icon}{children}
    </button>
  )
}

function ModeBtn({ on, onClick, icon, title, sub }: { on: boolean; onClick: () => void; icon: React.ReactNode; title: string; sub: string }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={on}
      className={clsx('flex items-start gap-2.5 rounded-xl border px-2.5 py-2 text-left transition-colors', on ? 'border-ground bg-surface-3 text-ink' : 'border-edge bg-surface-2 text-ink-2 hover:border-line hover:text-ink')}>
      <span className="mt-0.5">{icon}</span>
      <span>
        <span className="block text-[14px] font-semibold">{title}</span>
        <span className={clsx('block text-[12px]', on ? 'text-ink-2' : 'text-ink-3')}>{sub}</span>
      </span>
    </button>
  )
}
