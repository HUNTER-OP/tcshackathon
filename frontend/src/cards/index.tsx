import type { Card } from '../lib/types'
import BalanceCard from './BalanceCard'
import TransactionsCard from './TransactionsCard'
import SpendingCard from './SpendingCard'
import LoanCard from './LoanCard'
import RatesCard from './RatesCard'
import { CardActionCard, ConsentCard, FaqCard, FollowupCard, HandoffCard, TransferCard } from './ActionCards'

const MAP: Record<string, React.ComponentType<{ data: any }>> = {
  balance: BalanceCard,
  transactions: TransactionsCard,
  spending: SpendingCard,
  loan: LoanCard,
  rates: RatesCard,
  card_action: CardActionCard,
  transfer: TransferCard,
  handoff: HandoffCard,
  consent: ConsentCard,
  followup: FollowupCard,
  faq: FaqCard,
}

export function RenderCard({ card }: { card: Card }) {
  const C = MAP[card.type]
  if (!C || !card.data) return null
  return <C data={card.data} />
}
