# Hisab Kitab — AI Banking Customer Query Assistant (Design)

Date: 2026-10-28 · TCS Hackathon · Time budget: ~2 hours

Status: approved by team 2026-10-28.

## Intent & why
Bank customers wait in queues for simple answers (balance, transactions, loan eligibility, rates).
Build a conversational assistant that understands natural banking queries in English, Hindi, Kannada and Hinglish, fetches
real data from mock bank APIs, and answers accurately in <15 s, deflecting load from human agents.

Judging weights drive priorities: Relevance 30 · AI/ML/GenAI use 20 · Teamwork 20 · Innovation 15 · Feasibility/scale 15.

## Goals
- ≥80% query-resolution accuracy, measured by an eval script (not claimed).
- p95 response < 15 s (target < 3 s with cloud LLM).
- Handles: balance, transaction history/summary, loan eligibility + EMI, interest rates/products,
  card block/activate, transfers (mock), FAQs, human handoff.
- Two runnable modes: **Hybrid** (local ML + Gemini/OpenRouter) and **Fully Local** (local ML + Ollama), switchable in UI, with auto-fallback cloud → local.
- Deliverables: web UI, dev docs (setup + API), demo video script.

## Non-goals
- Real bank integration, real auth/KYC, real money movement.
- Training an LLM from scratch.

## Anti-goals (fails even if it "works")
- LLM inventing numbers: every balance/rate/EMI must come from the API/JSON, never the model.
- Leaking PII to the cloud LLM.
- A demo that breaks live — must degrade gracefully (fallback model, canned handoff).

## Constraints
- Workstation: RTX PRO 4000 Blackwell 24 GB, Python 3.12, Node v24 + Ollama 0.40 with qwen2.5:7b-instruct pulled. Project dir: D:\Hisab_kitab.
- Data must be synthetic/anonymized; consent flags respected.

## Approaches considered
- **A. Hybrid (chosen):** fine-tuned local intent classifier + rule/LLM entity extraction → tool/API router → LLM writes grounded reply. Pros: real ML to show, measurable, fast, robust. Cons: more parts.
- B. LLM-only function calling: fastest to build, generic, weak on AI/ML criterion and measurability.
- C. Fully local only: strong privacy, but slower to tune and weaker Hinglish. → Kept as the **Local mode** of A rather than a separate build.

User picked A, plus a standalone Ollama mode that can do all tasks offline.

## Architecture
```
Web UI (React+Vite+Tailwind)  ──►  FastAPI /chat
                                     │
   1. PII Firewall: redact card/acct/PAN/Aadhaar/phone typed by user
   2. Language detect (script + Hinglish lexicon); non-English → translated to English for classifier (LLM), reply generated in user language
   2b. Intent classifier (fine-tuned multilingual model on GPU) → intent + confidence
   3. Entity extractor: regex (₹, lakh/crore, dates, tenure, acct type) + LLM fallback
   4. Router → tools: mock Bank API (SQLite) | Product JSON | RAG over FAQ (embeddings)
   5. Low confidence (<0.5) or "human" intent → handoff with auto-summary for agent
   6. Response generator: Gemini/OpenRouter (Hybrid) or Ollama (Local), grounded on tool output only
   7. Trace returned to UI: intent, confidence, entities, API calls, latency, model used
```

## Data
- `raw/banking77_*.csv` (13k queries, 77 intents), `raw/bitext_banking.csv` (25.5k Q&A, 26 intents) — downloaded.
- Unified intent schema (~20 handler intents); mapping table from both datasets' labels → handlers.
- Synthetic (Faker en_IN, seeded): 50 customers with masked IDs, consent flags, accounts, 6 months of transactions, credit score, income.
- `products.json`: savings/FD/RD rates, home/car/personal/education loans (rates, max tenure, FOIR rules), cards & fees.
- Synthetic query generator incl. Hindi, Kannada and Hinglish templates for eval (≈200 labeled queries with expected intent+entities).

## Mock Bank API (FastAPI, also used by the bot)
`GET /api/customers/{id}/accounts` · `GET /api/accounts/{id}/balance` · `GET /api/accounts/{id}/transactions?from&to&category` ·
`GET /api/accounts/{id}/summary` (spend by category) · `POST /api/loans/eligibility` · `GET /api/loans/emi` · `GET /api/products/rates` ·
`POST /api/cards/{id}/block` · `POST /api/transfers` (mock). Responses mask PII (XXXX1234). Personalized endpoints check consent flag.

## Innovation elements (in priority order)
1. **Explainability panel** — "why this answer": intent, confidence, entities, API calls, latency, model.
2. **Affordability advisor** — "can I afford a ₹5L car loan?" → eligibility from income/FOIR, EMI table, plain-language reasoning.
3. **PII firewall + consent gating** — redaction shown in trace; cloud LLM never sees raw identifiers.
4. **Multilingual: English, Hindi (Devanagari), Kannada, Hinglish** — language auto-detected, reply in the same language; voice input via Web Speech API (en-IN, hi-IN, kn-IN).
5. **Smart human handoff** — low confidence → ticket with conversation summary + sentiment.
6. **Ops dashboard** — queries handled, resolution rate, avg latency, intent distribution, cloud vs local share.
7. **Offline mode toggle** — whole flow on Ollama, pitched for privacy/data residency.

## Evaluation
- Classifier: accuracy/F1 on Banking77 test split + held-out Bitext.
- End-to-end: `eval.py` runs the ≈200 labeled queries in both modes → resolution %, p50/p95 latency; numbers go into README and pitch.

## Build order (time-boxed)
| Time | Work |
|---|---|
| 0:00–0:20 | Synthetic data + products.json + SQLite mock API; start classifier training on GPU |
| 0:20–0:50 | Pipeline: firewall, entities, router, tools, LLM responder (Gemini + Ollama), handoff |
| 0:50–1:25 | UI: chat, trace panel, mode toggle, voice, dashboard |
| 1:25–1:40 | Eval script, fix failures, record numbers |
| 1:40–2:00 | README/dev docs, demo script & recording |

## Builder's calls (my defaults, overridable)
- Backend FastAPI + SQLite; frontend React + Vite + Tailwind; classifier: fine-tune `distilbert-base-multilingual-cased` (handles Hindi/Kannada script directly; fallback TF-IDF+LogReg if time runs short).
- Cloud LLM: Gemini 2.x Flash via key; OpenRouter as alternative. Local LLM: `qwen2.5:7b-instruct` on Ollama (multilingual incl. Hindi/Kannada, tool-following, fits 24 GB).
- Embeddings: `gte-large`/`bge-small` via sentence-transformers, in-memory numpy search.
- Assistant name: **Hisab Kitab** (project name), serving a fictional bank — no real bank branding.
- UI visual direction: decided later with frontend skills.
