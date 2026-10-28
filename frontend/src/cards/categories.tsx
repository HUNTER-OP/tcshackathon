import { ArrowDownLeft, Banknote, Bus, Clapperboard, HeartPulse, Home, Landmark, Plug, ShoppingBag, ShoppingBasket, Utensils, Send, Wallet } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export const CAT_ICON: Record<string, LucideIcon> = {
  salary: ArrowDownLeft, rent: Home, emi: Landmark, utilities: Plug, groceries: ShoppingBasket, food: Utensils,
  shopping: ShoppingBag, travel: Bus, upi_transfer: Send, atm: Banknote, entertainment: Clapperboard, health: HeartPulse,
}
export const catIcon = (c: string): LucideIcon => CAT_ICON[c] ?? Wallet

// one restrained ramp for categories: accent first, then ink steps (no rainbow)
export const CAT_SHADES = ['var(--accent)', 'var(--credit)', 'var(--debit)', 'var(--ink-2)', 'var(--ink-3)', 'var(--surface-3)', 'var(--edge)', 'var(--bahi)']
