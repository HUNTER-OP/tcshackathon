const inr = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const inr2 = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2, maximumFractionDigits: 2 })
const num = new Intl.NumberFormat('en-IN')

export const rupees = (v: number | null | undefined) => (v == null || isNaN(Number(v)) ? '—' : inr.format(Number(v)))
export const rupeesExact = (v: number | null | undefined) => (v == null || isNaN(Number(v)) ? '—' : inr2.format(Number(v)))
export const n = (v: number) => num.format(v)

export function lakh(v: number): string {
  if (v >= 1e7) return `₹${+(v / 1e7).toFixed(2)} crore`
  if (v >= 1e5) return `₹${+(v / 1e5).toFixed(2)} lakh`
  return rupees(v)
}

export function shortDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

export const humanize = (s: string) => s.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase())

export const LANG_LABEL: Record<string, string> = { en: 'English', hi: 'हिन्दी', kn: 'ಕನ್ನಡ', hinglish: 'Hinglish' }
export const SPEECH_LANG: Record<string, string> = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN', hinglish: 'hi-IN' }

export function modelLabel(m: string): { label: string; local: boolean } {
  const s = (m || '').toLowerCase()
  if (s.includes('ollama') || s.includes('qwen')) return { label: 'Ollama · local', local: true }
  if (s.includes('groq') || s.includes('llama')) return { label: 'Groq', local: false }
  if (s.includes('gemini')) return { label: 'Gemini', local: false }
  if (s.includes('openrouter')) return { label: 'OpenRouter', local: false }
  if (s === 'template' || s === 'none' || !s) return { label: 'Template', local: true }
  return { label: m, local: false }
}
