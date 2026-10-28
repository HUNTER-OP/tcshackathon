"""The /chat pipeline: language -> PII firewall -> intent -> entities -> tools -> LLM reply, with a trace."""
import json
import random
import time

from pydantic import BaseModel

from . import bank_api, llm, metrics, tools
from .nlu.entities import extract_entities
from .nlu.intent import get_classifier
from .nlu.lang import NAMES, detect_language
from .nlu.pii import redact

HANDOFF_CONF = 0.45
TRANSLATE_CONF = 0.6
NEGATIVE = ["angry", "worst", "fraud", "useless", "frustrat", "bakwas", "bekar", "गुस्सा", "बेकार", "ಕೋಪ", "not helping", "nahi kar raha"]

SUGGEST = {
    "en": {"check_balance": ["Show my last 5 transactions", "How much did I spend last month?"],
           "transaction_history": ["Spending summary for last 30 days", "What is my balance?"],
           "spending_summary": ["Show my food transactions", "Can I afford a ₹5 lakh car loan?"],
           "loan_eligibility": ["What is the car loan interest rate?", "EMI for ₹5 lakh over 3 years"],
           "interest_rates": ["Senior citizen FD rates", "Can I afford a ₹10 lakh home loan?"],
           "_": ["What is my balance?", "Show my last 5 transactions", "FD interest rates"]},
    "hinglish": {"_": ["Mera balance kitna hai?", "Last 5 transactions dikhao", "5 lakh car loan mil sakta hai?"]},
    "hi": {"_": ["मेरा बैलेंस कितना है?", "पिछले 5 लेनदेन दिखाओ", "FD की ब्याज दर क्या है?"]},
    "kn": {"_": ["ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?", "ಕೊನೆಯ 5 ವಹಿವಾಟು ತೋರಿಸಿ", "FD ಬಡ್ಡಿ ದರ ಎಷ್ಟು?"]},
}
CONSENT_MSG = {
    "en": "I can't access your personal account data because personalised data consent is turned off. You can enable it in the app under Settings → Privacy, or visit a branch.",
    "hinglish": "Aapka personal data consent off hai, isliye main account details nahi dekh sakta. App me Settings → Privacy me consent on kar lijiye.",
    "hi": "आपकी व्यक्तिगत डेटा सहमति बंद है, इसलिए मैं आपके खाते की जानकारी नहीं देख सकता। कृपया ऐप में Settings → Privacy में सहमति चालू करें।",
    "kn": "ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಡೇಟಾ ಸಮ್ಮತಿ ಆಫ್ ಆಗಿದೆ, ಆದ್ದರಿಂದ ನಾನು ನಿಮ್ಮ ಖಾತೆ ಮಾಹಿತಿಯನ್ನು ನೋಡಲು ಸಾಧ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ಆ್ಯಪ್‌ನ Settings → Privacy ನಲ್ಲಿ ಸಮ್ಮತಿ ಆನ್ ಮಾಡಿ.",
}
HANDOFF_MSG = {
    "en": "I've raised ticket {t} and a banking specialist will call you shortly. I've shared a summary so you won't need to repeat yourself.",
    "hinglish": "Maine ticket {t} raise kar diya hai, ek specialist aapko jaldi call karenge. Summary share kar di hai, aapko dobara batana nahi padega.",
    "hi": "मैंने टिकट {t} बना दिया है, एक विशेषज्ञ जल्द ही आपको कॉल करेंगे। सारांश साझा कर दिया गया है।",
    "kn": "ನಾನು ಟಿಕೆಟ್ {t} ರಚಿಸಿದ್ದೇನೆ, ತಜ್ಞರು ಶೀಘ್ರದಲ್ಲೇ ನಿಮಗೆ ಕರೆ ಮಾಡುತ್ತಾರೆ. ಸಾರಾಂಶವನ್ನು ಹಂಚಿಕೊಳ್ಳಲಾಗಿದೆ.",
}

SYSTEM = """You are Hisab Kitab, a friendly, precise AI banking assistant for an Indian bank.
Rules:
- Reply ONLY in {language}. Match the customer's tone.
- Use ONLY facts and numbers present in TOOL_DATA or FAQ. Never invent balances, rates, amounts, dates or policies. If something is missing, say so or ask.
- Format money as Indian rupees with Indian digit grouping, e.g. ₹5,00,000.
- The app already shows a visual card with the full details, so give the key answer in 1-3 short sentences, then at most one helpful tip. Max 90 words. Markdown bold allowed, no tables.
- For loan eligibility, state eligible or not, the EMI, and the main reason in plain words.
- If TOOL_DATA says an amount is missing, ask for it in one short question (you may mention the maximum they can get).
- Never ask for card numbers, PINs, OTPs or passwords."""


class ChatResult(BaseModel):
    reply: str
    language: str
    intent: str
    confidence: float
    entities: dict
    tool_calls: list[dict]
    redactions: int
    redacted_text: str
    handoff: dict | None
    model_used: str
    latency_ms: int
    stages: list[dict]
    cards: list[dict]
    suggestions: list[str]


def _template_reply(intent: str, data: dict) -> str:
    """Deterministic English fallback so the demo never returns a blank answer."""
    if "balance" in data and "account" in data:
        return f"Your {data['account_type']} account {data['account']} balance is ₹{data['balance']:,.2f}."
    if intent in ("loan_eligibility", "emi_calculation") and "emi" in data:
        verdict = "eligible" if data["eligible"] else "not eligible"
        return f"You are {verdict} for a {data['product']} of ₹{data['requested_amount']:,.0f}. EMI: ₹{data['emi']:,.0f}/month at {data['rate']}% for {data['tenure_months']} months."
    if data.get("missing") == "amount":
        return f"How much would you like to borrow? You can get up to ₹{data['max_amount_you_can_get']:,.0f}."
    if "items" in data:
        return f"Here are your last {len(data['items'])} transactions."
    if "by_category" in data:
        return f"You spent ₹{data['total_debit']:,.0f} in the last {data['days']} days."
    if data.get("faq"):
        return data["faq"][0]["a"][:500]
    return "Here are the details you asked for."


def _sentiment(text: str) -> str:
    t = text.lower()
    return "negative" if any(w in t for w in NEGATIVE) or text.count("!") >= 2 else "neutral"


async def handle_message(text: str, customer_id: str = "CUST001", mode: str = "hybrid",
                         history: list[dict] | None = None) -> ChatResult:
    t0 = time.perf_counter()
    stages: list[dict] = []

    def stage(name: str, start: float, detail: str = "") -> float:
        now = time.perf_counter()
        stages.append({"name": name, "ms": round((now - start) * 1000, 1), "detail": detail})
        return now

    t = time.perf_counter()
    lang = detect_language(text)
    t = stage("language", t, lang)
    clean, n_red = redact(text)
    t = stage("privacy_filter", t, f"{n_red} redacted")

    clf = get_classifier()
    intent, conf = clf.predict(clean)
    query_en = clean
    t = stage("intent", t, f"{intent} {conf:.2f}")
    if lang != "en" and conf < TRANSLATE_CONF:
        query_en = await llm.translate_to_english(clean, mode)
        i2, c2 = clf.predict(query_en)
        if c2 > conf:
            intent, conf = i2, c2
        t = stage("translate_retry", t, f"{intent} {conf:.2f}")

    ents = extract_entities(clean)
    if query_en != clean:
        e2 = extract_entities(query_en)
        for k, v in e2.dict().items():
            if getattr(ents, k) is None:
                setattr(ents, k, v)
    t = stage("entities", t, json.dumps(ents.dict(), ensure_ascii=False))

    handoff = None
    cards: list[dict] = []
    calls: list[dict] = []
    data: dict = {}
    reply = ""
    model_used = "rules"

    if intent == "human_agent" or conf < HANDOFF_CONF:
        handoff = {"ticket_id": f"HK-{random.randint(10000, 99999)}",
                   "summary": f"Customer {customer_id} ({lang}) asked: \"{clean[:160]}\". Bot intent guess: {intent} ({conf:.0%}).",
                   "sentiment": _sentiment(text), "priority": "high" if _sentiment(text) == "negative" else "normal",
                   "reason": "customer requested a human" if intent == "human_agent" else "low confidence"}
        cards.append({"type": "handoff", "data": handoff})
        reply = HANDOFF_MSG[lang].format(t=handoff["ticket_id"])
        t = stage("handoff", t, handoff["ticket_id"])
    else:
        try:
            res = tools.run(intent, ents, customer_id, query_en)
            data, cards, calls = res["data"], res["cards"], res["calls"]
            t = stage("tools", t, ", ".join(c["tool"] for c in calls) or "none")
        except bank_api.ConsentError:
            cards.append({"type": "consent", "data": {"message": CONSENT_MSG[lang]}})
            reply = CONSENT_MSG[lang]
            t = stage("tools", t, "consent_required")
        if not reply:
            hist = "\n".join(f"{h['role']}: {h['content'][:300]}" for h in (history or [])[-4:])
            user = (f"CONVERSATION SO FAR:\n{hist or '(none)'}\n\nCUSTOMER MESSAGE: {clean}\n"
                    f"DETECTED INTENT: {intent}\nENTITIES: {json.dumps(ents.dict(), ensure_ascii=False)}\n"
                    f"TOOL_DATA: {json.dumps(data, ensure_ascii=False, default=str)[:6000]}")
            reply, model_used = await llm.generate(SYSTEM.format(language=NAMES[lang]), user, mode)
            if not reply:
                reply, model_used = _template_reply(intent, data), "template"
            t = stage("llm_reply", t, model_used)

    sugg = SUGGEST.get(lang, {})
    result = ChatResult(
        reply=reply, language=lang, intent=intent, confidence=round(conf, 4), entities=ents.dict(),
        tool_calls=calls, redactions=n_red, redacted_text=clean, handoff=handoff, model_used=model_used,
        latency_ms=round((time.perf_counter() - t0) * 1000), stages=stages, cards=cards,
        suggestions=sugg.get(intent) or sugg.get("_") or SUGGEST["en"]["_"])
    metrics.record(result)
    return result
