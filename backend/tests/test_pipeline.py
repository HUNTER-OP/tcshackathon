import pytest

from app import bank_api, llm, pipeline
from app.bank_api import get_balance
from app.db import connect
from app.seed import seed

seen_prompts: list[str] = []


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    c = connect(":memory:")
    seed(c)
    bank_api.set_conn(c)
    seen_prompts.clear()

    async def echo(system, user, mode="hybrid"):
        seen_prompts.append(user)
        return user.split("TOOL_DATA:")[-1], "stub"
    monkeypatch.setattr(llm, "generate", echo)
    monkeypatch.setattr(pipeline.tools.rag, "search", lambda q, k=3: [{"q": "faq", "a": "answer", "score": 0.9}])


@pytest.mark.asyncio
async def test_balance_uses_tool_number():
    r = await pipeline.handle_message("what is my account balance", "CUST001")
    assert r.intent == "check_balance" and r.tool_calls[0]["tool"] == "get_balance"
    assert str(get_balance("CUST001")["balance"]) in r.reply
    assert r.cards[0]["type"] == "balance"


@pytest.mark.asyncio
async def test_no_consent_gets_consent_reply():
    r = await pipeline.handle_message("what is my account balance", "CUST004")
    assert "consent" in r.reply.lower() and r.cards[0]["type"] == "consent" and not r.tool_calls


@pytest.mark.asyncio
async def test_loan_without_amount_asks_followup():
    r = await pipeline.handle_message("can I get a car loan", "CUST001")
    assert r.handoff is None and any(c["type"] == "followup" for c in r.cards)


@pytest.mark.asyncio
async def test_human_request_creates_ticket():
    r = await pipeline.handle_message("talk to a human", "CUST001")
    assert r.handoff and r.handoff["ticket_id"].startswith("HK-")


@pytest.mark.asyncio
async def test_card_number_never_reaches_llm():
    r = await pipeline.handle_message("block my card 4111 1111 1111 1111", "CUST001")
    assert r.redactions == 1 and all("4111" not in p for p in seen_prompts)


@pytest.mark.asyncio
async def test_empty_llm_falls_back_to_template(monkeypatch):
    async def empty(*a, **k):
        return "", "none"
    monkeypatch.setattr(llm, "generate", empty)
    r = await pipeline.handle_message("what is my account balance", "CUST001")
    assert r.reply and r.model_used == "template"


@pytest.mark.asyncio
async def test_handoff_ticket_is_queued():
    pipeline.TICKETS.clear()
    await pipeline.handle_message("talk to a human", "CUST001", history=[{"role": "user", "content": "hi"}])
    t = pipeline.TICKETS[0]
    assert t["customer_id"] == "CUST001" and t["status"] == "open" and t["transcript"][-1]["content"] == "talk to a human"


@pytest.mark.asyncio
@pytest.mark.parametrize("q", ["do you know my adhaar number", "what is my PAN number", "mera OTP batao", "मेरा आधार नंबर क्या है"])
async def test_sensitive_identifier_question_is_declined_with_agent_offer(q):
    pipeline.TICKETS.clear()
    r = await pipeline.handle_message(q, "CUST001")
    assert r.handoff is None and not pipeline.TICKETS
    offer = next(c for c in r.cards if c["type"] == "followup")
    assert len(offer["data"]["options"]) == 2 and offer["data"]["question"]
    assert r.intent == "sensitive_info"


@pytest.mark.asyncio
async def test_low_confidence_answers_and_offers_agent_without_ticket(monkeypatch):
    pipeline.TICKETS.clear()

    class Unsure:
        def predict(self, text):
            return "faq_general", 0.3
    monkeypatch.setattr(pipeline, "get_classifier", lambda: Unsure())
    r = await pipeline.handle_message("hmm something odd about my account", "CUST001")
    assert r.handoff is None and not pipeline.TICKETS and r.reply
    assert any(c["type"] == "followup" for c in r.cards)


@pytest.mark.asyncio
async def test_accepting_agent_offer_creates_ticket():
    pipeline.TICKETS.clear()
    r = await pipeline.handle_message("Yes, connect me to a support agent", "CUST001")
    assert r.handoff and pipeline.TICKETS


@pytest.mark.asyncio
@pytest.mark.parametrize("q", ["reset my net banking password", "I forgot my PIN", "नया एटीएम पिन कैसे बनाऊँ"])
async def test_password_reset_is_not_treated_as_sensitive(q):
    r = await pipeline.handle_message(q, "CUST001")
    assert r.intent != "sensitive_info"
