# Hisab Kitab — API Reference

Base URL: `http://localhost:8000`. All bodies are JSON. Interactive docs: `http://localhost:8000/docs` (FastAPI Swagger).

The example values below are illustrative. Real values come from the seeded synthetic database.

---

## Assistant

### `POST /chat`

Runs one message through the full pipeline: language detection, PII firewall, intent, entities, tools, response generation and trace.

**Request**

```json
{
  "message": "kya main 5 lakh ka car loan afford kar sakta hoon?",
  "customer_id": "CUST001",
  "mode": "hybrid",
  "history": [
    {"role": "user", "content": "mera balance kitna hai"},
    {"role": "assistant", "content": "Aapka savings balance ₹1,24,350 hai."}
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `message` | string | Raw user text (any of en / hi / kn / Hinglish) |
| `customer_id` | string | Default `CUST001` |
| `mode` | `"hybrid"` \| `"local"` | `hybrid` = cloud LLM with local fallback; `local` = Ollama only |
| `history` | list of `{role, content}` | Previous turns; the last few are used for context |

**Response**

```json
{
  "reply": "Haan Ravi ji, aap ₹5,00,000 ka car loan le sakte hain. 84 mahine ke liye EMI ₹8,0xx hogi ...",
  "language": "hinglish",
  "intent": "loan_eligibility",
  "confidence": 0.97,
  "entities": {"amount_inr": 500000, "loan_type": "car"},
  "tool_calls": [
    {"tool": "loan_eligibility", "args": {"loan_type": "car", "amount": 500000, "tenure_months": null}, "ms": 3}
  ],
  "redactions": 0,
  "redacted_text": "kya main 5 lakh ka car loan afford kar sakta hoon?",
  "handoff": null,
  "model_used": "gemini",
  "latency_ms": 1840,
  "stages": [
    {"name": "language", "ms": 0, "detail": "hinglish"},
    {"name": "pii", "ms": 0, "detail": "0 redacted"},
    {"name": "intent", "ms": 12, "detail": "loan_eligibility 0.97"},
    {"name": "entities", "ms": 0, "detail": "amount_inr=500000, loan_type=car"},
    {"name": "tools", "ms": 3, "detail": "loan_eligibility"},
    {"name": "llm", "ms": 1810, "detail": "gemini"}
  ],
  "cards": [
    {"type": "loan", "data": {"loan_type": "car", "eligible": true, "requested_amount": 500000, "emi": 8063.0,
                              "rate": 9.2, "tenure_months": 84, "max_amount": 2010000, "affordable_emi": 42500.0,
                              "foir_after": 0.095, "processing_fee": 5000.0, "reasons": []}}
  ],
  "suggestions": ["What would the EMI be for 5 years?", "Show home loan rates"]
}
```

| Field | Meaning |
|---|---|
| `reply` | Markdown text in the user's language |
| `language` | `en`, `hi`, `kn`, `hinglish` |
| `intent`, `confidence` | Top intent from the classifier and its softmax probability |
| `entities` | Extracted slots: `amount_inr`, `tenure_months`, `loan_type`, `account_type`, `category`, `days`, `card_last4` |
| `tool_calls` | Bank or product functions called, with arguments and duration |
| `redactions`, `redacted_text` | Count of masked identifiers, and the text actually sent onwards |
| `handoff` | `null`, or `{ticket_id, summary, sentiment}` when escalated to a human |
| `model_used` | Which LLM wrote the reply (`gemini`, `groq`, `openrouter`, `ollama`, or `template` if all failed) |
| `latency_ms`, `stages` | End-to-end time and per-stage breakdown (feeds the "why this answer" trace) |
| `cards` | Structured UI cards; types include `balance`, `transactions`, `spending`, `loan`, `emi`, `rates`, `card_action`, `transfer`, `handoff`, `consent`, `followup` |
| `suggestions` | Follow-up chips for the UI |

**Special cases**
- Customer without consent: `reply` explains that consent is required, `cards` contains `{"type":"consent"}`, and no account data is returned.
- Missing required detail (for example a loan amount): `reply` asks a follow-up question and `cards` contains `{"type":"followup","data":{"needs":["amount_inr"]}}`.
- Low confidence or a request for a human: `handoff` is filled in.

### `GET /customers`

Persona list for the customer picker.

```json
[
  {"id": "CUST001", "name": "Ravi Kumar", "preferred_language": "en"},
  {"id": "CUST002", "name": "Priya Sharma", "preferred_language": "hi"}
]
```

### `GET /metrics`

In-memory counters for the ops dashboard (reset on restart).

```json
{
  "total": 42, "resolved": 38, "handoffs": 3,
  "avg_latency_ms": 1620, "p95_latency_ms": 3400,
  "by_intent": {"check_balance": 12, "loan_eligibility": 7},
  "by_language": {"en": 15, "hinglish": 12, "hi": 9, "kn": 6},
  "by_model": {"gemini": 35, "ollama": 7}
}
```

### `GET /health`

```json
{"status": "ok"}
```

---

## Mock core-banking API (`/api`)

These endpoints simulate a bank's backend. The assistant calls the same Python functions directly, while the HTTP routes are there for developers and demos. Personalised endpoints return **403** when the customer has not consented, and **404** for unknown customers.

### `GET /api/customers/{cid}/accounts`

```json
[
  {"id": "AC001S", "type": "savings", "number_masked": "XXXX4821", "balance": 124350.5, "currency": "INR"},
  {"id": "AC001F", "type": "fd", "number_masked": "XXXX0937", "balance": 350000.0, "currency": "INR"}
]
```

### `GET /api/accounts/{cid}/balance?account_type=savings`

`account_type`: `savings` (default), `fd` or `current`. Falls back to savings when the type isn't held.

```json
{"account": "XXXX4821", "account_type": "savings", "balance": 124350.5, "currency": "INR", "as_of": "2026-10-28T14:05"}
```

### `GET /api/accounts/{cid}/transactions?days=30&category=food&limit=10`

```json
[
  {"date": "2026-10-27T19:42:00", "description": "Swiggy", "category": "food", "amount": -486.0, "balance_after": 124350.5},
  {"date": "2026-10-25T13:10:00", "description": "Zomato", "category": "food", "amount": -712.0, "balance_after": 124836.5}
]
```

Categories: `salary, rent, emi, utilities, groceries, food, shopping, travel, upi_transfer, atm, entertainment, health`.

### `GET /api/accounts/{cid}/summary?days=30`

```json
{"days": 30, "total_debit": 61240.0, "total_credit": 85000.0,
 "by_category": {"rent": 21300.0, "shopping": 11870.0, "groceries": 8420.0, "food": 5110.0}}
```

### `POST /api/loans/eligibility`

```json
{"customer_id": "CUST001", "loan_type": "car", "amount": 500000, "tenure_months": 60}
```

```json
{"loan_type": "car", "product": "Car Loan", "requested_amount": 500000.0, "tenure_months": 60, "rate": 9.2,
 "emi": 10427.6, "eligible": true, "max_amount": 2048000, "affordable_emi": 42500.0, "existing_emi": 0.0,
 "monthly_income": 85000.0, "credit_score": 768, "foir_after": 0.123, "processing_fee": 5000.0, "reasons": []}
```

The rules are: income must meet the product minimum, the credit score must be at least 650, and the new EMI must stay within 50% of income minus existing EMIs (FOIR). Tenure defaults to the product maximum.

### `GET /api/loans/emi?principal=500000&rate=9.2&tenure_months=60`

```json
{"emi": 10427.6}
```

### `GET /api/products/rates?kind=fd`

`kind`: `fd`, `savings`, `rd` (deposits) or `home`, `car`, `personal`, `education` (loans). Leave it out to get everything.

```json
{"deposits": {"savings": {"rate": 3.0, "min_balance": 5000},
              "fd": [{"tenor": "1-2 years", "rate": 6.8}, {"tenor": "3-5 years", "rate": 7.25}],
              "senior_citizen_bonus": 0.5, "rd": {"rate": 6.5, "min_monthly": 500}}}
```

### `POST /api/cards/{cid}/block?last4=1234`

Blocks the card ending in `last4`, or the customer's first card if `last4` is omitted.

```json
{"card": "XXXX1234", "type": "debit", "status": "blocked", "reference": "BLK482913", "replacement_eta_days": 7}
```

### `POST /api/transfers`

```json
{"customer_id": "CUST001", "to": "XXXX9999", "amount": 5000}
```

```json
{"status": "success", "ref": "UTR4829137465", "amount": 5000, "to": "XXXX9999", "balance_after": 119350.5}
```

When the amount is more than the balance (or not positive), the response is `{"status": "failed", "reason": "insufficient balance", "balance": ...}`.

---

## Configuration (`.env`)

| Key | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Primary cloud LLM |
| `GEMINI_MODEL` | see `backend/app/config.py` | Gemini model id |
| `GROQ_API_KEY`, `GROQ_MODEL` | — | Cloud fallback |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | — | Cloud fallback |
| `OLLAMA_URL` | `http://localhost:11434` | Local LLM server |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Local model |
| `LLM_TIMEOUT_S` / `LOCAL_TIMEOUT_S` | `8` / `12` | Per-call timeouts before falling back |
