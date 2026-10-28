"""Synthetic, anonymised bank data. Deterministic for a given seed."""
import random
from datetime import date, timedelta

from faker import Faker

from .db import connect

PERSONAS = {
    "CUST001": ("Ravi Kumar", "en", 85000, 768, 1, "Bengaluru"),
    "CUST002": ("Priya Sharma", "hi", 62000, 742, 1, "Lucknow"),
    "CUST003": ("Kiran Gowda", "kn", 54000, 721, 1, "Mysuru"),
    "CUST004": ("Arjun Mehta", "en", 70000, 700, 0, "Pune"),
    "CUST005": ("Anjali Verma", "hinglish", 48000, 689, 1, "Delhi"),
}

MERCHANTS = {
    "groceries": ["BigBasket", "DMart", "Reliance Fresh", "More Supermarket"],
    "food": ["Swiggy", "Zomato", "Cafe Coffee Day", "Domino's"],
    "shopping": ["Amazon", "Flipkart", "Myntra", "Croma"],
    "travel": ["Uber", "Ola", "IRCTC", "Namma Metro", "IndiGo"],
    "utilities": ["BESCOM Electricity", "Airtel Postpaid", "Jio Fiber", "BWSSB Water"],
    "upi_transfer": ["UPI to friend", "UPI to family", "UPI split bill"],
    "atm": ["ATM withdrawal"],
    "entertainment": ["Netflix", "BookMyShow", "Spotify"],
    "health": ["Apollo Pharmacy", "Practo", "Cult.fit"],
}
SPEND_RANGE = {
    "groceries": (300, 3500), "food": (150, 1200), "shopping": (500, 8000),
    "travel": (80, 6000), "upi_transfer": (200, 5000), "atm": (1000, 5000),
    "entertainment": (149, 799), "health": (200, 2500),
}


def _mask_digits(rng: random.Random) -> str:
    return f"XXXX{rng.randint(0, 9999):04d}"


def seed(conn, n_customers: int = 50, seed: int = 42) -> None:
    rng = random.Random(seed)
    fake = Faker("en_IN")
    fake.seed_instance(seed)
    conn.executescript("delete from customers; delete from accounts; delete from transactions; delete from cards; delete from loans;")
    end = date.today()
    start = end - timedelta(days=180)
    langs = ["en", "hi", "kn", "hinglish"]

    for i in range(1, n_customers + 1):
        cid = f"CUST{i:03d}"
        if cid in PERSONAS:
            name, lang, income, score, consent, city = PERSONAS[cid]
        else:
            name = fake.name()
            lang = rng.choice(langs)
            income = rng.randrange(18000, 250000, 1000)
            score = rng.randint(580, 840)
            consent = 0 if rng.random() < 0.1 else 1
            city = fake.city()
        conn.execute(
            "insert into customers values (?,?,?,?,?,?,?,?,?)",
            (cid, name, f"+91 XXXXXX{rng.randint(0, 9999):04d}", f"{name.split()[0].lower()[0]}***@mail.com",
             income, score, consent, lang, city),
        )

        # existing loan for some customers
        existing_emi = 0.0
        if cid != "CUST001" and rng.random() < 0.35:
            p = rng.randrange(100000, 1500000, 10000)
            existing_emi = round(p * 0.022, 2)
            conn.execute("insert into loans values (?,?,?,?,?,?,?)",
                         (f"LN{i:03d}", cid, rng.choice(["personal", "car", "home"]), p, existing_emi,
                          round(p * rng.uniform(0.3, 0.9), 2), rng.choice([8.5, 9.2, 11.5])))

        conn.execute("insert into cards values (?,?,?,?,?)", (f"CD{i:03d}D", cid, f"{rng.randint(0, 9999):04d}", "debit", "active"))
        if income >= 40000:
            conn.execute("insert into cards values (?,?,?,?,?)", (f"CD{i:03d}C", cid, f"{rng.randint(0, 9999):04d}", "credit", "active"))
        if rng.random() < 0.3 or cid == "CUST001":
            conn.execute("insert into accounts values (?,?,?,?,?,?)",
                         (f"AC{i:03d}F", cid, "fd", _mask_digits(rng), float(rng.randrange(50000, 1000000, 5000)), "INR"))

        aid = f"AC{i:03d}S"
        bal = float(rng.randrange(20000, 200000, 500))
        txns = []
        d = start
        n = 0
        while d <= end:
            day_events = []
            if d.day == 1:
                day_events.append(("salary", f"Salary credit - {fake.company()[:24]}", income))
            if d.day == 5:
                day_events.append(("rent", "Rent - house owner", -round(income * 0.25, -2)))
            if d.day == 10 and existing_emi:
                day_events.append(("emi", "Loan EMI auto-debit", -existing_emi))
            if d.day == 15:
                day_events.append(("utilities", rng.choice(MERCHANTS["utilities"]), -float(rng.randint(400, 3000))))
            for _ in range(rng.choice([0, 0, 1, 1, 1, 2])):
                cat = rng.choice(list(SPEND_RANGE))
                lo, hi = SPEND_RANGE[cat]
                scale = max(0.3, min(1.5, income / 90000))
                day_events.append((cat, rng.choice(MERCHANTS[cat]), -round(rng.randint(lo, hi) * scale)))
            for cat, desc, amt in day_events:
                bal = round(bal + amt, 2)
                n += 1
                t = f"{d.isoformat()}T{rng.randint(8, 22):02d}:{rng.randint(0, 59):02d}:00"
                txns.append((f"TX{i:03d}{n:05d}", aid, t, desc, cat, amt, bal))
            d += timedelta(days=1)
        conn.executemany("insert into transactions values (?,?,?,?,?,?,?)", txns)
        conn.execute("insert into accounts values (?,?,?,?,?,?)", (aid, cid, "savings", _mask_digits(rng), bal, "INR"))
    conn.commit()


if __name__ == "__main__":
    c = connect()
    seed(c)
    print("seeded", c.execute("select count(*) from transactions").fetchone()[0], "transactions")
