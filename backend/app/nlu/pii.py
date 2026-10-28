import re

# Secrets near their keyword: "otp maanga 739201", "CVV: 123", "pin is 4321" -> keep the words, mask the digits.
SECRET_CODE = re.compile(r"\b(otp|cvv|pin|mpin|upi\s*pin)\b(\D{0,20}?)(\d{3,8})\b", re.I)

# order matters: most specific first, so a phone isn't tagged as an account number
PATTERNS = [
    ("[CARD]", re.compile(r"\b(?:\d[ -]?){15,18}\d\b")),
    ("[AADHAAR]", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("[PHONE]", re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b")),
    ("[ACCOUNT]", re.compile(r"\b\d{9,18}\b")),
    ("[PAN]", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)),
    ("[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
]


def redact(text: str) -> tuple[str, int]:
    n = 0

    def _secret(m: re.Match) -> str:
        kind = "OTP" if m.group(1).lower() == "otp" else m.group(1).upper().replace(" ", "")
        return f"{m.group(1)}{m.group(2)}[{kind}]"

    text, k = SECRET_CODE.subn(_secret, text)
    n += k
    for token, pat in PATTERNS:
        text, k = pat.subn(token, text)
        n += k
    return text, n
