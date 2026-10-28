"""Generate SYNTHETIC customer query logs (the brief's "simulated customer query logs in text format").
Usage: python generate_logs.py [--n 5000] [--days 30] [--seed 42] [--out-dir .]
Writes query_logs.txt (pipe-separated text) and query_logs.jsonl. Deterministic for a given seed; not real traffic.
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

LANG_MIX = {"en": 0.40, "hinglish": 0.25, "hi": 0.20, "kn": 0.15}

# Rough share of traffic per intent (sums to 1.0). human_agent + low-confidence fallbacks give ~6% handoffs.
INTENT_MIX = {
    "check_balance": 0.17, "transaction_history": 0.13, "spending_summary": 0.08, "loan_eligibility": 0.07,
    "emi_calculation": 0.05, "interest_rates": 0.07, "loan_products": 0.04, "card_block": 0.05,
    "card_activate": 0.03, "card_issue": 0.03, "transfer_money": 0.06, "fees_charges": 0.04,
    "atm_branch": 0.04, "password_pin": 0.04, "dispute_refund": 0.03, "human_agent": 0.03, "faq_general": 0.04,
}

CHANNEL_MIX = {"web": 0.55, "app": 0.30, "cli": 0.03, "voice": 0.12}

Q = {
    "check_balance": {
        "en": ["what's my balance", "check my account balance", "how much money do i have", "balance pls", "savings balance?"],
        "hinglish": ["mera balance kitna hai", "account mein kitne paise hai", "balance batao", "balance check karo"],
        "hi": ["मेरा बैलेंस कितना है?", "खाते में कितने पैसे हैं", "बैलेंस बताइए"],
        "kn": ["ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?", "ಖಾತೆಯಲ್ಲಿ ಎಷ್ಟು ಹಣ ಇದೆ", "balance eshtu ide"],
    },
    "transaction_history": {
        "en": ["show my last 5 transactions", "recent transactions", "what did i spend yesterday", "last 10 txns"],
        "hinglish": ["last 5 transactions dikhao", "kal kya kharcha hua", "recent transactions batao"],
        "hi": ["मेरे पिछले 5 लेनदेन दिखाओ", "हाल के ट्रांजैक्शन दिखाइए"],
        "kn": ["ಕೊನೆಯ 5 ವಹಿವಾಟುಗಳನ್ನು ತೋರಿಸಿ", "ಇತ್ತೀಚಿನ ವಹಿವಾಟು"],
    },
    "spending_summary": {
        "en": ["how much did i spend on food last month", "spending summary", "where is my money going"],
        "hinglish": ["is mahine kitna kharch kiya", "food pe kitna gaya last month"],
        "hi": ["पिछले महीने मैंने खाने पर कितना खर्च किया?", "मेरा खर्च कितना हुआ"],
        "kn": ["ಕಳೆದ ತಿಂಗಳು ಎಷ್ಟು ಖರ್ಚು ಮಾಡಿದೆ?", "ಊಟಕ್ಕೆ ಎಷ್ಟು ಖರ್ಚಾಯಿತು"],
    },
    "loan_eligibility": {
        "en": ["can i afford a 5 lakh car loan", "am i eligible for a home loan", "how much loan can i get"],
        "hinglish": ["kya main 5 lakh ka car loan afford kar sakta hoon", "home loan mil sakta hai kya"],
        "hi": ["क्या मुझे 10 लाख का होम लोन मिल सकता है?", "मैं कितना लोन ले सकता हूँ"],
        "kn": ["ನನಗೆ ಕಾರ್ ಸಾಲ ಸಿಗುತ್ತಾ?", "ಎಷ್ಟು ಸಾಲ ಸಿಗಬಹುದು"],
    },
    "emi_calculation": {
        "en": ["emi for 3 lakh personal loan for 2 years", "calculate emi 10 lakh 5 years"],
        "hinglish": ["2 lakh ka emi kitna hoga 3 saal ke liye", "emi batao 5 lakh 5 saal"],
        "hi": ["5 लाख के लोन की EMI कितनी होगी?", "ईएमआई कैलकुलेट करो"],
        "kn": ["5 ಲಕ್ಷ ಸಾಲಕ್ಕೆ EMI ಎಷ್ಟು?", "EMI eshtu aagutte"],
    },
    "interest_rates": {
        "en": ["what are fd rates", "home loan interest rate", "savings account interest"],
        "hinglish": ["fd ka rate kya hai", "home loan pe interest kitna hai"],
        "hi": ["एफडी पर ब्याज दर क्या है?", "होम लोन की ब्याज दर"],
        "kn": ["FD ಬಡ್ಡಿ ದರ ಎಷ್ಟು?", "ಗೃಹ ಸಾಲದ ಬಡ್ಡಿ ದರ"],
    },
    "loan_products": {
        "en": ["what loans do you offer", "types of loans available"],
        "hinglish": ["kaun kaun se loan milte hai", "loan options batao"],
        "hi": ["आपके पास कौन से लोन हैं?"],
        "kn": ["ಯಾವ ಸಾಲಗಳು ಲಭ್ಯವಿದೆ?"],
    },
    "card_block": {
        "en": ["block my card", "i lost my debit card", "card stolen block it now"],
        "hinglish": ["mera card block karo", "card kho gaya"],
        "hi": ["मेरा कार्ड ब्लॉक करो", "कार्ड खो गया है"],
        "kn": ["ನನ್ನ ಕಾರ್ಡ್ ಬ್ಲಾಕ್ ಮಾಡಿ", "ಕಾರ್ಡ್ ಕಳೆದುಹೋಗಿದೆ"],
    },
    "card_activate": {
        "en": ["activate my new card", "how to activate debit card"],
        "hinglish": ["naya card activate karna hai"],
        "hi": ["नया कार्ड कैसे एक्टिवेट करें"],
        "kn": ["ಹೊಸ ಕಾರ್ಡ್ ಆಕ್ಟಿವೇಟ್ ಮಾಡಿ"],
    },
    "card_issue": {
        "en": ["my card is not working", "card declined at shop", "new card not received"],
        "hinglish": ["card kaam nahi kar raha", "card decline ho gaya"],
        "hi": ["मेरा कार्ड काम नहीं कर रहा"],
        "kn": ["ಕಾರ್ಡ್ ಕೆಲಸ ಮಾಡುತ್ತಿಲ್ಲ"],
    },
    "transfer_money": {
        "en": ["send 5000 to my saved beneficiary", "transfer money to mom", "how to do neft"],
        "hinglish": ["5000 transfer karo", "paise bhejne hai"],
        "hi": ["5000 रुपये ट्रांसफर करो"],
        "kn": ["5000 ರೂಪಾಯಿ ಕಳುಹಿಸಿ"],
    },
    "fees_charges": {
        "en": ["what are imps charges", "atm withdrawal fee", "minimum balance penalty"],
        "hinglish": ["neft ka charge kitna hai", "atm fee kya hai"],
        "hi": ["आईएमपीएस का चार्ज कितना है?"],
        "kn": ["ATM ಶುಲ್ಕ ಎಷ್ಟು?"],
    },
    "atm_branch": {
        "en": ["nearest atm", "branch timings", "is the branch open on saturday"],
        "hinglish": ["paas mein atm kahan hai", "branch kab khulti hai"],
        "hi": ["नज़दीकी एटीएम कहाँ है?", "ब्रांच का समय क्या है"],
        "kn": ["ಹತ್ತಿರದ ATM ಎಲ್ಲಿದೆ?", "ಶಾಖೆ ಸಮಯ"],
    },
    "password_pin": {
        "en": ["forgot my net banking password", "reset atm pin", "change upi pin"],
        "hinglish": ["password bhool gaya", "pin reset karna hai"],
        "hi": ["पासवर्ड भूल गया", "पिन कैसे बदलें"],
        "kn": ["ಪಾಸ್ವರ್ಡ್ ಮರೆತಿದ್ದೇನೆ", "PIN ಬದಲಿಸಿ"],
    },
    "dispute_refund": {
        "en": ["money debited but transaction failed", "i want a refund", "wrong charge on my account"],
        "hinglish": ["paise kat gaye par payment fail", "refund chahiye"],
        "hi": ["पैसे कट गए लेकिन पेमेंट फेल हो गया"],
        "kn": ["ಹಣ ಕಡಿತವಾಯಿತು ಆದರೆ ಪಾವತಿ ವಿಫಲ"],
    },
    "human_agent": {
        "en": ["i want to talk to a human", "connect me to an agent", "this is useless, get me a person"],
        "hinglish": ["kisi insaan se baat karao", "agent se connect karo"],
        "hi": ["किसी इंसान से बात करवाइए"],
        "kn": ["ಮನುಷ್ಯರೊಂದಿಗೆ ಮಾತನಾಡಬೇಕು"],
    },
    "faq_general": {
        "en": ["documents needed for loan", "how is fd interest taxed", "can i prepay my loan"],
        "hinglish": ["loan ke liye kya documents chahiye", "fd pe tax lagta hai kya"],
        "hi": ["लोन के लिए कौन से दस्तावेज़ चाहिए?"],
        "kn": ["ಸಾಲಕ್ಕೆ ಯಾವ ದಾಖಲೆಗಳು ಬೇಕು?"],
    },
}

# Hour-of-day weights: peaks at 10-13h and 18-21h, quiet overnight.
HOUR_W = [0.2, 0.1, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.6, 2.2, 3.6, 4.0, 3.8, 3.4,
          2.6, 2.4, 2.3, 2.6, 3.5, 4.0, 3.9, 3.4, 1.6, 0.7]


def pick(rng: random.Random, mix: dict) -> str:
    return rng.choices(list(mix), weights=list(mix.values()))[0]


def latency(rng: random.Random, channel: str) -> float:
    base = rng.lognormvariate(0.75, 0.28)          # median about 2.1 s, mostly 1.5-3 s
    if rng.random() < 0.04:                       # long tail: LLM fallback / retries
        base += rng.uniform(3, 9)
    if channel == "voice":
        base += 0.4
    return round(max(0.3, base), 2)


def generate(n: int, days: int, seed: int, end: datetime) -> list[dict]:
    rng = random.Random(seed)
    start = end - timedelta(days=days)
    customers = [f"CUST{i:03d}" for i in range(1, 51)]
    # Demo personas mostly use their own language.
    pref = {"CUST001": "en", "CUST002": "hi", "CUST003": "kn", "CUST004": "en", "CUST005": "hinglish"}
    rows = []
    for _ in range(n):
        day = start + timedelta(days=rng.randrange(days))
        hour = rng.choices(range(24), weights=HOUR_W)[0]
        ts = day.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60), microsecond=0)
        cust = rng.choice(customers)
        lang = pref[cust] if cust in pref and rng.random() < 0.8 else pick(rng, LANG_MIX)
        intent = pick(rng, INTENT_MIX)
        channel = pick(rng, CHANNEL_MIX)
        text = rng.choice(Q[intent][lang])

        if intent == "human_agent":
            conf, status = round(rng.uniform(0.9, 1.0), 2), "handoff"
        else:
            conf = round(min(0.999, rng.betavariate(9, 1.2)), 2)
            if conf < 0.45 or rng.random() < 0.028:         # unsure, or customer escalated mid-chat
                status = "handoff"
            elif cust == "CUST004" and intent in ("check_balance", "transaction_history", "spending_summary"):
                status = "consent_refused"
            elif rng.random() < 0.025:
                status = "followup_asked"
            else:
                status = "resolved"
        rows.append({"ts": ts.isoformat(), "customer_id": cust, "channel": channel, "lang": lang, "text": text,
                     "intent": intent, "confidence": conf, "status": status, "latency_s": latency(rng, channel)})
    rows.sort(key=lambda r: r["ts"])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", default="2026-10-28T00:00:00", help="end of the window (fixed for determinism)")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent))
    a = ap.parse_args()

    rows = generate(a.n, a.days, a.seed, datetime.fromisoformat(a.end))
    out = Path(a.out_dir)
    with open(out / "query_logs.txt", "w", encoding="utf-8") as f:
        f.write("# SYNTHETIC query logs generated by generate_logs.py (seed=%d). Not real customer traffic.\n" % a.seed)
        f.write("# ts | customer_id | channel | lang | text | intent | confidence | status | latency\n")
        for r in rows:
            f.write(f'{r["ts"]} | {r["customer_id"]} | {r["channel"]} | {r["lang"]} | "{r["text"]}" | '
                    f'{r["intent"]} | {r["confidence"]:.2f} | {r["status"]} | {r["latency_s"]}s\n')
    with open(out / "query_logs.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    st = {}
    for r in rows:
        st[r["status"]] = st.get(r["status"], 0) + 1
    langs = {}
    for r in rows:
        langs[r["lang"]] = langs.get(r["lang"], 0) + 1
    lat = sorted(r["latency_s"] for r in rows)
    print(f"wrote {len(rows)} rows to {out / 'query_logs.txt'} and .jsonl")
    print("status:", {k: f"{v / len(rows):.1%}" for k, v in sorted(st.items())})
    print("lang:", {k: f"{v / len(rows):.1%}" for k, v in sorted(langs.items())})
    print(f"latency p50={lat[len(lat) // 2]}s p95={lat[int(len(lat) * 0.95)]}s max={lat[-1]}s")


if __name__ == "__main__":
    main()
