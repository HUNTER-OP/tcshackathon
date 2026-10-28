import re

import pytest

from app.ml.intents import BANKING77_MAP, BITEXT_MAP, UNIFIED_INTENTS
from app.nlu.entities import extract_entities
from app.nlu.lang import detect_language
from app.nlu.pii import redact


@pytest.mark.parametrize("text,lang", [
    ("what is my account balance", "en"), ("mera balance kitna hai", "hinglish"),
    ("मेरा खाता बैलेंस बताओ", "hi"), ("ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು", "kn"), ("hello", "en"),
])
def test_detect_language(text, lang):
    assert detect_language(text) == lang


def test_redact_card_and_pan():
    out, n = redact("my card 4111 1111 1111 1111 and PAN ABCDE1234F")
    assert n == 2 and not re.search(r"\d{12,}", out.replace(" ", "")) and "ABCDE1234F" not in out


def test_redact_aadhaar_phone():
    out, n = redact("aadhaar 1234 5678 9012 phone 9876543210")
    assert n == 2 and "9876543210" not in out


@pytest.mark.parametrize("text,amt,loan,tenure", [
    ("can I afford a 5 lakh car loan for 5 years", 500000, "car", 60),
    ("₹2,50,000", 250000, None, None),
    ("mujhe 50k personal loan chahiye", 50000, "personal", None),
    ("ಮನೆ ಸಾಲ 30 ಲಕ್ಷ", 3000000, "home", None),
    ("5 लाख का कार लोन 3 साल", 500000, "car", 36),
])
def test_entities(text, amt, loan, tenure):
    e = extract_entities(text)
    assert e.amount_inr == amt and e.loan_type == loan and e.tenure_months == tenure


def test_entities_days():
    assert extract_entities("last 7 days").days == 7
    assert extract_entities("pichle mahine kitna kharcha").days == 30


def test_label_maps_cover_targets():
    assert set(BANKING77_MAP.values()) <= set(UNIFIED_INTENTS)
    assert set(BITEXT_MAP.values()) <= set(UNIFIED_INTENTS)
