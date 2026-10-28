import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import { Mic, Square } from 'lucide-react'

// Web Speech API typing is not in lib.dom for all TS versions
type SR = { lang: string; interimResults: boolean; continuous: boolean; start: () => void; stop: () => void; onresult: ((e: any) => void) | null; onend: (() => void) | null; onerror: ((e: any) => void) | null }
const Ctor: (new () => SR) | undefined = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export default function VoiceButton({ lang, onText, onFinal }: { lang: string; onText: (t: string) => void; onFinal: (t: string) => void }) {
  const [on, setOn] = useState(false)
  const rec = useRef<SR | null>(null)
  useEffect(() => () => rec.current?.stop(), [])
  if (!Ctor) return null

  const start = () => {
    const r = new Ctor()
    r.lang = lang
    r.interimResults = true
    r.continuous = false
    let finalText = ''
    r.onresult = (e: any) => {
      let s = ''
      for (let i = 0; i < e.results.length; i++) {
        s += e.results[i][0].transcript
        if (e.results[i].isFinal) finalText = s
      }
      onText(s)
    }
    r.onend = () => { setOn(false); if (finalText.trim()) onFinal(finalText.trim()) }
    r.onerror = () => setOn(false)
    rec.current = r
    r.start()
    setOn(true)
  }

  return (
    <button type="button" onClick={() => (on ? rec.current?.stop() : start())}
      aria-label={on ? 'Stop listening' : `Speak (${lang})`} aria-pressed={on}
      className={clsx('relative grid h-10 w-10 shrink-0 place-items-center rounded-full transition-colors', on ? 'bg-bahi text-white' : 'text-ink-2 hover:bg-surface-3 hover:text-ink')}>
      {on && <span className="absolute inset-0 animate-ping rounded-full bg-bahi/40" aria-hidden />}
      {on ? <Square size={14} className="relative" /> : <Mic size={18} />}
    </button>
  )
}
