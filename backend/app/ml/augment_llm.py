"""Generate natural paraphrases per intent x language with the LLM chain -> data/processed/llm_paraphrases.jsonl"""
import asyncio
import json
import re
from pathlib import Path

from .. import llm
from ..config import settings
from .intents import UNIFIED_INTENTS

DESC = {
    "check_balance": "asking their current account/savings/FD balance",
    "transaction_history": "asking to see recent transactions, statement, mini statement, payments made",
    "spending_summary": "asking how much they spent, spending by category, where money went, expense analysis",
    "loan_eligibility": "asking if they can get/afford/qualify for a loan of some amount, max loan they can get",
    "emi_calculation": "asking EMI/monthly instalment for a loan amount, or their existing loan EMI/payment due",
    "interest_rates": "asking interest rates on FD, savings, RD, or a loan type",
    "loan_products": "asking which loans are offered, how to apply for a loan, documents needed for a loan",
    "card_block": "reporting lost/stolen/misused card and wanting it blocked or frozen",
    "card_activate": "wanting to activate a new card or enable online/international usage",
    "card_issue": "card not arrived, card not working, swallowed by ATM, need replacement or new card",
    "transfer_money": "wanting to send/transfer money to someone, or asking about a transfer status",
    "fees_charges": "asking about bank charges, fees, penalties, annual card fee",
    "atm_branch": "asking nearest ATM/branch, branch timings or address",
    "password_pin": "forgot or want to change PIN, UPI PIN, net banking password",
    "dispute_refund": "double charge, unrecognised payment, missing refund, ATM debited without cash",
    "human_agent": "wanting to talk to a human agent, customer care, complaint to a person, callback",
    "faq_general": "greetings, thanks, small talk, opening or closing an account, general bank policy questions",
}
LANG = {"en": "casual Indian English (abbreviations like a/c, rn, pls, some typos)",
        "hi": "Hindi in Devanagari script, natural spoken style (English banking words like EMI, FD, UPI allowed)",
        "kn": "Kannada in Kannada script, natural spoken style (English banking words allowed)",
        "hinglish": "Hinglish: Hindi written in Latin script, casual chat style"}
OUT = Path(settings.data_dir) / "processed" / "llm_paraphrases.jsonl"


async def _one(sem, intent, lang, n):
    prompt = (f"Write {n} different realistic messages a bank customer would type to a chatbot when {DESC[intent]}. "
              f"Language: {LANG[lang]}. Vary length, wording and politeness; include amounts or time periods in some. "
              f"Do not include personal numbers. Output one message per line, no numbering, no quotes, nothing else.")
    async with sem:
        text, model = await llm.generate("You generate training data for an Indian banking chatbot.", prompt, "hybrid")
    lines = [re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", l).strip().strip('"') for l in text.splitlines()]
    rows = [{"text": l, "label": intent, "lang": lang, "src": model} for l in lines if 3 <= len(l) <= 160]
    print(intent, lang, len(rows), model, flush=True)
    return rows


async def main(n: int = 25, concurrency: int = 6):
    llm.settings.llm_timeout_s = 40
    sem = asyncio.Semaphore(concurrency)
    jobs = [_one(sem, i, l, n) for i in UNIFIED_INTENTS for l in LANG]
    rows = [r for part in await asyncio.gather(*jobs) for r in part]
    with open(OUT, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(rows), OUT)


if __name__ == "__main__":
    asyncio.run(main())
