"""Mock core-banking API. Plain functions (used by the assistant's tools) + a FastAPI router."""
import json
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import connect

PRODUCTS = json.loads((Path(__file__).parent / "products.json").read_text(encoding="utf-8"))
_conn: sqlite3.Connection | None = None


class ConsentError(Exception):
    pass


class NotFound(Exception):
    pass


def set_conn(conn: sqlite3.Connection) -> None:
    global _conn
    _conn = conn


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = connect()
    return _conn


def get_customer(cid: str) -> dict:
    row = conn().execute("select * from customers where id=?", (cid,)).fetchone()
    if not row:
        raise NotFound(cid)
    return dict(row)


def _require_consent(cid: str) -> dict:
    c = get_customer(cid)
    if not c["consent_personalization"]:
        raise ConsentError(cid)
    return c


def get_accounts(cid: str) -> list[dict]:
    _require_consent(cid)
    return [dict(r) for r in conn().execute(
        "select id, type, number_masked, balance, currency from accounts where customer_id=?", (cid,))]


def _account(cid: str, account_type: str = "savings") -> dict:
    row = conn().execute("select * from accounts where customer_id=? and type=?", (cid, account_type)).fetchone()
    if not row:
        row = conn().execute("select * from accounts where customer_id=? and type='savings'", (cid,)).fetchone()
    return dict(row)


def get_balance(cid: str, account_type: str = "savings") -> dict:
    _require_consent(cid)
    a = _account(cid, account_type or "savings")
    return {"account": a["number_masked"], "account_type": a["type"], "balance": round(a["balance"], 2),
            "currency": "INR", "as_of": datetime.now().isoformat(timespec="minutes")}


def get_transactions(cid: str, days: int = 30, category: str | None = None, limit: int = 10) -> list[dict]:
    _require_consent(cid)
    a = _account(cid)
    since = (date.today() - timedelta(days=days or 30)).isoformat()
    q = "select date, description, category, amount, balance_after from transactions where account_id=? and date>=?"
    args: list = [a["id"], since]
    if category:
        q += " and category=?"
        args.append(category)
    q += " order by date desc limit ?"
    args.append(limit or 10)
    return [dict(r) for r in conn().execute(q, args)]


def spending_summary(cid: str, days: int = 30) -> dict:
    _require_consent(cid)
    a = _account(cid)
    since = (date.today() - timedelta(days=days or 30)).isoformat()
    rows = conn().execute(
        "select category, sum(amount) s from transactions where account_id=? and date>=? group by category",
        (a["id"], since)).fetchall()
    by_cat = {r["category"]: round(-r["s"], 2) for r in rows if r["s"] < 0}
    credit = sum(r["s"] for r in rows if r["s"] > 0)
    return {"days": days or 30, "total_debit": round(sum(by_cat.values()), 2), "total_credit": round(credit, 2),
            "by_category": dict(sorted(by_cat.items(), key=lambda kv: -kv[1]))}


def emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    r = annual_rate / 1200
    if r == 0:
        return round(principal / tenure_months, 2)
    f = (1 + r) ** tenure_months
    return round(principal * r * f / (f - 1), 2)


def _principal_for_emi(emi_amt: float, annual_rate: float, n: int) -> float:
    r = annual_rate / 1200
    f = (1 + r) ** n
    return emi_amt * (f - 1) / (r * f)


def loan_eligibility(cid: str, loan_type: str, amount: float | None, tenure_months: int | None = None) -> dict:
    c = _require_consent(cid)
    prod = PRODUCTS["loans"].get(loan_type or "personal") or PRODUCTS["loans"]["personal"]
    loan_type = loan_type if loan_type in PRODUCTS["loans"] else "personal"
    n = min(tenure_months or prod["max_tenure_months"], prod["max_tenure_months"])
    existing = conn().execute("select coalesce(sum(emi),0) from loans where customer_id=?", (cid,)).fetchone()[0]
    income = c["monthly_income"]
    max_emi = max(0.0, income * prod["max_foir"] - existing)
    max_amount = min(prod["max_amount"], round(_principal_for_emi(max_emi, prod["rate"], n), -3)) if max_emi else 0
    req = float(amount or max_amount)
    e = emi(req, prod["rate"], n)
    reasons = []
    if income < prod["min_income"]:
        reasons.append(f"Monthly income below minimum of {prod['min_income']}")
    if c["credit_score"] < 650:
        reasons.append(f"Credit score {c['credit_score']} below 650")
    if e > max_emi:
        reasons.append(f"EMI {e} exceeds affordable EMI {round(max_emi, 2)} (50% of income minus existing EMIs)")
    if req > prod["max_amount"]:
        reasons.append(f"Amount above product maximum {prod['max_amount']}")
    return {"loan_type": loan_type, "product": prod["name"], "requested_amount": req, "tenure_months": n,
            "rate": prod["rate"], "emi": e, "eligible": not reasons, "max_amount": max_amount,
            "affordable_emi": round(max_emi, 2), "existing_emi": round(existing, 2), "monthly_income": income,
            "credit_score": c["credit_score"], "foir_after": round((existing + e) / income, 3),
            "processing_fee": round(req * prod["processing_fee_pct"] / 100, 2), "reasons": reasons}


def get_rates(kind: str | None = None) -> dict:
    if kind in ("fd", "savings", "rd"):
        return {"deposits": PRODUCTS["deposits"]}
    if kind in PRODUCTS["loans"]:
        return {"loans": {kind: PRODUCTS["loans"][kind]}}
    return {"deposits": PRODUCTS["deposits"], "loans": PRODUCTS["loans"]}


def get_cards(cid: str) -> list[dict]:
    _require_consent(cid)
    return [dict(r) for r in conn().execute("select id, last4, type, status from cards where customer_id=?", (cid,))]


def block_card(cid: str, last4: str | None = None, card_type: str | None = None) -> dict:
    cards = get_cards(cid)
    target = next((c for c in cards if last4 and c["last4"] == last4), None) or \
        next((c for c in cards if card_type and c["type"] == card_type), None) or cards[0]
    conn().execute("update cards set status='blocked' where id=?", (target["id"],))
    conn().commit()
    return {"card": f"XXXX{target['last4']}", "type": target["type"], "status": "blocked",
            "reference": f"BLK{random.randint(100000, 999999)}", "replacement_eta_days": 7}


def transfer(cid: str, to_masked: str, amount: float) -> dict:
    a = _account(cid)
    _require_consent(cid)
    if amount <= 0 or amount > a["balance"]:
        return {"status": "failed", "reason": "insufficient balance" if amount > 0 else "invalid amount",
                "balance": round(a["balance"], 2)}
    nb = round(a["balance"] - amount, 2)
    conn().execute("update accounts set balance=? where id=?", (nb, a["id"]))
    conn().execute("insert into transactions values (?,?,?,?,?,?,?)",
                   (f"TXN{random.randint(10**8, 10**9)}", a["id"], datetime.now().isoformat(timespec="seconds"),
                    f"Transfer to {to_masked}", "upi_transfer", -amount, nb))
    conn().commit()
    return {"status": "success", "ref": f"UTR{random.randint(10**9, 10**10)}", "amount": amount,
            "to": to_masked, "balance_after": nb}


# ---------------- HTTP router ----------------
router = APIRouter(prefix="/api", tags=["mock-bank"])


def _wrap(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except ConsentError:
        raise HTTPException(403, "Customer has not consented to personalised data access")
    except NotFound:
        raise HTTPException(404, "Customer not found")


class EligibilityReq(BaseModel):
    customer_id: str
    loan_type: str
    amount: float | None = None
    tenure_months: int | None = None


class TransferReq(BaseModel):
    customer_id: str
    to: str
    amount: float


@router.get("/customers/{cid}/accounts")
def api_accounts(cid: str):
    return _wrap(get_accounts, cid)


@router.get("/accounts/{cid}/balance")
def api_balance(cid: str, account_type: str = "savings"):
    return _wrap(get_balance, cid, account_type)


@router.get("/accounts/{cid}/transactions")
def api_transactions(cid: str, days: int = 30, category: str | None = None, limit: int = 10):
    return _wrap(get_transactions, cid, days, category, limit)


@router.get("/accounts/{cid}/summary")
def api_summary(cid: str, days: int = 30):
    return _wrap(spending_summary, cid, days)


@router.post("/loans/eligibility")
def api_eligibility(req: EligibilityReq):
    return _wrap(loan_eligibility, req.customer_id, req.loan_type, req.amount, req.tenure_months)


@router.get("/loans/emi")
def api_emi(principal: float, rate: float, tenure_months: int):
    return {"emi": emi(principal, rate, tenure_months)}


@router.get("/products/rates")
def api_rates(kind: str | None = None):
    return get_rates(kind)


@router.post("/cards/{cid}/block")
def api_block(cid: str, last4: str | None = None):
    return _wrap(block_card, cid, last4)


@router.post("/transfers")
def api_transfer(req: TransferReq):
    return _wrap(transfer, req.customer_id, req.to, req.amount)
