import type { ChatResult, Customer, Metrics, Mode } from './types'
import { demoChat, demoCustomers, demoMetrics } from './demo'

export const API = (import.meta.env.VITE_API as string | undefined) ?? ''  // same origin; Vite proxies to the backend
export const DEMO = new URLSearchParams(window.location.search).get('demo') === '1'

async function j<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } })
  if (!r.ok) throw new Error(`${r.status} ${await r.text().catch(() => r.statusText)}`)
  return r.json() as Promise<T>
}

export function sendChat(body: { message: string; customer_id: string; mode: Mode; history: { role: string; content: string }[] }): Promise<ChatResult> {
  if (DEMO) return demoChat(body.message)
  return j<ChatResult>('/chat', { method: 'POST', body: JSON.stringify(body) })
}

export function getCustomers(): Promise<Customer[]> {
  if (DEMO) return Promise.resolve(demoCustomers)
  return j<Customer[]>('/customers')
}

export function getMetrics(): Promise<Metrics> {
  if (DEMO) return Promise.resolve(demoMetrics)
  return j<Metrics>('/metrics')
}

export async function getEmi(principal: number, rate: number, tenure: number): Promise<number> {
  if (DEMO) {
    const r = rate / 1200
    const f = (1 + r) ** tenure
    return Math.round((principal * r * f) / (f - 1) * 100) / 100
  }
  const d = await j<{ emi: number }>(`/api/loans/emi?principal=${principal}&rate=${rate}&tenure_months=${tenure}`)
  return d.emi
}

export async function ping(): Promise<boolean> {
  if (DEMO) return true
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(2500) })
    return r.ok
  } catch {
    return false
  }
}
