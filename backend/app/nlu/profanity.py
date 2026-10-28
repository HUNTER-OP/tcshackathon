"""Profanity filter (English, Hinglish, Hindi, Kannada). Masks abusive words as *** everywhere text is stored or shown."""
import re

MASK = "***"

# whole-word Latin-script patterns (stems with suffixes), so "assessment" or "shitake" are left alone
_LATIN = [
    r"f+u+c*k+(?:ing|in|er|ers|ed|s)?", r"motherf\w*", r"f+\*+k\w*", r"wtf", r"stfu",
    r"shit(?:ty|s|head)?", r"bullshit", r"bitch(?:es|y)?", r"bastards?", r"assholes?", r"dickheads?",
    r"chutiy\w*", r"chutiye", r"madarchod\w*", r"maderchod\w*", r"b[eh]+n+chod\w*", r"bhenchod\w*",
    r"bhosd\w*", r"bsdk", r"gaand\w*", r"gandu", r"harami\w*", r"randi\w*", r"lavde\w*", r"lode\b",
    r"suleya\w*", r"bolimaga\w*",
]
_LATIN_RE = re.compile(r"(?<![A-Za-z])(?:" + "|".join(_LATIN) + r")(?![A-Za-z])", re.I)
# stems that never occur inside clean English words: mask the whole token, catching typos and run-ons ("fucknig", "tofucking")
_STEM_RE = re.compile(r"[A-Za-z]*(?:f+u+c+k+|f+u+k+(?:ing|in|er)|motherf|madarchod|b[eh]+n+chod|chutiy)[A-Za-z]*", re.I)
# Devanagari / Kannada words: no \b (it is unreliable around combining marks), match the word itself
_INDIC_RE = re.compile("|".join([
    "मादरचोद", "बहनचोद", "बहेनचोद", "चूतिया", "चुतिया", "भोसड़ी\\w*", "भोसडी\\w*", "गांडू", "गाण्डू", "हरामी", "रंडी",
    "ಸೂಳೆ\\w*", "ಬೋಳಿಮಗ\\w*", "ಬೋಳಿ ಮಗ", "ಹಲ್ಕಾ",
]))


def clean(text: str) -> tuple[str, int]:
    """Return text with abusive words masked, and how many were masked."""
    text, s = _STEM_RE.subn(MASK, text)
    text, a = _LATIN_RE.subn(MASK, text)
    text, b = _INDIC_RE.subn(MASK, text)
    return text, s + a + b


def has_profanity(text: str) -> bool:
    return bool(_STEM_RE.search(text) or _LATIN_RE.search(text) or _INDIC_RE.search(text))
