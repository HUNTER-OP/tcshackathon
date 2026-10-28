// UI-development mock (only active with ?demo=1). Not used against the real backend.
import type { ChatResult, Customer, Metrics } from './types'

export const demoCustomers: Customer[] = [
  { id: 'CUST001', name: 'Ravi Kumar', preferred_language: 'en', city: 'Bengaluru', monthly_income: 85000, credit_score: 768, consent: true },
  { id: 'CUST002', name: 'Priya Sharma', preferred_language: 'hi', city: 'Lucknow', monthly_income: 62000, credit_score: 742, consent: true },
  { id: 'CUST003', name: 'Kiran Gowda', preferred_language: 'kn', city: 'Mysuru', monthly_income: 54000, credit_score: 721, consent: true },
  { id: 'CUST004', name: 'Arjun Mehta', preferred_language: 'en', city: 'Pune', monthly_income: 70000, credit_score: 700, consent: false },
  { id: 'CUST005', name: 'Anjali Verma', preferred_language: 'hinglish', city: 'Delhi', monthly_income: 48000, credit_score: 689, consent: true },
]

export const demoMetrics: Metrics = {
  total: 42, resolved: 37, handoffs: 3, avg_latency_ms: 1840, p95_latency_ms: 3920,
  by_intent: { check_balance: 11, loan_eligibility: 7, transaction_history: 6, interest_rates: 5, spending_summary: 5, card_block: 4, human_agent: 3, faq_general: 1 },
  by_language: { en: 18, hi: 9, kn: 7, hinglish: 8 },
  by_model: { gemini: 30, ollama: 9, template: 3 },
  recent: [
    { t: new Date().toISOString(), intent: 'loan_eligibility', language: 'hinglish', latency_ms: 2210, model_used: 'gemini', message: 'kya main 5 lakh ka car loan afford kar sakta hoon' },
    { t: new Date().toISOString(), intent: 'check_balance', language: 'kn', latency_ms: 1410, model_used: 'ollama:qwen2.5', message: 'ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು' },
  ],
}

const base = (o: Partial<ChatResult>): ChatResult => ({
  reply: '', language: 'en', intent: 'faq_general', confidence: 0.9, entities: {}, tool_calls: [], redactions: 0,
  handoff: null, model_used: 'gemini', latency_ms: 1500,
  stages: [
    { name: 'language', ms: 1 }, { name: 'privacy', ms: 1 }, { name: 'intent', ms: 14 }, { name: 'entities', ms: 1 },
    { name: 'tools', ms: 9 }, { name: 'reply', ms: 1420 },
  ],
  cards: [], suggestions: [], ...o,
})

export async function demoChat(msg: string): Promise<ChatResult> {
  await new Promise((r) => setTimeout(r, 1200))
  const m = msg.toLowerCase()
  if (/loan|afford|लोन|ಸಾಲ/.test(m) && /\d/.test(m)) {
    return base({
      reply: 'Yes — a **₹5 lakh car loan** fits your budget. At 9.2% over 60 months the EMI is **₹10,428**, well within your affordable EMI of ₹42,500.',
      intent: 'loan_eligibility', confidence: 0.97, language: /kya|main/.test(m) ? 'hinglish' : 'en',
      entities: { amount_inr: 500000, loan_type: 'car', tenure_months: 60 },
      tool_calls: [{ tool: 'loan_eligibility', args: { loan_type: 'car', amount: 500000 }, ms: 6 }],
      cards: [{ type: 'loan', data: { loan_type: 'car', product: 'Car Loan', requested_amount: 500000, tenure_months: 60, rate: 9.2, emi: 10427.6, eligible: true, max_amount: 2040000, affordable_emi: 42500, existing_emi: 0, monthly_income: 85000, credit_score: 768, foir_after: 0.123, processing_fee: 5000, reasons: [] } }],
      suggestions: ['What about 7 years?', 'Show car loan rates', 'Talk to a loan officer'],
    })
  }
  if (/loan|लोन|ಸಾಲ/.test(m)) {
    return base({ reply: 'Happy to check. How much would you like to borrow?', intent: 'loan_eligibility', confidence: 0.91, entities: { loan_type: 'car' },
      cards: [{ type: 'followup', data: { missing: ['amount_inr'], question: 'How much would you like to borrow?', options: ['₹2 lakh', '₹5 lakh', '₹10 lakh'] } }] })
  }
  if (/transaction|statement|लेनदेन/.test(m)) {
    return base({ reply: 'Here are your last 5 transactions.', intent: 'transaction_history', confidence: 0.95, tool_calls: [{ tool: 'get_transactions', ms: 4 }],
      cards: [{ type: 'transactions', data: { items: [
        { date: '2026-10-27T19:12:00', description: 'Swiggy', category: 'food', amount: -642, balance_after: 148210 },
        { date: '2026-10-26T10:03:00', description: 'BigBasket', category: 'groceries', amount: -2310, balance_after: 148852 },
        { date: '2026-10-25T08:40:00', description: 'Uber', category: 'travel', amount: -318, balance_after: 151162 },
        { date: '2026-10-15T12:00:00', description: 'BESCOM Electricity', category: 'utilities', amount: -1840, balance_after: 151480 },
        { date: '2026-10-01T09:00:00', description: 'Salary credit', category: 'salary', amount: 85000, balance_after: 153320 },
      ] } }], suggestions: ['Spending summary', 'Only food'] })
  }
  if (/spend|kharch|खर्च|ಖರ್ಚು/.test(m)) {
    return base({ reply: 'You spent **₹48,920** in the last 30 days. Rent was the largest share.', intent: 'spending_summary', confidence: 0.93,
      cards: [{ type: 'spending', data: { days: 30, total_debit: 48920, total_credit: 85000, by_category: { rent: 21300, groceries: 8120, food: 6340, shopping: 5600, travel: 3980, utilities: 2280, entertainment: 1300 } } }] })
  }
  if (/rate|byaj|ब्याज|ಬಡ್ಡಿ|fd/.test(m)) {
    return base({ reply: 'Our FD rates go up to **7.25%** for 3–5 years.', intent: 'interest_rates', confidence: 0.96,
      cards: [{ type: 'rates', data: { deposits: { savings: { rate: 3, min_balance: 5000, note: 'Interest credited quarterly' }, fd: [{ tenor: '7-45 days', rate: 3.5 }, { tenor: '1-2 years', rate: 6.8 }, { tenor: '3-5 years', rate: 7.25 }], senior_citizen_bonus: 0.5, rd: { rate: 6.5, min_monthly: 500 } }, loans: { home: { name: 'Home Loan', rate: 8.5, max_tenure_months: 360 }, car: { name: 'Car Loan', rate: 9.2, max_tenure_months: 84 } } } }] })
  }
  if (/block|lost|chori|ब्लॉक|ಬ್ಲಾಕ್/.test(m)) {
    return base({ reply: 'Your debit card ending 4821 is now **blocked**.', intent: 'card_block', confidence: 0.98,
      cards: [{ type: 'card_action', data: { card: 'XXXX4821', type: 'debit', status: 'blocked', reference: 'BLK482910', replacement_eta_days: 7 } }] })
  }
  if (/human|agent|insaan|इंसान/.test(m)) {
    return base({ reply: "I've raised a ticket. An agent will call you within 15 minutes.", intent: 'human_agent', confidence: 0.99,
      handoff: { ticket_id: 'HK-20481', summary: 'Customer wants to speak to an agent about a car loan.', sentiment: 'neutral', priority: 'normal' },
      cards: [{ type: 'handoff', data: { ticket_id: 'HK-20481', summary: 'Customer wants to speak to an agent about a car loan.', sentiment: 'neutral', priority: 'normal' } }] })
  }
  const red = /\d{4}\s?\d{4}\s?\d{4}\s?\d{4}/.test(msg)
  return base({
    reply: 'Your savings balance is **₹1,48,210**.', intent: 'check_balance', confidence: 0.98,
    redactions: red ? 1 : 0, redacted_text: red ? msg.replace(/\d{4}\s?\d{4}\s?\d{4}\s?\d{4}/, '[CARD]') : msg,
    tool_calls: [{ tool: 'get_balance', args: { account_type: 'savings' }, ms: 3 }],
    cards: [{ type: 'balance', data: { account: 'XXXX7731', account_type: 'savings', balance: 148210, currency: 'INR', as_of: new Date().toISOString() } }],
    suggestions: ['Show my last 5 transactions', 'How much did I spend last month?'],
  })
}
