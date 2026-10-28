# Hisab Kitab: Privacy & Compliance Controls

> Prototype for the TCS hackathon. This page maps what the prototype does to India's Digital Personal Data Protection Act 2023 (DPDP Act) and RBI guidance. **It is not a legal compliance certification.** Gaps are listed honestly at the end.

## Controls in the prototype

| # | Control | How it works | Verified by |
|---|---|---|---|
| C1 | **Privacy filter before any cloud LLM** | Card, Aadhaar, PAN, phone, email, account number, OTP and CVV are replaced with tags like `[CARD]` and `[PAN]` before the message reaches Gemini, Groq or Ollama. The trace shows `redactions` and `redacted_text`. | `pc2/eval/test_pii_leak.py` (30 live cases) |
| C2 | **Consent gating** | If `consent_personalization = 0`, no balance, transaction or spending data is fetched. The bot returns a `consent` card that explains how to enable consent. | `test_no_consent_gets_no_personal_data` (CUST004, en/hi/hinglish) |
| C3 | **Only tool numbers reach the LLM** | Balances, EMIs and rates come from the mock bank API and `products.json`. The LLM only words the reply and never invents figures. If the LLM fails, a template reply is built from the tool data. | Pipeline design and trace `tool_calls` |
| C4 | **Masked identifiers** | Account numbers (`XXXX6561`), phone (`+91 XXXXXX1824`) and email (`r***@mail.com`) are stored and shown masked. | `hisab.db` schema |
| C5 | **Offline local mode** | `mode: "local"` runs the full pipeline on the on-premise GPU with Ollama `qwen2.5:7b-instruct`. No data leaves the premises. | UI mode toggle; `model_used: ollama:*` in the trace |
| C6 | **Synthetic data only** | All 50 customers and their transactions are generated. Training uses public datasets (Banking77, Bitext) plus synthetic paraphrases. No real customer data is used. | `seed.py`, dataset sources |
| C7 | **Explainable answers** | Every reply carries a trace: intent, confidence, entities, tools called, model and latency. | `/chat` response, "why this answer" panel |
| C8 | **Human handoff** | Low confidence or an explicit request creates a ticket with a summary, so a human decides on sensitive cases. | `/tickets`, agent console |
| C9 | **No product offers without consent** | `suggest_offer()` returns nothing when consent is 0, or during complaints, disputes and card blocks. | `pc2/addons/test_offers.py` |

## Mapping to the DPDP Act 2023

| DPDP principle | Section (approx.) | Our controls |
|---|---|---|
| **Consent:** free, specific, informed, and as easy to withdraw as to give | s.6 | C2, C9. Consent is a per-customer flag. Without it, personal data is never fetched. |
| **Notice:** tell the person what data is used and why | s.5 | The consent card explains why data is withheld and how to enable it. *A full notice screen is not built.* |
| **Purpose limitation:** use data only for the stated purpose | s.4, s.6 | Tools fetch only what the detected intent needs (balance → `get_balance` only). The cloud LLM gets the redacted query plus the tool output for that purpose. |
| **Data minimisation** | s.6(1) | C1, C3, C4. The LLM sees tags in place of identifiers and masked account numbers. |
| **Accuracy** | s.8(3) | C3. Numbers come from the system of record, not the LLM. |
| **Security safeguards** | s.8(5) | C1, C5. Keys are kept in a git-ignored `.env`. *No encryption at rest or auth in the prototype.* |
| **Rights of the data principal:** access, correction, erasure, grievance | s.11–13 | The bot answers "show my data" queries (balance, transactions). C8 gives a grievance path through a human agent. *Correction and erasure are not implemented.* |
| **Cross-border transfer** | s.16 | C5 keeps all processing on-premise. In hybrid mode, only redacted text goes to the cloud LLM. |

## Mapping to RBI guidance

| RBI guidance | Our controls |
|---|---|
| **IT Governance, Risk, Controls and Assurance Directions (2023)**: data security, access control, audit | C1, C7. The trace on every reply supports an audit trail. *Persisting the audit logs is a production to-do.* |
| **Outsourcing of IT Services Directions (2023)**: the bank stays responsible, data is protected at the vendor, and an exit or contingency plan exists | C1 means the cloud LLM vendor never receives raw personal data. C5 is the contingency and exit plan: full offline operation with no vendor dependency. Automatic fallback goes Gemini → Groq → Ollama → template. |
| **Storage of payment system data (2018 circular)**: payment data stored in India | C5. Card and payment data are never sent out raw. Card numbers are redacted (C1). |
| **Customer Service and Grievance Redressal**: an escalation path | C8. Human handoff tickets carry the AI summary, sentiment and priority. |
| **Never ask for OTP, PIN or CVV** (standard RBI fraud advisory) | C1 redacts OTP and CVV. *Recommended: the bot should actively warn customers who share an OTP (see the PC-2 stretch item `scam_check.py`).* |

## Test results (live run, 2026-10-28, `mode=local`, backend 10.127.10.203:8000)

`python -m pytest eval/test_pii_leak.py`: **33 passed, 3 failed of 36.**

| Failed case | Input | Observed |
|---|---|---|
| `phone_dash` | `contact +91-98765-43210 for callback` | Not redacted |
| `account_15` | `account number 123456789012345 balance` | Not redacted (15-digit account) |
| `otp_sentence` | `bank wale ne otp maanga 739201 de du?` | Not redacted, and part of the OTP was echoed in the reply |

All 5 no-consent checks for CUST004 passed. Suggested fixes for the filter are in `pc2/HANDOVER.md`.

## Not production-grade (honest gaps)

- Detection is regex-based. Unusual formats can slip through, as the three failures above show. Production would add an ML-based personal-data detector and a filter on the LLM's output as well as its input.
- There is no authentication: `customer_id` is trusted from the client.
- The SQLite database is not encrypted at rest, and there is no key vault (keys sit in `.env`).
- There is no persistent, tamper-proof audit log, and no data retention or erasure workflow.
- Consent is a single flag. The DPDP Act expects consent per purpose, with withdrawal and a consent-manager integration.
- Cloud LLM providers' data retention terms are not assessed. Production would need a contract (DPA) and data-residency guarantees.
- No breach notification process (DPDP s.8(6)) and no Data Protection Officer role, since this is a prototype.
