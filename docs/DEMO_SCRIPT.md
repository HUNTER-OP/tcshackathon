# Hisab Kitab — 5-minute demo script

**Setup before recording:** backend running (`uvicorn app.main:app --port 8000`), frontend at `http://localhost:5173`, Ollama running, mode = **Hybrid**, customer = **Ravi Kumar (CUST001)**, browser zoom about 110%, screen recorder at 1080p. Restart the backend just before recording so the dashboard starts from zero.

Each section below lists **Type** (exact text to enter), **Point at** (what to show on screen) and **Say** (narration). The tag in brackets is the judging criterion the narration supports.

---

### 0:00–0:30 — Hook and problem

**Show:** the landing chat screen.

**Say:** "Thousands of bank customers wait on hold every day just to ask their balance or whether they can afford a loan. Scripted FAQ bots break the moment you phrase something differently, or switch to Hindi. This is Hisab Kitab: ask your bank anything, in your own language, and get a correct, personal answer in seconds." *[Relevance]*

---

### 0:30–1:05 — English: balance and transactions (Ravi)

**Type:** `What's my balance?`

**Point at:** the balance card, then the **"Why this answer"** trace sidebar showing intent `check_balance`, the confidence, the `get_balance` tool call, the model and latency.

**Say:** "The answer comes from the bank's API, not from the AI's imagination. The trace shows what it understood, how sure it was, which API it called and how long it took. No black box." *[AI/ML, Innovation]*

**Type:** `Show my last 5 transactions`

**Point at:** the transaction table card.

---

### 1:05–1:50 — Hinglish: loan affordability

**Type:** `Kya main 5 lakh ka car loan afford kar sakta hoon?`

**Point at:** the language badge (`hinglish`), the extracted entities (`amount 500000`, `loan_type car`), and the loan card showing eligible, EMI, maximum amount and FOIR. Drag the EMI slider if the UI has one.

**Say:** "Hinglish, the way people actually type. Our own intent model, fine-tuned on the GPU on more than 11,000 banking queries, picks the intent. The rule engine checks income and existing EMIs against a 50% limit. The reply explains the decision, and every number comes from the calculation." *[AI/ML, Relevance]*

---

### 1:50–2:25 — Hindi: spending insight (Priya)

**Switch customer:** Priya Sharma (CUST002).

**Type:** `पिछले महीने मैंने खाने पर कितना खर्च किया?`

**Point at:** the reply in Devanagari and the spending chart card.

**Say:** "It replies in Hindi, in Hindi script. It's the same pipeline; only the language changes." *[Innovation]*

---

### 2:25–2:50 — Kannada: rates (Kiran)

**Switch customer:** Kiran Gowda (CUST003). Optionally use the **mic button** with Kannada voice.

**Type:** `FD ಬಡ್ಡಿ ದರ ಎಷ್ಟು?`

**Point at:** the rates card and the reply in Kannada.

**Say:** "Kannada, by voice or text: English, Hindi, Kannada and Hinglish, all detected automatically."

---

### 2:50–3:20 — Privacy filter

**Switch back:** Ravi (CUST001).

**Type:** `My card 4111 1111 1111 1111 is lost, block it`

**Point at:** the trace showing `1 redacted` and the redacted text with `[CARD]`, then the card-blocked confirmation card.

**Say:** "The card number is masked before any cloud AI sees it. The model never receives raw personal data, and the card is blocked through the bank API." *[Feasibility, privacy]*

---

### 3:20–3:45 — Consent

**Switch customer:** Arjun Mehta (CUST004).

**Type:** `What's my balance?`

**Point at:** the consent refusal card.

**Say:** "Arjun hasn't consented to personalised data use, so the assistant refuses politely and fetches nothing. Consent is checked at the API layer, not just in the prompt."

---

### 3:45–4:10 — Human handoff

**Type:** `I want to talk to a human`

**Point at:** the handoff ticket card with ticket ID, summary and sentiment.

**Say:** "When the bot is unsure, or the customer asks, it hands over with a ready-made summary, so the agent doesn't start from zero. This is how it cuts call-centre load without trapping anyone." *[Relevance]*

---

### 4:10–4:40 — Offline mode

**Toggle:** **Local** mode (and optionally turn off Wi-Fi).

**Type:** `mera balance kitna hai`

**Point at:** the trace showing `model_used: ollama`, plus the latency.

**Say:** "Flip one switch and everything runs on our own GPU, with a local model, no internet and no data leaving the bank. If the cloud model is slow or down, it falls back to this automatically." *[Feasibility and scalability]*

---

### 4:40–5:00 — Dashboard and results

**Open:** the ops dashboard.

**Point at:** total queries, resolution rate, latency, language mix and cloud vs local split.

**Say:** "On our 200-question test set across four languages we hit <!-- EVAL_RESOLUTION --> resolution with a p95 response time of <!-- EVAL_P95 -->, against targets of 80% and 15 seconds. Hisab Kitab: your bank, in your language." *[Relevance, Team work]*

> Fill the two placeholders from `eval/results_hybrid.json` before recording. Never quote numbers you haven't measured.

---

### Backup lines (if something fails live)

- Cloud model slow or erroring: "Watch the fallback." Then point at `model_used` switching to `ollama` in the trace.
- Wrong intent: "That's the confidence score. Below the threshold, it asks or hands off instead of guessing."
