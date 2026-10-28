import re

HINGLISH = {"mera", "meri", "mere", "kitna", "kitni", "kitne", "hai", "hain", "kya", "mujhe", "chahiye", "paise", "paisa",
            "batao", "karo", "kar", "nahi", "ka", "ki", "ko", "se", "pe", "bhai", "yaar", "kaise", "kab", "kaha", "kahan",
            "dikhao", "bhejo", "milega", "sakta", "sakti", "hoon", "kharcha", "kharch", "saal", "lakh", "abhi", "aur", "wala"}
NAMES = {"en": "English", "hi": "Hindi (Devanagari script)", "kn": "Kannada (Kannada script)",
         "hinglish": "Hinglish (Hindi written in Latin script, casual)"}


def detect_language(text: str) -> str:
    if re.search(r"[ಀ-೿]", text):
        return "kn"
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = re.findall(r"[a-zA-Z]+", text.lower())
    hits = sum(w in HINGLISH for w in words)
    return "hinglish" if hits >= 2 or (hits == 1 and len(words) <= 3 and words and words[0] in HINGLISH) else "en"
