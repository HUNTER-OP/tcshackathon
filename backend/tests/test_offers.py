"""Tests for next-best-offer rules.
Usage: cd pc2 && python -m pytest addons/test_offers.py -q
Uses fixtures/products.json and card shapes captured from the live /chat.
"""
import json
from pathlib import Path

import pytest

from app.addons.offers import suggest_offer

PRODUCTS = json.loads((Path(__file__).resolve().parent / "fixtures" / "products.json").read_text(encoding="utf-8"))

RAVI = {"id": "CUST001", "name": "Ravi Kumar", "monthly_income": 85000.0, "credit_score": 768,
        "consent_personalization": 1, "preferred_language": "en"}
ARJUN = {"id": "CUST004", "name": "Arjun Mehta", "monthly_income": 70000.0, "credit_score": 700,
         "consent_personalization": 0, "preferred_language": "en"}
ANJALI = {"id": "CUST005", "name": "Anjali Verma", "monthly_income": 48000.0, "credit_score": 689,
          "consent_personalization": 1, "preferred_language": "hinglish"}

BALANCE_HIGH = {"account": "XXXX6561", "account_type": "savings", "balance": 184572.0, "currency": "INR"}
BALANCE_LOW = {**BALANCE_HIGH, "balance": 21240.0}
LOAN = {"loan_type": "car", "product": "Car Loan", "requested_amount": 500000.0, "tenure_months": 84,
        "rate": 9.2, "emi": 8095.38, "eligible": True, "existing_emi": 0, "monthly_income": 85000.0}
SPENDING = {"days": 30, "total_debit": 89728.0, "total_credit": 85000.0, "by_category": {"food": 1666.0}}
RATES = {"deposits": PRODUCTS["deposits"], "loans": PRODUCTS["loans"]}


def test_fd_offer_on_high_balance():
    o = suggest_offer(RAVI, "check_balance", BALANCE_HIGH, PRODUCTS)
    assert o["type"] == "offer"
    assert o["data"]["offer_id"] == "fd_best_rate"
    assert o["data"]["rate"] == max(f["rate"] for f in PRODUCTS["deposits"]["fd"])


def test_fd_offer_accepts_full_card():
    o = suggest_offer(RAVI, "check_balance", {"type": "balance", "data": BALANCE_HIGH}, PRODUCTS)
    assert o["data"]["offer_id"] == "fd_best_rate"


def test_no_fd_offer_on_low_balance():
    assert suggest_offer(RAVI, "check_balance", BALANCE_LOW, PRODUCTS) is None


def test_personal_loan_preapproved():
    o = suggest_offer(RAVI, "loan_eligibility", LOAN, PRODUCTS)
    d = o["data"]
    assert d["offer_id"] == "personal_loan_preapproved"
    assert d["rate"] == PRODUCTS["loans"]["personal"]["rate"]
    assert 0 < d["amount"] <= PRODUCTS["loans"]["personal"]["max_amount"]


def test_no_personal_loan_with_existing_emi():
    assert suggest_offer(RAVI, "emi_calculation", {**LOAN, "existing_emi": 12000}, PRODUCTS) is None


def test_no_personal_loan_low_score_or_income():
    assert suggest_offer(ANJALI, "loan_eligibility", LOAN, PRODUCTS) is None


def test_card_offer_on_high_spending():
    o = suggest_offer(RAVI, "spending_summary", SPENDING, PRODUCTS)
    assert o["data"]["offer_id"] == "credit_platinum"


def test_no_card_offer_on_low_spending():
    assert suggest_offer(RAVI, "spending_summary", {**SPENDING, "total_debit": 20000.0}, PRODUCTS) is None


@pytest.mark.parametrize("intent", ["interest_rates", "loan_products"])
def test_cheapest_loan(intent):
    o = suggest_offer(RAVI, intent, RATES, PRODUCTS)
    cheapest = min(PRODUCTS["loans"].values(), key=lambda v: v["rate"])
    assert o["data"]["rate"] == cheapest["rate"]
    assert cheapest["name"] in o["data"]["title"]


def test_cheapest_loan_respects_loan_type():
    o = suggest_offer(RAVI, "interest_rates", {"loan_type": "car"}, PRODUCTS)
    assert o["data"]["rate"] == PRODUCTS["loans"]["car"]["rate"]


def test_none_without_consent():
    assert suggest_offer(ARJUN, "check_balance", BALANCE_HIGH, PRODUCTS) is None
    assert suggest_offer(ARJUN, "interest_rates", RATES, PRODUCTS) is None


def test_none_with_consent_field_from_customers_endpoint():
    c = {k: v for k, v in RAVI.items() if k != "consent_personalization"} | {"consent": False}
    assert suggest_offer(c, "check_balance", BALANCE_HIGH, PRODUCTS) is None


@pytest.mark.parametrize("intent", ["human_agent", "dispute_refund", "card_block"])
def test_none_on_blocked_intents(intent):
    assert suggest_offer(RAVI, intent, BALANCE_HIGH, PRODUCTS) is None


@pytest.mark.parametrize("intent", ["transfer_money", "faq_general", "atm_branch"])
def test_none_when_nothing_matches(intent):
    assert suggest_offer(RAVI, intent, BALANCE_HIGH, PRODUCTS) is None


def test_single_card_shape():
    o = suggest_offer(RAVI, "check_balance", BALANCE_HIGH, PRODUCTS)
    assert set(o) == {"type", "data"}
    assert {"offer_id", "title", "description", "cta", "reason"} <= set(o["data"])
