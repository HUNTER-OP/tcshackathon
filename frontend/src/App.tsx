import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, PanelRight, WifiOff } from 'lucide-react'
import type { ChatMessage, Customer, Lang, Mode } from './lib/types'
import { DEMO, getCustomers, ping, sendChat } from './lib/api'
import Sidebar from './components/Sidebar'
import ChatView from './components/ChatView'
import TracePanel from './components/TracePanel'
const Dashboard = lazy(() => import('./components/Dashboard'))
import { SendContext } from './cards/Shell'

const store = {
  get: (k: string) => { try { return localStorage.getItem(k) } catch { return null } },
  set: (k: string, v: string) => { try { localStorage.setItem(k, v) } catch { /* storage unavailable */ } },
}
const uid = () => Math.random().toString(36).slice(2, 10)
const viewFromHash = () => (window.location.hash === '#/dashboard' ? 'dashboard' : 'chat') as 'chat' | 'dashboard'

export default function App() {
  const [view, setView] = useState(viewFromHash)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [customerId, setCustomerId] = useState('CUST001')
  const [mode, setMode] = useState<Mode>('hybrid')
  const [lang, setLang] = useState<Lang>('en')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [online, setOnline] = useState(true)
  const [navOpen, setNavOpen] = useState(false)
  const [traceOpen, setTraceOpen] = useState(false)

  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = new URLSearchParams(window.location.search).get('theme') || store.get('hk-theme')
    if (saved === 'light' || saved === 'dark') return saved
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => { document.documentElement.dataset.theme = theme; store.set('hk-theme', theme) }, [theme])
  const toggleTheme = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), [])
  useEffect(() => {
    const on = () => setView(viewFromHash())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  useEffect(() => {
    let live = true
    const check = async () => {
      const ok = await ping()
      if (!live) return
      setOnline(ok)
      if (ok && customers.length === 0) getCustomers().then((c) => live && setCustomers(c)).catch(() => {})
    }
    check()
    const t = setInterval(check, 8000)
    return () => { live = false; clearInterval(t) }
  }, [customers.length])

  const customer = customers.find((c) => c.id === customerId)
  const go = (v: 'chat' | 'dashboard') => { window.location.hash = v === 'dashboard' ? '#/dashboard' : '#/'; setView(v); setNavOpen(false) }

  const send = useCallback(async (text: string) => {
    if (pending) return
    const user: ChatMessage = { id: uid(), role: 'user', content: text }
    const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }))
    setMessages((ms) => [...ms, user])
    setPending(true)
    try {
      const r = await sendChat({ message: text, customer_id: customerId, mode, history })
      const a: ChatMessage = { id: uid(), role: 'assistant', content: r.reply, result: r }
      setMessages((ms) => [...ms, a])
      setSelectedId(a.id)
      setOnline(true)
    } catch (e) {
      setMessages((ms) => [...ms, { id: uid(), role: 'assistant', content: `The assistant server didn't answer (${(e as Error).message.slice(0, 80)}). Check that the backend is running on port 8000, then send your question again.`, error: true }])
      setOnline(false)
    } finally {
      setPending(false)
    }
  }, [pending, messages, customerId, mode])

  // demo-only: ?demo=1&script=a|b|c sends prompts one after another (for screenshots / UI checks)
  const script = new URLSearchParams(window.location.search).get('script')
  useEffect(() => {
    if (!script || pending) return
    const steps = script.split('|')
    const sent = messages.filter((m) => m.role === 'user').length
    if (sent < steps.length) send(steps[sent])
  }, [script, pending, messages, send])

  const selected = useMemo(() => {
    const m = messages.find((x) => x.id === selectedId) ?? [...messages].reverse().find((x) => x.result)
    return m?.result ?? null
  }, [messages, selectedId])

  const pickCustomer = (id: string) => {
    setCustomerId(id)
    const c = customers.find((x) => x.id === id)
    if (c) setLang(c.preferred_language)
    setMessages([]); setSelectedId(null); setNavOpen(false)
  }

  const sidebar = (
    <Sidebar customers={customers} customerId={customerId} onCustomer={pickCustomer} mode={mode} onMode={setMode} lang={lang} onLang={setLang}
      view={view} onView={go} onNewChat={() => { setMessages([]); setSelectedId(null); go('chat') }} theme={theme} onToggleTheme={toggleTheme} />
  )

  return (
    <SendContext.Provider value={send}>
      <div className="flex h-full flex-col">
        {(!online || DEMO) && (
          <div className={`flex items-center justify-center gap-2 px-4 py-1.5 text-[13px] ${DEMO ? 'bg-accent text-ink font-medium' : 'bg-debit text-white'}`} role="status">
            {DEMO ? 'Demo mode: canned answers for interface testing.' : <><WifiOff size={14} />Can't reach the Hisab Kitab server at port 8000. Start the backend and this page reconnects on its own.</>}
          </div>
        )}
        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] gap-3 p-2 sm:p-3 lg:grid-cols-[290px_minmax(0,1fr)] xl:grid-cols-[290px_minmax(0,1fr)_360px]">
          <div className="nb hidden min-h-0 overflow-hidden lg:block">{sidebar}</div>

          <main className="nb relative flex min-h-0 min-w-0 flex-col overflow-hidden">
            <div className="spiral" aria-hidden>{Array.from({ length: 12 }, (_, i) => <span key={i} />)}</div>
            <div className="flex items-center justify-between px-3 py-2 lg:hidden">
              <button type="button" onClick={() => setNavOpen(true)} className="rounded-md p-2 text-ink-2 hover:bg-surface" aria-label="Open menu"><Menu size={18} /></button>
              <img src="/logo.jpeg" alt="Hisab Kitab" className="mix-blend-multiply brightness-[1.1] contrast-[1.15] h-7 w-auto" />
              <button type="button" onClick={() => setTraceOpen(true)} className="rounded-md p-2 text-ink-2 hover:bg-surface" aria-label="Open why this answer"><PanelRight size={18} /></button>
            </div>
            <div className="hidden justify-end px-3 pt-2 lg:flex xl:hidden">
              {view === 'chat' && <button type="button" onClick={() => setTraceOpen(true)} className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[13px] text-ink-2 hover:bg-surface"><PanelRight size={15} />Why this answer</button>}
            </div>
            <div className="min-h-0 flex-1">
              {view === 'chat'
                ? <ChatView messages={messages} pending={pending} lang={lang} customerName={customer?.name} selectedId={selectedId}
                    onSelect={(id) => { setSelectedId(id); if (window.innerWidth < 1280) setTraceOpen(true) }} onSend={send} />
                : <Suspense fallback={<p className="p-8 text-ink-3">Loading dashboard…</p>}><Dashboard /></Suspense>}
            </div>
          </main>

          {view === 'chat' && <div className="nb hidden min-h-0 overflow-hidden xl:block"><TracePanel result={selected} /></div>}
        </div>

        <AnimatePresence>
          {navOpen && <Drawer key="nav" side="left" onClose={() => setNavOpen(false)}>{sidebar}</Drawer>}
          {traceOpen && <Drawer key="trace" side="right" onClose={() => setTraceOpen(false)}><TracePanel result={selected} onClose={() => setTraceOpen(false)} /></Drawer>}
        </AnimatePresence>
      </div>
    </SendContext.Provider>
  )
}

function Drawer({ side, onClose, children }: { side: 'left' | 'right'; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', k)
    return () => window.removeEventListener('keydown', k)
  }, [onClose])
  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true">
      <motion.button type="button" aria-label="Close" onClick={onClose} className="absolute inset-0 bg-black/50"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
      <motion.div className={`absolute inset-y-0 ${side === 'left' ? 'left-0' : 'right-0'} w-[min(360px,88vw)] shadow-2xl`}
        initial={{ x: side === 'left' ? '-100%' : '100%' }} animate={{ x: 0 }} exit={{ x: side === 'left' ? '-100%' : '100%' }}
        transition={{ type: 'spring', stiffness: 380, damping: 36 }}>
        {children}
      </motion.div>
    </div>
  )
}
