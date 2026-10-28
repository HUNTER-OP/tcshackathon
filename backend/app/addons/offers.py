"""Next-best-offer: pick at most one product offer card for a chat reply.
Usage: from addons.offers import suggest_offer
       offer = suggest_offer(customer, intent, tool_data, PRODUCTS); if offer: cards.append(offer)
Pure function: no I/O, no LLM. Every rate/fee comes from `products`; amounts come from tool_data/customer.
"""
from __future__ import annotations

BLOCKED_INTENTS = {"human_agent", "dispute_refund", "card_block"}
LOAN_INTENTS = {"loan_eligibility", "emi_calculation"}
RATE_INTENTS = {"interest_rates", "loan_products"}

FD_MIN_BALANCE = 100_000
PL_MIN_INCOME = 50_000
PL_MIN_SCORE = 720
SPEND_RATIO = 0.40


def _has_consent(customer: dict) -> bool:
    for key in ("consent_personalization", "consent"):
        if key in customer:
            return bool(customer[key])
    return False


def _unwrap(tool_data: dict) -> dict:
    """Accept either a card's `data` dict, a full card {type, data}, or {card_type: data}."""
    if not isinstance(tool_data, dict):
        return {}
    if "data" in tool_data and isinstance(tool_data["data"], dict):
        return tool_data["data"]
    for key in ("balance", "loan", "spending", "rates"):
        inner = tool_data.get(key)
        if isinstance(inner, dict):
            return inner
    return tool_data


def _balance(data: dict) -> float | None:
    if isinstance(data.get("balance"), (int, float)):
        return float(data["balance"])
    accounts = data.get("accounts")
    if isinstance(accounts, list):
        vals = [a.get("balance") for a in accounts
                if isinstance(a, dict) and a.get("account_type", a.get("type")) == "savings"
                and isinstance(a.get("balance"), (int, float))]
        if vals:
            return float(sum(vals))
    return None


def _inr(x: float) -> str:
    """Indian digit grouping: 1250000 -> 12,50,000."""
    s = str(int(round(x)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def _offer(offer_id, title, description, cta, reason, rate=None, amount=None) -> dict:
    data = {"offer_id": offer_id, "title": title, "description": description, "cta": cta, "reason": reason}
    if rate is not None:
        data["rate"] = rate
    if amount is not None:
        data["amount"] = amount
    return {"type": "offer", "data": data}


def _fd_offer(balance: float, products: dict) -> dict | None:
    fds = products.get("deposits", {}).get("fd") or []
    if not fds:
        return None
    best = max(fds, key=lambda f: f["rate"])
    return _offer(
        "fd_best_rate",
        f"Earn {best['rate']}% with a Fixed Deposit",
        f"Your savings balance is ₹{_inr(balance)}. Park idle funds in an FD for {best['tenor']} at {best['rate']}% p.a.",
        "Open FD",
        f"savings balance ≥ ₹{_inr(FD_MIN_BALANCE)}",
        rate=best["rate"],
    )


def _personal_loan_offer(customer: dict, products: dict) -> dict | None:
    pl = products.get("loans", {}).get("personal")
    if not pl:
        return None
    income = float(customer["monthly_income"])
    rate = pl["rate"]
    n = pl["max_tenure_months"]
    emi_cap = income * pl["max_foir"]
    r = rate / 1200
    principal = emi_cap * ((1 + r) ** n - 1) / (r * (1 + r) ** n)
    amount = min(principal, pl["max_amount"])
    amount = int(amount // 10_000 * 10_000)
    return _offer(
        "personal_loan_preapproved",
        f"Pre-approved {pl['name']} up to ₹{_inr(amount)}",
        f"Based on your income and credit score {customer['credit_score']}, get up to ₹{_inr(amount)} "
        f"at {rate}% for up to {n} months. Processing fee {pl['processing_fee_pct']}%.",
        "Check offer",
        f"income ≥ ₹{_inr(PL_MIN_INCOME)}, credit score ≥ {PL_MIN_SCORE}, no existing EMI",
        rate=rate,
        amount=amount,
    )


def _card_offer(total: float, income: float, products: dict) -> dict | None:
    card = products.get("cards", {}).get("credit_platinum")
    if not card:
        return None
    pct = round(total / income * 100)
    return _offer(
        "credit_platinum",
        "Platinum Credit Card",
        f"You spent ₹{_inr(total)} recently ({pct}% of income). Get rewards on everyday spends "
        f"with the Platinum card. Annual fee ₹{_inr(card['annual_fee'])}.",
        "Apply now",
        f"spending ≥ {int(SPEND_RATIO * 100)}% of monthly income",
    )


def _cheapest_loan_offer(data: dict, products: dict) -> dict | None:
    loans = products.get("loans") or {}
    wanted = data.get("loan_type")
    pool = {k: v for k, v in loans.items() if k == wanted} if wanted in loans else loans
    if not pool:
        return None
    key, best = min(pool.items(), key=lambda kv: kv[1]["rate"])
    return _offer(
        f"cheapest_loan_{key}",
        f"{best['name']} from {best['rate']}% p.a.",
        f"Our lowest loan rate: {best['name']} at {best['rate']}% for up to {best['max_tenure_months']} months, "
        f"up to ₹{_inr(best['max_amount'])}.",
        "See details",
        "cheapest matching loan product",
        rate=best["rate"],
    )


def suggest_offer(customer: dict, intent: str, tool_data: dict, products: dict) -> dict | None:
    if not customer or not _has_consent(customer):
        return None
    if intent in BLOCKED_INTENTS:
        return None
    data = _unwrap(tool_data or {})
    income = float(customer.get("monthly_income") or 0)

    if intent == "check_balance":
        bal = _balance(data)
        if bal is not None and bal >= FD_MIN_BALANCE:
            return _fd_offer(bal, products)
        return None

    if intent in LOAN_INTENTS:
        score = int(customer.get("credit_score") or 0)
        existing = data.get("existing_emi") or 0
        if income >= PL_MIN_INCOME and score >= PL_MIN_SCORE and not existing:
            return _personal_loan_offer(customer, products)
        return None

    if intent == "spending_summary":
        total = data.get("total_debit")
        if isinstance(total, (int, float)) and income > 0 and total >= SPEND_RATIO * income:
            return _card_offer(float(total), income, products)
        return None

    if intent in RATE_INTENTS:
        return _cheapest_loan_offer(data, products)

    return None
