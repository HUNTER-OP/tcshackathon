import { Suspense, lazy, useCallback, useEffect, useMemo, useRef, useState } from 'react'
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

export type Convo = { id: string; customerId: string; mode: Mode; lang: Lang; createdAt: number; updatedAt: number; messages: ChatMessage[] }
const CONVO_KEY = 'hk-convos'
const MAX_CONVOS = 40
const loadConvos = (): Convo[] => {
  try { const v = JSON.parse(store.get(CONVO_KEY) || '[]'); return Array.isArray(v) ? v : [] } catch { return [] }
}
const newConvo = (customerId: string, mode: Mode, lang: Lang): Convo =>
  ({ id: uid(), customerId, mode, lang, createdAt: Date.now(), updatedAt: Date.now(), messages: [] })
const viewFromHash = () => (window.location.hash === '#/dashboard' ? 'dashboard' : 'chat') as 'chat' | 'dashboard'

export default function App() {
  const [view, setView] = useState(viewFromHash)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [customerId, setCustomerId] = useState('CUST001')
  const [mode, setMode] = useState<Mode>('hybrid')
  const [lang, setLang] = useState<Lang>('en')
  const [convos, setConvos] = useState<Convo[]>(loadConvos)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const sendLock = useRef(false) // state updates are async; this blocks a second send before `pending` re-renders
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

  // conversations: saved in this browser so old chats (cards, trace, agent tickets) can be reopened
  useEffect(() => { store.set(CONVO_KEY, JSON.stringify(convos.slice(0, MAX_CONVOS))) }, [convos])
  const active = convos.find((c) => c.id === activeId) ?? null
  const messages = useMemo(() => active?.messages ?? [], [active])
  const appendTo = useCallback((id: string, m: ChatMessage) => {
    setConvos((cs) => cs.map((c) => (c.id === id ? { ...c, messages: [...c.messages, m], updatedAt: Date.now() } : c)))
  }, [])
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
    if (pending || sendLock.current) return
    sendLock.current = true
    // the reply always lands in the conversation it was asked in, even if the user switches chats meanwhile
    let convoId = activeId
    if (!convoId || !convos.some((c) => c.id === convoId)) {
      const c = newConvo(customerId, mode, lang)
      convoId = c.id
      setConvos((cs) => [c, ...cs])
      setActiveId(c.id)
    }
    const user: ChatMessage = { id: uid(), role: 'user', content: text }
    const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }))
    appendTo(convoId, user)
    setPending(true)
    try {
      const r = await sendChat({ message: text, customer_id: customerId, mode, history })
      const a: ChatMessage = { id: uid(), role: 'assistant', content: r.reply, result: r }
      appendTo(convoId, a)
      setSelectedId(a.id)
      setOnline(true)
    } catch (e) {
      appendTo(convoId, { id: uid(), role: 'assistant', content: `The assistant server didn't answer (${(e as Error).message.slice(0, 80)}). Check that the backend is running, then send your question again.`, error: true })
      setOnline(false)
    } finally {
      sendLock.current = false
      setPending(false)
    }
  }, [pending, messages, customerId, mode, lang, activeId, convos, appendTo])

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

  // start a fresh chat; an empty current chat is reused instead of piling up blank entries
  const startNew = (cid: string, l: Lang) => {
    const c = newConvo(cid, mode, l)
    setConvos((cs) => [c, ...cs.filter((x) => x.messages.length > 0)])
    setActiveId(c.id); setSelectedId(null); setNavOpen(false); go('chat')
  }
  const pickCustomer = (id: string) => {
    setCustomerId(id)
    const l = customers.find((x) => x.id === id)?.preferred_language ?? lang
    setLang(l)
    startNew(id, l)
  }
  const openConvo = (id: string) => {
    const c = convos.find((x) => x.id === id)
    if (!c) return
    setActiveId(c.id); setCustomerId(c.customerId); setMode(c.mode); setLang(c.lang)
    setSelectedId(null); setNavOpen(false); go('chat')
  }
  const deleteConvo = (id: string) => {
    setConvos((cs) => cs.filter((c) => c.id !== id))
    if (id === activeId) { setActiveId(null); setSelectedId(null) }
  }
  const history = convos.filter((c) => c.messages.length > 0).map((c) => ({
    id: c.id,
    title: c.messages.find((m) => m.role === 'user')?.content ?? 'New conversation',
    customerName: customers.find((x) => x.id === c.customerId)?.name ?? c.customerId,
    updatedAt: c.updatedAt,
    agentCalled: c.messages.some((m) => m.result?.handoff),
    active: c.id === activeId,
  }))

  const sidebar = (
    <Sidebar customers={customers} customerId={customerId} onCustomer={pickCustomer} mode={mode} onMode={setMode} lang={lang} onLang={setLang}
      view={view} onView={go} onNewChat={() => startNew(customerId, lang)} theme={theme} onToggleTheme={toggleTheme}
      conversations={history} onOpenConvo={openConvo} onDeleteConvo={deleteConvo} />
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
