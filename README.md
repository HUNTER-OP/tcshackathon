# Hisab Kitab

**Ask your bank anything, in your own language.** Hisab Kitab is an AI banking assistant that answers customer questions in **English, Hindi, Kannada and Hinglish**. It gets real figures from the bank's systems, so it never makes up a number. It also shows *why* it answered the way it did.

Built for the TCS hackathon problem *"AI-Powered Banking Customer Query Assistant"*.

---

## Why

Customers wait in call-centre queues for simple answers: balance, recent transactions, loan eligibility, interest rates. Scripted FAQ bots can't handle varied phrasing, mixed languages or personal context. Hisab Kitab handles these queries in seconds and hands the rest to a human with a ready-made summary.

**Targets from the brief:** at least 80% of queries resolved, and responses in under 15 seconds.

## Results

**Measured results** (200 held-out questions, 50 per language, `python eval/run_eval.py --mode hybrid`, 2026-10-28):

| Metric | Result | Target |
|---|---|---|
| Query resolution | **89.0%** | ≥ 80% |
| Intent accuracy | 89.0% (en 88, hi 90, hinglish 92, kn 86) | — |
| Language detection | 99.5% | — |
| Latency p50 / p95 / max | 1.3 s / 6.0 s / 12.2 s | p95 < 15 s |
| Intent model (internal split) | 96.4% accuracy, trained in 36 s on RTX PRO 4000 | — |

**Fully offline mode** (`--mode local`, everything on the local GPU with Ollama `qwen2.5:7b-instruct`): resolution **88.5%**, latency p50 2.3 s / p95 8.2 s / max 13.4 s, no internet required.
_Run `eval/run_eval.py` (below) and paste the summary table here._

| Metric | Hybrid (cloud) | Local (offline) |
|---|---|---|
| Resolution rate | <!-- hybrid_resolution --> | <!-- local_resolution --> |
| Intent accuracy | <!-- hybrid_intent --> | <!-- local_intent --> |
| p95 latency | <!-- hybrid_p95 --> | <!-- local_p95 --> |

Intent classifier (held-out split from training data): see `models/intent/metrics.json`.

## Features

1. **"Why this answer" trace.** Every reply shows the detected language, the intent and its confidence, the extracted details, the bank APIs called, the model used, and the time spent at each stage.
2. **Loan affordability advisor.** For example: "Can I afford a ₹5 lakh car loan?" The assistant checks income and existing EMIs (using a 50% FOIR limit), then works out eligibility, the maximum amount, the EMI and the processing fee, and explains its reasoning.
3. **Privacy filter and consent check.** Card, Aadhaar, PAN, account, phone, email and OTP/CVV numbers are hidden *before* any cloud model sees the text. Customers who haven't given consent get a polite refusal, and no personal data is fetched.
4. **Four languages and voice.** The language is detected from the script and a Hinglish word list, and the reply comes back in the same language. Voice input uses the browser's Web Speech API (en-IN, hi-IN, kn-IN).
5. **Human handoff.** If the assistant is unsure, or the user asks for a person, it creates a ticket with a conversation summary and the customer's sentiment.
6. **Interactive answer cards.** Answers come with balance, transaction, spending-chart, loan/EMI, rates and handoff cards. A trace sidebar sits alongside the chat.
7. **Ops dashboard.** Shows queries handled, resolution rate, latency percentiles, the intent and language mix, and the cloud vs local split.
8. **Offline mode.** One toggle runs the whole flow on the local GPU with Ollama, with no internet connection needed.

## Architecture

```
 Customer (web UI: text or voice)
        |
        v
 [1] Language detect ------- en / hi / kn / hinglish  (script + Hinglish lexicon)
        |
        v
 [2] PII firewall ---------- masks card, Aadhaar, PAN, account, phone, email, OTP
        |
        v
 [3] Intent model ---------- fine-tuned multilingual DistilBERT on local GPU
        |                    (low confidence + non-English -> translate, re-classify)
        v
 [4] Entity extraction ----- "5 lakh" -> 500000, "5 saal" -> 60 months, loan type, period
        |
        +--> low confidence or "talk to a human" --> [Handoff ticket + summary]
        |
        v
 [5] Tools ----------------- mock core-banking API (SQLite) | products.json | FAQ retrieval
        |                    no consent -> refusal   missing detail -> follow-up question
        v
 [6] Response generator ---- Hybrid: Gemini -> Groq / OpenRouter -> Ollama (auto-fallback)
        |                    Local:  Ollama (qwen2.5:7b-instruct) only
        |                    grounded ONLY on tool output; template reply if all models fail
        v
 [7] Reply + trace + cards -> UI
```

**Rules that always hold:**
- Every number in a reply comes from tool output. The model only writes the wording.
- The privacy filter runs before any language model call.
- If every model fails, a reply built from a template is returned instead, so the chat never goes blank.

## Tech stack

| Part | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLite |
| Intent model | `distilbert-base-multilingual-cased`, fine-tuned locally (CUDA). Falls back to TF-IDF + logistic regression if no GPU model is present |
| Cloud LLM | Gemini Flash (Google AI Studio); backups Groq and OpenRouter |
| Local LLM | Ollama, `qwen2.5:7b-instruct` |
| Retrieval | `BAAI/bge-small-en-v1.5` embeddings over FAQ and product data |
| Frontend | React + Vite + TypeScript + Tailwind, Recharts, Framer Motion |
| Tests | pytest; Playwright smoke test for the UI |

## Setup (Windows)

Prerequisites: Python 3.12, Node 20+, [Ollama](https://ollama.com), and an NVIDIA GPU (optional, but it makes training fast).

```powershell
cd D:\Hisab_kitab
python -m venv .venv
.venv\Scripts\activate

# PyTorch with CUDA 12.8 (needed for RTX 50-series / Blackwell GPUs); use the CPU wheel otherwise
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r backend\requirements.txt

ollama pull qwen2.5:7b-instruct
```

Create `D:\Hisab_kitab\.env` (git-ignored, so never commit it):

```
GEMINI_API_KEY=...
GROQ_API_KEY=...          # optional backup
OPENROUTER_API_KEY=...    # optional backup
```

Build the data, train the model and run the backend:

```powershell
cd backend
python -m app.seed                 # synthetic bank: 50 customers, ~6 months of transactions
python -m app.ml.build_dataset     # Banking77 + Bitext + multilingual templates -> data/processed
python -m app.ml.train_intent      # fine-tune on GPU -> models/intent (+ metrics.json)
uvicorn app.main:app --port 8000
```

Run the frontend (in a second terminal):

```powershell
cd D:\Hisab_kitab\frontend
npm install
npm run dev                        # http://localhost:5173
```

## Tests and evaluation

```powershell
cd D:\Hisab_kitab\backend
python -m pytest -q                # unit tests (add -m "not live" to skip live-LLM tests)

cd D:\Hisab_kitab
.venv\Scripts\python eval\run_eval.py --mode hybrid
.venv\Scripts\python eval\run_eval.py --mode local --concurrency 2
```

`eval/queries.jsonl` holds 200 hand-written queries, 50 per language, covering all 17 intents. None of them are copies of the training templates. The eval reports intent accuracy, language accuracy, resolution rate, latency percentiles and per-language and per-intent breakdowns, and writes `eval/results_<mode>.json`.

A query counts as **resolved** when the intent is correct, the reply is non-empty, and any expected text is present. For the no-consent customer, a query is resolved when the assistant refuses.

## Data

All data is public or synthetic. No real customer data is used.

| Dataset | Use |
|---|---|
| [Banking77](https://github.com/PolyAI-LDN/task-specific-datasets) (PolyAI): 13,083 queries, 77 intents | Intent training (mapped to 17 unified intents) |
| [Bitext Retail Banking](https://huggingface.co/datasets/bitext/Bitext-retail-banking-llm-chatbot-training-dataset): 25,545 Q&A, 26 intents | Intent training + FAQ retrieval |
| Hand-written multilingual templates (`backend/app/ml/templates.py`) | Hindi / Kannada / Hinglish training examples |
| Synthetic bank (`backend/app/seed.py`, Faker en_IN, seed 42) | Mock customers, accounts, transactions, cards, loans |
| `backend/app/products.json` | Deposit and loan rates, fees, policy FAQs |

**Demo customers:** CUST001 Ravi Kumar (English), CUST002 Priya Sharma (Hindi), CUST003 Kiran Gowda (Kannada), CUST004 Arjun Mehta (no consent), CUST005 Anjali Verma (Hinglish).

## Privacy

- Identifiers are masked at the source: account numbers appear as `XXXX1234`, and phone and email are masked in the customer table.
- The privacy filter hides any sensitive identifiers the user types before cloud LLM calls. The trace shows how many were hidden.
- Personalised endpoints check `consent_personalization`. Without consent, the API returns HTTP 403 and the assistant replies with a refusal.
- Local mode keeps every step on the machine.

## Project layout

```
backend/app/
  config.py, db.py, seed.py, products.json   settings, schema, synthetic data
  bank_api.py                                mock core-banking API (/api/...)
  nlu/  lang.py pii.py entities.py intent.py language, PII firewall, entities, classifier
  ml/   intents.py templates.py build_dataset.py train_intent.py
  rag.py tools.py llm.py pipeline.py         retrieval, tool router, LLM clients, orchestration
  main.py                                    FastAPI app: /chat /metrics /customers /health
backend/tests/                               pytest suite
eval/        queries.jsonl, run_eval.py, results_*.json
frontend/    React web UI
docs/        API.md, DEMO_SCRIPT.md, design spec and implementation plan
data/raw/    downloaded datasets      models/  trained intent model (git-ignored)
```

Developer API reference: [docs/API.md](docs/API.md). Demo script: [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).
