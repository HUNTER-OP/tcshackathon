"""Intent -> bank API call. Returns tool data for the LLM and cards for the UI."""
import re
import time

from . import bank_api, rag
from .nlu.entities import Entities

KB_INTENTS = {"card_activate", "card_issue", "password_pin", "atm_branch", "dispute_refund", "faq_general", "fees_charges"}
AMOUNT_OPTIONS = ["₹1 lakh", "₹2 lakh", "₹5 lakh", "₹10 lakh"]


def _call(log: list, name: str, fn, *args, **kw):
    t = time.perf_counter()
    out = fn(*args, **kw)
    log.append({"tool": name, "args": {k: v for k, v in kw.items() if v is not None} or list(args[1:]),
                "ms": round((time.perf_counter() - t) * 1000, 1)})
    return out


BLOCK_YES = {"en": "Yes, block {kind} card {card}", "hinglish": "Haan, {kind} card {card} block karo",
             "hi": "हाँ, {kind} कार्ड {card} ब्लॉक करें", "kn": "ಹೌದು, {kind} ಕಾರ್ಡ್ {card} ಬ್ಲಾಕ್ ಮಾಡಿ"}
BLOCK_NO = {"en": "No, keep my card active", "hinglish": "Nahi, card chalu rakho",
            "hi": "नहीं, कार्ड चालू रखें", "kn": "ಬೇಡ, ಕಾರ್ಡ್ ಚಾಲೂ ಇರಲಿ"}
BLOCK_Q = {"en": "Should I block this card now? This can't be undone; a replacement is sent in 7 days.",
           "hinglish": "Kya main ye card abhi block kar doon? Ye wapas nahi hoga; naya card 7 din me aayega.",
           "hi": "क्या मैं यह कार्ड अभी ब्लॉक कर दूँ? यह वापस नहीं होगा; नया कार्ड 7 दिन में आएगा।",
           "kn": "ಈ ಕಾರ್ಡ್ ಅನ್ನು ಈಗ ಬ್ಲಾಕ್ ಮಾಡಲೇ? ಇದನ್ನು ಹಿಂಪಡೆಯಲಾಗುವುದಿಲ್ಲ; ಹೊಸ ಕಾರ್ಡ್ 7 ದಿನಗಳಲ್ಲಿ ಬರುತ್ತದೆ."}
KIND = {"debit": {"en": "debit", "hinglish": "debit", "hi": "डेबिट", "kn": "ಡೆಬಿಟ್"},
        "credit": {"en": "credit", "hinglish": "credit", "hi": "क्रेडिट", "kn": "ಕ್ರೆಡಿಟ್"}}
# a confirmation is "yes ... block ... XXXX1234" (the button text), in any of the four languages
BLOCK_CONFIRM = re.compile(r"^\s*(?:yes|haan|हाँ|ಹೌದು)[\s,!.]+(?=.*(?:block|ब्लॉक|ಬ್ಲಾಕ್)).*?xxxx(\d{4})", re.I | re.S)
BLOCK_DECLINE = re.compile(r"^\s*(?:no|nahi|नहीं|ಬೇಡ)[\s,!.]+.*(?:active|chalu|चालू|ಚಾಲೂ)", re.I | re.S)


def block_confirmation(text: str) -> str | None:
    """last4 of the card the customer confirmed blocking, or None."""
    m = BLOCK_CONFIRM.search(text)
    return m.group(1) if m else None


def run(intent: str, e: Entities, customer_id: str, query_en: str, lang: str = "en", confirmed_last4: str | None = None) -> dict:
    """-> {tool, data, needs, cards, calls}. Raises bank_api.ConsentError for personal data without consent."""
    calls: list[dict] = []
    cards: list[dict] = []
    data: dict = {}
    needs: list[str] = []

    if intent == "check_balance":
        data = _call(calls, "get_balance", bank_api.get_balance, customer_id, account_type=e.account_type or "savings")
        cards.append({"type": "balance", "data": data})
    elif intent == "transaction_history":
        n = int(m.group(1)) if (m := re.search(r"\b(?:last|pichle|पिछले|ಕೊನೆಯ)\s*(\d{1,2})\b", query_en.lower())) else 10
        items = _call(calls, "get_transactions", bank_api.get_transactions, customer_id,
                      days=e.days or 60, category=e.category, limit=min(n, 25))
        data = {"items": items, "days": e.days or 60, "category": e.category}
        cards.append({"type": "transactions", "data": data})
    elif intent == "spending_summary":
        data = _call(calls, "spending_summary", bank_api.spending_summary, customer_id, days=e.days or 30)
        if e.category:
            data["asked_category"] = e.category
            data["asked_category_amount"] = data["by_category"].get(e.category, 0)
        cards.append({"type": "spending", "data": data})
    elif intent in ("loan_eligibility", "emi_calculation"):
        lt = e.loan_type or "personal"
        if e.amount_inr is None:
            base = _call(calls, "loan_eligibility", bank_api.loan_eligibility, customer_id,
                         loan_type=lt, amount=None, tenure_months=e.tenure_months)
            loans = [dict(r) for r in bank_api.conn().execute(
                "select type, principal, emi, outstanding, rate from loans where customer_id=?", (customer_id,))]
            data = {"loan_type": lt, "max_amount_you_can_get": base["max_amount"], "rate": base["rate"],
                    "existing_loans": loans, "missing": "amount"}
            needs = ["amount_inr"]
            cards.append({"type": "followup", "data": {
                "missing": ["amount"], "question": f"How much {lt} loan are you looking for?",
                "options": [f"{o} {lt} loan" for o in AMOUNT_OPTIONS]}})
        else:
            data = _call(calls, "loan_eligibility", bank_api.loan_eligibility, customer_id,
                         loan_type=lt, amount=e.amount_inr, tenure_months=e.tenure_months)
            cards.append({"type": "loan", "data": data})
    elif intent in ("interest_rates", "loan_products"):
        kind = e.account_type if e.account_type in ("fd", "savings") else e.loan_type
        data = _call(calls, "get_rates", bank_api.get_rates, kind)
        cards.append({"type": "rates", "data": data})
        if intent == "loan_products":
            data = {**data, "faq": rag.search(query_en, k=2)}
    elif intent == "card_block":
        if confirmed_last4:
            data = _call(calls, "block_card", bank_api.block_card, customer_id, last4=confirmed_last4)
            cards.append({"type": "card_action", "data": data})
        else:
            # never block on the first message: list active cards and ask the customer to confirm with a button
            active = [c for c in _call(calls, "get_cards", bank_api.get_cards, customer_id) if c["status"] == "active"]
            want = "credit" if re.search(r"credit|क्रेडिट|ಕ್ರೆಡಿಟ್", query_en, re.I) else "debit"
            active.sort(key=lambda c: (c["last4"] != e.card_last4, c["type"] != want))
            options = [BLOCK_YES[lang].format(kind=KIND.get(c["type"], KIND["debit"])[lang], card=f"XXXX{c['last4']}") for c in active]
            data = {"awaiting_confirmation": True, "active_cards": [f"{c['type']} XXXX{c['last4']}" for c in active],
                    "note": "Do NOT say the card is blocked. Tell the customer you can block it right away and ask them to confirm using the buttons."}
            cards.append({"type": "followup", "data": {"missing": [], "question": BLOCK_Q[lang], "options": options + [BLOCK_NO[lang]]}})
    elif intent == "transfer_money":
        if e.amount_inr is None or not re.search(r"\b(send|transfer|pay|bhejo|bhej|भेज|ಕಳುಹಿಸ)", query_en.lower()):
            data = {"faq": rag.search(query_en, k=2)}
            if e.amount_inr is None and re.search(r"\b(send|transfer|pay)\b", query_en.lower()):
                needs = ["amount_inr"]
                cards.append({"type": "followup", "data": {"missing": ["amount"], "question": "How much should I send?",
                                                           "options": ["Send ₹500", "Send ₹2,000", "Send ₹10,000"]}})
            else:
                cards.append({"type": "faq", "data": {"items": data["faq"]}})
        else:
            to = f"XXXX{e.card_last4}" if e.card_last4 else "saved beneficiary"
            data = _call(calls, "transfer", bank_api.transfer, customer_id, to_masked=to, amount=e.amount_inr)
            cards.append({"type": "transfer", "data": data})
    elif intent in KB_INTENTS:
        hits = _call(calls, "faq_search", rag.search, query_en, k=3)
        data = {"faq": hits}
        if intent == "fees_charges":
            data["fees"] = bank_api.PRODUCTS["fees"]
            data["cards"] = bank_api.PRODUCTS["cards"]
        cards.append({"type": "faq", "data": {"items": hits}})
    return {"tool": calls[0]["tool"] if calls else None, "data": data, "needs": needs, "cards": cards, "calls": calls}
