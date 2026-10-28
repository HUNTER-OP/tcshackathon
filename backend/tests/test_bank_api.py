import pytest
from fastapi.testclient import TestClient

from app import bank_api
from app.bank_api import ConsentError, emi, get_balance, loan_eligibility, transfer
from app.db import connect
from app.seed import seed


@pytest.fixture(autouse=True)
def seeded():
    c = connect(":memory:")
    seed(c)
    bank_api.set_conn(c)
    yield c


def client():
    from app.main import app
    return TestClient(app)


def test_emi_formula():
    assert abs(emi(500000, 9.2, 60) - 10427.6) < 1


def test_car_loan_eligibility_for_demo_persona():
    r = loan_eligibility("CUST001", "car", 500000, 60)
    assert r["eligible"] is True
    assert r["emi"] == emi(500000, 9.2, 60)


def test_ineligible_when_amount_far_above_income():
    r = loan_eligibility("CUST001", "personal", 85000 * 12 * 10, 60)
    assert r["eligible"] is False and r["reasons"]


def test_consent_blocks_balance():
    with pytest.raises(ConsentError):
        get_balance("CUST004")
    assert client().get("/api/accounts/CUST004/balance").status_code == 403


def test_transfer_over_balance_fails():
    bal = get_balance("CUST001")["balance"]
    assert transfer("CUST001", "XXXX9999", bal + 1)["status"] == "failed"


def test_rates_endpoint():
    r = client().get("/api/products/rates")
    assert r.status_code == 200 and "car" in r.text
