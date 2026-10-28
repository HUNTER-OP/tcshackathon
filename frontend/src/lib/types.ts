export type Lang = 'en' | 'hi' | 'kn' | 'hinglish'
export type Mode = 'hybrid' | 'local'

export interface Card { type: string; data: any }
export interface ToolCall { tool: string; args?: Record<string, unknown>; ms?: number }
export interface Stage { name: string; ms: number; detail?: string }
export interface Handoff { ticket_id: string; summary: string; sentiment: string; priority: string }

export interface ChatResult {
  reply: string
  language: Lang
  intent: string
  confidence: number
  entities: Record<string, string | number>
  tool_calls: ToolCall[]
  redactions: number
  redacted_text?: string
  handoff: Handoff | null
  model_used: string
  latency_ms: number
  stages?: Stage[]
  cards?: Card[]
  suggestions?: string[]
}

export interface Customer {
  id: string
  name: string
  preferred_language: Lang
  city?: string
  monthly_income?: number
  credit_score?: number
  consent?: boolean | number
}

export interface Metrics {
  total: number
  resolved: number
  handoffs: number
  avg_latency_ms: number
  p95_latency_ms: number
  by_intent: Record<string, number>
  by_language: Record<string, number>
  by_model: Record<string, number>
  recent?: { t: string; intent: string; language: string; latency_ms: number; model_used: string; message: string }[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  result?: ChatResult
  error?: boolean
}
