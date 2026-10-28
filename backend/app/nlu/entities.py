import re
from dataclasses import asdict, dataclass

LAKH = r"(?:lakh|lakhs|lac|lacs|l|लाख|ಲಕ್ಷ)"
CRORE = r"(?:crore|crores|cr|करोड़|ಕೋಟಿ)"
LOAN_WORDS = {
    "car": ["car", "gaadi", "gadi", "vehicle", "auto loan", "कार", "गाड़ी", "गाडी", "ಕಾರು", "ವಾಹನ"],
    "home": ["home", "house", "housing", "mortgage", "ghar", "घर", "होम", "ಮನೆ", "ಗೃಹ"],
    "education": ["education", "study", "student", "padhai", "एजुकेशन", "शिक्षा", "ಶಿಕ್ಷಣ"],
    "personal": ["personal", "पर्सनल", "व्यक्तिगत", "ವೈಯಕ್ತಿಕ"],
}
CATEGORIES = {
    "food": ["food", "khana", "swiggy", "zomato", "restaurant", "खाने", "खाना", "ಊಟ", "ಆಹಾರ"],
    "groceries": ["grocery", "groceries", "kirana", "राशन", "किराना", "ದಿನಸಿ"],
    "shopping": ["shopping", "amazon", "flipkart", "शॉपिंग", "ಶಾಪಿಂಗ್"],
    "travel": ["travel", "uber", "ola", "cab", "flight", "यात्रा", "ಪ್ರಯಾಣ"],
    "utilities": ["bill", "electricity", "utilities", "बिजली", "ಬಿಲ್"],
    "rent": ["rent", "kiraya", "किराया", "ಬಾಡಿಗೆ"],
    "atm": ["atm withdrawal", "cash withdrawal"],
    "entertainment": ["netflix", "movie", "entertainment", "मूवी", "ಸಿನಿಮಾ"],
}


@dataclass
class Entities:
    amount_inr: float | None = None
    tenure_months: int | None = None
    loan_type: str | None = None
    account_type: str | None = None
    category: str | None = None
    days: int | None = None
    card_last4: str | None = None

    def dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _amount(t: str) -> float | None:
    if m := re.search(rf"(\d+(?:\.\d+)?)\s*{CRORE}(?![a-z])", t):
        return _num(m.group(1)) * 1e7
    if m := re.search(rf"(\d+(?:\.\d+)?)\s*{LAKH}(?![a-z])", t):
        return _num(m.group(1)) * 1e5
    if m := re.search(r"(\d+(?:\.\d+)?)\s*k\b", t):
        return _num(m.group(1)) * 1e3
    if m := re.search(r"(?:₹|rs\.?|inr|rupees?)\s*(\d[\d,]*(?:\.\d+)?)", t):
        return _num(m.group(1))
    if m := re.search(r"\b(\d{1,3}(?:,\d{2,3})+|\d{4,8})\b(?!\s*(?:days?|din|दिन|ದಿನ|months?|mahine|years?|saal|साल|ವರ್ಷ))", t):
        return _num(m.group(1))
    return None


def extract_entities(text: str) -> Entities:
    t = text.lower()
    e = Entities(amount_inr=_amount(t))
    if m := re.search(r"(\d+)\s*(?:years?|yrs?|saal|sal|varsh|साल|वर्ष|ವರ್ಷ)", t):
        e.tenure_months = int(m.group(1)) * 12
    elif m := re.search(r"(\d+)\s*(?:months?|mahine|महीने|ತಿಂಗಳು)", t):
        e.tenure_months = int(m.group(1))
    for lt, words in LOAN_WORDS.items():
        if any(w in t for w in words):
            e.loan_type = lt
            break
    if any(w in t for w in ["fd", "fixed deposit", "एफडी", "ಎಫ್‌ಡಿ"]):
        e.account_type = "fd"
    elif any(w in t for w in ["current account"]):
        e.account_type = "current"
    elif any(w in t for w in ["saving", "सेविंग", "ಉಳಿತಾಯ"]):
        e.account_type = "savings"
    for cat, words in CATEGORIES.items():
        if any(w in t for w in words):
            e.category = cat
            break
    if m := re.search(r"(?:last|past|pichle|पिछले|ಕಳೆದ)\s*(\d+)\s*(?:days?|din|दिन|ದಿನ)", t):
        e.days = int(m.group(1))
    elif re.search(r"(?:last|past|pichle|पिछले|ಕಳೆದ)\s*(?:week|hafte|हफ्ते|ವಾರ)", t) or "this week" in t or "is hafte" in t:
        e.days = 7
    elif re.search(r"(?:last|past|pichle|पिछले|ಕಳೆದ)\s*(?:month|mahine|महीने|ತಿಂಗಳು)", t):
        e.days = 30
    if m := re.search(r"(?:ending|last 4|ending in|xxxx)\s*(\d{4})\b", t):
        e.card_last4 = m.group(1)
    return e
