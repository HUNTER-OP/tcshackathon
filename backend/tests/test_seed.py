import re
from datetime import date

from app.db import connect
from app.seed import seed


def _seeded():
    conn = connect(":memory:")
    seed(conn)
    return conn


def test_seed_creates_50_customers_with_masked_fields():
    conn = _seeded()
    assert conn.execute("select count(*) from customers").fetchone()[0] == 50
    for (num,) in conn.execute("select number_masked from accounts"):
        assert re.fullmatch(r"XXXX\d{4}", num)
    assert conn.execute("select count(*) from customers where consent_personalization=0").fetchone()[0] >= 1
    sav = conn.execute("select id from accounts where type='savings'").fetchall()
    for (aid,) in sav:
        rows = conn.execute("select date from transactions where account_id=? order by date", (aid,)).fetchall()
        assert len(rows) >= 60
        span = (date.fromisoformat(rows[-1][0][:10]) - date.fromisoformat(rows[0][0][:10])).days
        assert span >= 150
    c1 = conn.execute("select * from customers where id='CUST001'").fetchone()
    assert c1["preferred_language"] == "en" and c1["monthly_income"] >= 60000 and c1["consent_personalization"] == 1
    assert conn.execute("select consent_personalization from customers where id='CUST004'").fetchone()[0] == 0


def test_seed_is_deterministic():
    a = [tuple(r) for r in _seeded().execute("select id, balance from accounts order by id")]
    b = [tuple(r) for r in _seeded().execute("select id, balance from accounts order by id")]
    assert a == b
