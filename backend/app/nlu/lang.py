import re

HINGLISH = {"mera", "meri", "mere", "kitna", "kitni", "kitne", "hai", "hain", "kya", "mujhe", "chahiye", "paise", "paisa",
            "batao", "karo", "kar", "nahi", "ka", "ki", "ko", "se", "pe", "bhai", "yaar", "kaise", "kab", "kaha", "kahan",
            "dikhao", "bhejo", "milega", "sakta", "sakti", "hoon", "kharcha", "kharch", "saal", "lakh", "abhi", "aur", "wala",
            "ke", "dikha", "bhej", "kaunse", "kaunsa", "kaun", "gaye", "gaya", "gayi", "hisaab", "hisab", "milte", "milta",
            "liye", "karna", "karni", "karne", "bhul", "bhool", "hu", "banau", "banaye", "tha", "thi", "aaya", "aayi", "ji",
            "kholne", "kholna", "din", "kharche", "kharchey", "saare", "sab", "kidhar", "mujhko", "humko", "apna", "apne",
            "chahte", "chahta", "chahti", "dena", "lena", "wapas", "kyun", "kyu", "batado", "bata", "padhai", "bhai",
            "mummy", "papa", "dukandaar", "zyada", "jyada", "kam", "kitne", "paisa", "rupay", "rupaye", "byaj", "naya", "nayi"}
AMBIGUOUS = {"do", "par", "ne", "hu", "ji", "sab", "kam", "din", "bata"}
NAMES = {"en": "English", "hi": "Hindi (Devanagari script)", "kn": "Kannada (Kannada script)",
         "hinglish": "Hinglish (Hindi written in Latin script, casual)"}


def detect_language(text: str) -> str:
    if re.search(r"[ಀ-೿]", text):
        return "kn"
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    words = re.findall(r"[a-zA-Z]+", text.lower())
    strong = sum(w in HINGLISH and w not in AMBIGUOUS for w in words)
    weak = sum(w in AMBIGUOUS for w in words)
    return "hinglish" if strong >= 2 or (strong == 1 and (weak >= 1 or len(words) <= 4)) else "en"
