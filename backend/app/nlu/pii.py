import re

# order matters: longest / most specific first
PATTERNS = [
    ("[CARD]", re.compile(r"\b(?:\d[ -]?){15,18}\d\b")),
    ("[AADHAAR]", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("[ACCOUNT]", re.compile(r"\b\d{9,14}\b")),
    ("[PAN]", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)),
    ("[PHONE]", re.compile(r"(?:\+91[ -]?)?\b[6-9]\d{9}\b")),
    ("[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("[CVV/OTP]", re.compile(r"\b(?:cvv|otp|pin)\s*(?:is|:)?\s*\d{3,6}\b", re.I)),
]


def redact(text: str) -> tuple[str, int]:
    n = 0
    for token, pat in PATTERNS:
        text, k = pat.subn(token, text)
        n += k
    return text, n
