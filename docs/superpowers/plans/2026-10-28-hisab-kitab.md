# Hisab Kitab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A multilingual (English/Hindi/Kannada/Hinglish) banking query assistant that classifies intent with a locally fine-tuned model, fetches data from a mock bank API, and answers via Gemini (Hybrid) or Ollama (Local), with an explainability trace.

**Architecture:** FastAPI backend hosts both the mock Bank API (`/api/*`, SQLite) and the assistant (`/chat`). `/chat` runs a fixed pipeline: language detect → PII firewall → intent classifier → entity extraction → tool router → LLM responder (cloud with local fallback) → trace. React+Vite frontend shows chat, trace panel, mode toggle, voice input, ops dashboard.

**Tech Stack:** Python 3.12, FastAPI, uvicorn, SQLite (stdlib), Faker(en_IN), transformers+torch (CUDA), sentence-transformers, httpx, google-genai, pytest; React 18 + Vite + Tailwind; Ollama `qwen2.5:7b-instruct`.

**Spec:** `docs/superpowers/specs/2026-10-28-hisab-kitab-design.md`

## Global Constraints
- Project root `D:\Hisab_kitab`; backend in `backend/`, frontend in `frontend/`, eval in `eval/`.
- Assistant name in all UI/copy: **Hisab Kitab**; fictional bank, no real bank branding.
- Languages: `en`, `hi` (Devanagari), `kn` (Kannada script), `hinglish` (Hindi in Latin script). Reply in the user's language.
- Every number in a reply (balance, rate, EMI, amounts) comes from tool output; the LLM prompt says so and receives tool JSON only.
- Cloud LLM never receives raw PII: PII firewall runs before any LLM call.
- Response time p95 < 15 s; resolution accuracy ≥ 80% on `eval/queries.jsonl`.
- Secrets read from `.env` (`GEMINI_API_KEY`, optional `OPENROUTER_API_KEY`, `GROQ_API_KEY`); never logged or committed.
- Synthetic data seeded with `seed=42` for reproducibility.
- Account/card numbers displayed masked as `XXXX` + last 4.

## Review Focus
- Gemini key invalid/quota/timeout → must fall back to Ollama within the same request, trace shows `model_used="ollama"` (test in Task 5).
- Customer with `consent_personalization=False` asks for balance → refuse politely, no data fetched (test in Task 6).
- Query with no amount for EMI/eligibility ("can I get a car loan?") → assistant asks a follow-up for amount instead of inventing one (test in Task 6).
- User types a full 16-digit card number or Aadhaar → redacted before LLM, trace shows redaction count (test in Task 4).
- Mixed-script/romanized input ("mera balance kitna hai", "ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು") → correct language + intent (eval set covers; unit test in Task 4/3).

---

## File Structure
```
backend/
  requirements.txt
  app/config.py        settings from .env (keys, model names, paths, timeouts)
  app/db.py            SQLite connection + schema
  app/seed.py          synthetic customers/accounts/transactions/cards (Faker en_IN, seed 42)
  app/products.json    rates, loan products, card fees
  app/bank_api.py      FastAPI APIRouter /api/* (mock bank)
  app/nlu/lang.py      detect_language
  app/nlu/pii.py       redact
  app/nlu/entities.py  extract_entities
  app/nlu/intent.py    IntentClassifier (load + predict)
  app/ml/intents.py    UNIFIED_INTENTS + label maps from Banking77/Bitext
  app/ml/build_dataset.py  merge datasets + multilingual synthetic templates → data/processed/intent_*.jsonl
  app/ml/train_intent.py   fine-tune distilbert-base-multilingual-cased → models/intent/
  app/rag.py           FAQ retrieval over Bitext responses + products
  app/tools.py         intent → tool call (uses bank API functions directly)
  app/llm.py           Gemini / OpenRouter / Ollama clients + fallback
  app/pipeline.py      handle_message (orchestrates, builds trace)
  app/metrics.py       in-memory counters for dashboard
  app/main.py          FastAPI app: /chat, /metrics, /customers, include bank router, CORS
  tests/…
eval/queries.jsonl, eval/run_eval.py
frontend/ (Vite React TS + Tailwind)
README.md, docs/API.md, docs/DEMO_SCRIPT.md
```

## Shared Types (defined in Task 1–4, used everywhere)
- `Entities` (dataclass, `app/nlu/entities.py`): `amount_inr: float|None, tenure_months: int|None, loan_type: str|None ("home"|"car"|"personal"|"education"), account_type: str|None ("savings"|"current"|"fd"), category: str|None, days: int|None, card_last4: str|None`
- `UNIFIED_INTENTS` (17): `check_balance, transaction_history, spending_summary, loan_eligibility, emi_calculation, interest_rates, loan_products, card_block, card_activate, card_issue, transfer_money, fees_charges, atm_branch, password_pin, dispute_refund, human_agent, faq_general`
- `ChatResult` (pydantic, `app/pipeline.py`): `reply: str, language: str, intent: str, confidence: float, entities: dict, tool_calls: list[dict], redactions: int, handoff: dict|None, model_used: str, latency_ms: int`

---

### Task 1: Synthetic data, DB and products

**Files:** Create `backend/requirements.txt`, `backend/app/{__init__,config,db,seed}.py`, `backend/app/products.json`, `backend/tests/test_seed.py`

**Interfaces:**
- Produces: `db.connect(path: str|None=None) -> sqlite3.Connection` (row_factory=Row); `seed.seed(conn, n_customers=50, seed=42) -> None`; tables `customers(id TEXT PK 'CUST001'.., name, phone_masked, email_masked, monthly_income REAL, credit_score INT, consent_personalization INT, preferred_language TEXT)`, `accounts(id TEXT PK, customer_id, type, number_masked, balance REAL, currency 'INR')`, `transactions(id, account_id, date TEXT ISO, description, category, amount REAL signed, balance_after REAL)`, `cards(id, customer_id, last4, type, status 'active'|'blocked'|'inactive')`, `loans(id, customer_id, type, principal, emi, outstanding, rate)`; `config.settings` with `gemini_api_key, openrouter_api_key, groq_api_key, ollama_url='http://localhost:11434', ollama_model='qwen2.5:7b-instruct', gemini_model='gemini-2.5-flash', llm_timeout_s=8, db_path='backend/hisab.db'`.
- products.json keys: `deposits` (savings 3.0%, FD tenors 7d–5y 3.5–7.25%, senior +0.5%), `loans` (home 8.5% max 30y, car 9.2% max 7y, personal 11.5% max 5y, education 9.0% max 15y; each with `min_income`, `max_foir: 0.5`, `processing_fee_pct`), `cards` (annual fees), `faq` (10 short policy Q&As).

- [ ] Step 1: Test `test_seed_creates_50_customers_with_masked_fields` — after `seed(conn)`: 50 customers; every `accounts.number_masked` matches `^XXXX\d{4}$`; ≥1 customer has `consent_personalization=0`; each savings account has ≥60 transactions spanning ~180 days; `CUST001` exists with `preferred_language='en'`, income ≥ 60000, consent 1 (demo persona). Also: seeding twice with seed 42 gives identical balances.
- [ ] Step 2: run `pytest backend/tests/test_seed.py -v` → FAIL.
- [ ] Step 3: implement config/db/seed; transactions categories: salary, rent, groceries, food, travel, utilities, shopping, emi, upi_transfer, atm. Persona `CUST001` "Ravi Kumar" with car-loan-able profile; `CUST002` Hindi, `CUST003` Kannada, `CUST004` no consent.
- [ ] Step 4: pytest → PASS. Step 5: commit `feat: synthetic bank data and products`.

### Task 2: Mock Bank API

**Files:** Create `backend/app/bank_api.py`, `backend/app/main.py` (minimal, includes router), `backend/tests/test_bank_api.py`

**Interfaces:**
- Consumes: `db.connect`, `products.json`.
- Produces: plain functions reused by tools (no HTTP self-calls): `get_accounts(cid)->list[dict]`, `get_balance(cid, account_type="savings")->dict{account, balance, currency, as_of}`, `get_transactions(cid, days=30, category=None, limit=10)->list[dict]`, `spending_summary(cid, days=30)->dict{total_debit, total_credit, by_category:{cat:amt}}`, `loan_eligibility(cid, loan_type, amount, tenure_months|None)->dict{eligible: bool, max_amount, emi, rate, foir_after, reasons:list[str]}`, `emi(principal, annual_rate, tenure_months)->float` (standard amortization, 2 dp), `get_rates(kind=None)->dict`, `block_card(cid, last4|None)->dict`, `transfer(cid, to_masked, amount)->dict{status, ref}` (fails if amount > balance), `ConsentError` raised by personalized functions when consent=0. Router exposes each under `/api/...` per spec; ConsentError → HTTP 403.

- [ ] Step 1: tests: `abs(emi(500000, 9.2, 60) - 10427.6) < 1`; `loan_eligibility("CUST001","car",500000,60)["eligible"] is True` and `emi` equals the emi() value; eligibility for amount 10× income*12 is False with a reason; `get_balance("CUST004")` raises ConsentError and `GET /api/accounts/CUST004/balance` → 403; `transfer` over balance → `status=="failed"`; `GET /api/products/rates` 200 contains `"car"`.
- [ ] Step 2: FAIL → Step 3: implement (eligibility: max EMI = income*max_foir − existing EMIs; max_amount by inverting EMI formula; default tenure = product max) → Step 4: PASS → Step 5: commit `feat: mock bank API`.

### Task 3: Intent dataset + GPU classifier

**Files:** Create `backend/app/ml/{__init__,intents,build_dataset,train_intent}.py`, `backend/app/nlu/{__init__,intent}.py`, `backend/tests/test_intent.py`

**Interfaces:**
- Produces: `UNIFIED_INTENTS`, `BANKING77_MAP: dict[str,str]`, `BITEXT_MAP: dict[str,str]` (every source label mapped; unmapped → `faq_general`); `build_dataset.main()` writes `data/processed/intent_train.jsonl` / `intent_test.jsonl` (`{"text","label"}`), adding ≥40 template examples per intent per language (en/hi/kn/hinglish) for intents weak in sources (check_balance, spending_summary, loan_eligibility, emi_calculation, interest_rates, loan_products, human_agent); `train_intent.main(epochs=3)` fine-tunes `distilbert-base-multilingual-cased` (bf16, batch 64, lr 5e-5) → `models/intent/` + `models/intent/metrics.json` {accuracy, macro_f1}; `IntentClassifier(path="models/intent").predict(text) -> tuple[str, float]` (softmax top-1), singleton `get_classifier()`; if model dir missing, fallback TF-IDF+LogisticRegression trained at load from processed data.

- [ ] Step 1: tests (marked `@pytest.mark.model`, skip if no model): predict on `"what is my account balance"`→check_balance, `"mera balance kitna hai"`→check_balance, `"मेरा खाता बैलेंस बताओ"`→check_balance, `"ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು"`→check_balance, `"can I afford a 5 lakh car loan"`→loan_eligibility, `"block my card"`→card_block, `"talk to a human"`→human_agent; metrics.json accuracy ≥ 0.85. Non-model test: every label in both source CSVs is a key in its map.
- [ ] Step 2: FAIL → Step 3: implement, run `python -m app.ml.build_dataset && python -m app.ml.train_intent` from `backend/` (GPU) → Step 4: PASS → Step 5: commit (models/ gitignored) `feat: multilingual intent classifier`.

### Task 4: Language detect, PII firewall, entities

**Files:** Create `backend/app/nlu/{lang,pii,entities}.py`, `backend/tests/test_nlu.py`

**Interfaces:**
- Produces: `detect_language(text)->str` (Kannada block U+0C80–0CFF → `kn`; Devanagari U+0900–097F → `hi`; Latin with ≥2 Hinglish lexicon hits (`mera, kitna, hai, kya, mujhe, chahiye, paise, batao, karo, nahi, ka, ki, ko`) → `hinglish`; else `en`); `redact(text)->tuple[str,int]` replacing 12–19 digit card numbers `[CARD]`, Aadhaar `\d{4}\s?\d{4}\s?\d{4}` `[AADHAAR]`, PAN `[A-Z]{5}\d{4}[A-Z]` `[PAN]`, Indian phone `[PHONE]`, emails `[EMAIL]`, long account numbers `[ACCOUNT]`; `extract_entities(text)->Entities` handling `₹5,00,000`, `5 lakh`, `5 lac`, `2.5 crore`, `50k`, `5 लाख`, `5 ಲಕ್ಷ`; tenure `5 years`/`60 months`/`5 saal`/`5 साल`; loan types incl. Hindi/Kannada words (गाड़ी/कार, ಕಾರು, घर/home, ಮನೆ); `last N days/week/month`; category words.

- [ ] Step 1: tests: lang for the four example strings above + `"hello"`→en; `redact("my card 4111 1111 1111 1111 and PAN ABCDE1234F")` → no digits run ≥12, count 2; entities: `"can I afford a 5 lakh car loan for 5 years"` → amount 500000, loan_type car, tenure 60; `"₹2,50,000"`→250000; `"mujhe 50k personal loan chahiye"`→50000/personal; `"ಮನೆ ಸಾಲ 30 ಲಕ್ಷ"`→3000000/home; `"last 7 days"`→days 7.
- [ ] Steps 2–5: FAIL → implement → PASS → commit `feat: language detection, PII firewall, entity extraction`.

### Task 5: LLM clients with fallback

**Files:** Create `backend/app/llm.py`, `backend/tests/test_llm.py`

**Interfaces:**
- Produces: `async generate(system: str, user: str, mode: Literal["hybrid","local"]) -> tuple[str, str]` returning `(text, model_used)`; hybrid order: Gemini (`google-genai`, if key starts `AQ.` try `vertexai=True` express mode on 401/404 of AI Studio path) → OpenRouter (if key) → Groq (if key) → Ollama; local: Ollama only (`POST /api/chat`, stream false, `options.temperature=0.2`). Each cloud call wrapped in `asyncio.wait_for(timeout=settings.llm_timeout_s)`. If all fail → returns `("", "none")`. `async translate_to_english(text, mode) -> str` (same chain; one-line output).
- [ ] Step 1: tests with monkeypatched providers: Gemini raising → result model_used `"ollama"`; mode local never calls Gemini; all failing → `("", "none")`. Plus `@pytest.mark.live` smoke: real Ollama returns non-empty for "Say hi".
- [ ] Steps 2–5: FAIL → implement → PASS (+ run live smoke; also run a live Gemini call manually and note result) → commit `feat: LLM clients with cloud→local fallback`.

### Task 6: Tools, RAG and pipeline

**Files:** Create `backend/app/{rag,tools,pipeline,metrics}.py`; modify `backend/app/main.py`; `backend/tests/test_pipeline.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `rag.search(query_en: str, k=3) -> list[dict{q,a,score}]` (sentence-transformers `BAAI/bge-small-en-v1.5` over Bitext deduped per intent (~300 entries) + products FAQ; embeddings cached `models/rag.npy`); `tools.run(intent, entities, customer_id) -> dict{tool, data, needs: list[str]}` — `needs` lists missing required entities (e.g. `["amount_inr"]` for loan_eligibility/emi without amount); `pipeline.handle_message(text, customer_id, mode, history: list[dict]) -> ChatResult`:
  1. `lang=detect_language`; 2. `clean, n=redact(text)`; 3. classify on clean; if lang≠en and confidence<0.6, `translate_to_english` then re-classify and keep the higher; 4. entities from clean (+ translated); 5. if intent==human_agent or confidence<0.45 → handoff `{ticket_id, summary, sentiment}` (summary by LLM, fallback template); 6. tools.run → ConsentError → reply consent message; `needs` non-empty → ask follow-up; 7. LLM system prompt: "You are Hisab Kitab… reply in {language name, script}… use ONLY numbers in TOOL_DATA… ≤120 words, markdown allowed"; user prompt = last 4 history turns + clean message + TOOL_DATA JSON + RAG snippets; 8. if LLM returns "" → deterministic template reply from tool data (English) so demo never blanks; 9. metrics.record(result).
  `main.py`: `POST /chat {message, customer_id="CUST001", mode="hybrid", history=[]}` → ChatResult; `GET /metrics` → `{total, resolved, handoffs, avg_latency_ms, p95_latency_ms, by_intent, by_language, by_model}`; `GET /customers` → id, name, preferred_language (for persona picker); CORS for `http://localhost:5173`.
- [ ] Step 1: tests (LLM monkeypatched to echo TOOL_DATA): balance for CUST001 → intent check_balance, tool_calls[0].tool=="get_balance", reply contains the balance number; CUST004 balance → reply mentions consent, no tool data; `"can I get a car loan"` → reply is a follow-up, `handoff is None`; `"talk to a human"` → handoff has ticket_id; message with card number → `redactions==1` and the LLM stub never saw the digits; LLM returns "" → reply non-empty.
- [ ] Steps 2–5: FAIL → implement → PASS → commit `feat: chat pipeline with tools, RAG, handoff, metrics`.

### Task 7: Evaluation

**Files:** Create `eval/queries.jsonl`, `eval/run_eval.py`

**Interfaces:** `queries.jsonl` rows `{"text","lang","intent","customer_id","expect_contains"?: str}`; ≥200 rows: 50 each en/hi/kn/hinglish covering all 17 intents. `python eval/run_eval.py --mode hybrid|local` calls `pipeline.handle_message` directly, prints & writes `eval/results_{mode}.json`: intent accuracy, resolution rate (intent correct AND (no expect_contains OR it's in reply) AND reply non-empty), p50/p95 latency, per-language accuracy.
- [ ] Step 1: write queries (hand-written + LLM-assisted, reviewed). Step 2: run both modes. Step 3: if resolution < 80% → inspect failures, add training templates/entity patterns, retrain, rerun. Step 4: commit results `feat: eval harness and results`.

### Task 8: Frontend

**Files:** `frontend/` Vite React TS + Tailwind. Components: `ChatPanel`, `MessageBubble` (markdown), `TracePanel`, `ModeToggle` (Hybrid ☁ / Local 🔒), `PersonaPicker` (from `/customers`), `VoiceButton` (Web Speech API, lang `en-IN|hi-IN|kn-IN`), `QuickChips` (example queries per language), `Dashboard` (from `/metrics`, polled 5 s), `HandoffCard`.
**Interfaces:** consumes `POST /chat`, `GET /metrics`, `GET /customers` at `VITE_API=http://localhost:8000`.
- [ ] Step 1: before styling, load `frontend-design` / `taste-skill` skills and pick the visual direction with the team. Step 2: build. Step 3: `npm run build` passes; Playwright smoke (webapp-testing skill): send "what is my balance", reply bubble and trace panel with intent `check_balance` appear; toggle Local and resend → trace `model_used` contains `qwen`/`ollama`. Step 4: commit `feat: Hisab Kitab web UI`.

### Task 9: Docs and demo

**Files:** `README.md` (pitch, architecture diagram, setup: `pip install -r backend/requirements.txt`, `ollama pull qwen2.5:7b-instruct`, train, `uvicorn app.main:app`, `npm run dev`; eval numbers from Task 7), `docs/API.md` (all endpoints with example request/response), `docs/DEMO_SCRIPT.md` (5-min flow: English balance → Hinglish car-loan affordability → Hindi transactions → Kannada rates → card number redaction → human handoff → toggle Local mode, pull network → dashboard).
- [ ] Step 1: write. Step 2: follow README from clean shell to verify. Step 3: commit `docs: setup, API, demo script`.
