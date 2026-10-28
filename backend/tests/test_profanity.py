import pytest

from app import bank_api, llm, pipeline
from app.db import connect
from app.nlu.profanity import clean, has_profanity
from app.seed import seed


@pytest.mark.parametrize("text", [
    "I need my fucking balance", "FUCK this bank", "this is bullshit", "you are a bitch",
    "madarchod bank", "kya chutiya service hai", "behenchod card block karo", "यह मादरचोद बैंक है",
    "my fucknig card", "tell me tofucking balance", "fuckingrecent transactions",
])
def test_profanity_is_masked(text):
    out, n = clean(text)
    assert n >= 1 and "***" in out and not has_profanity(out)


@pytest.mark.parametrize("text", ["shitake mushrooms", "scunthorpe", "Dickens novel", "assessment", "class assignment"])
def test_clean_words_are_left_alone(text):
    assert clean(text) == (text, 0)


@pytest.fixture
def stub_llm(monkeypatch):
    c = connect(":memory:")
    seed(c)
    bank_api.set_conn(c)
    seen = []

    async def rude(system, user, mode="hybrid"):
        seen.append(user)
        return "Here is your fucking balance", "stub"
    monkeypatch.setattr(llm, "generate", rude)
    return seen


@pytest.mark.asyncio
async def test_reply_and_prompt_never_contain_profanity(stub_llm):
    r = await pipeline.handle_message("what is my fucking balance", "CUST001")
    assert not has_profanity(r.reply) and not has_profanity(r.redacted_text)
    assert all(not has_profanity(p) for p in stub_llm)


@pytest.mark.asyncio
async def test_abusive_handoff_ticket_is_masked_and_high_priority(stub_llm):
    pipeline.TICKETS.clear()
    r = await pipeline.handle_message("connect me to a human, fucking useless bot", "CUST001")
    assert r.handoff and r.handoff["sentiment"] == "negative" and r.handoff["priority"] == "high"
    assert not has_profanity(pipeline.TICKETS[0]["summary"])
    assert all(not has_profanity(m["content"]) for m in pipeline.TICKETS[0]["transcript"])


def test_faq_corpus_has_no_profanity():
    from app.rag import _corpus
    assert not any(has_profanity(d["q"]) or has_profanity(d["a"]) for d in _corpus())
