import pytest

from app import llm
from app.config import settings


async def _boom(*a):
    raise RuntimeError("down")


async def _ok(*a):
    return "local answer"


@pytest.mark.asyncio
async def test_cloud_failure_falls_back_to_ollama(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "x")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(llm, "gemini", _boom)
    monkeypatch.setattr(llm, "ollama", _ok)
    text, model = await llm.generate("s", "u", "hybrid")
    assert text == "local answer" and model.startswith("ollama")


@pytest.mark.asyncio
async def test_local_mode_never_calls_cloud(monkeypatch):
    called = []

    async def spy(*a):
        called.append(1)
        return "cloud"
    monkeypatch.setattr(settings, "gemini_api_key", "x")
    monkeypatch.setattr(llm, "gemini", spy)
    monkeypatch.setattr(llm, "groq", spy)
    monkeypatch.setattr(llm, "ollama", _ok)
    _, model = await llm.generate("s", "u", "local")
    assert not called and model.startswith("ollama")


@pytest.mark.asyncio
async def test_all_fail_returns_empty(monkeypatch):
    for name in ("gemini", "groq", "openrouter", "ollama"):
        monkeypatch.setattr(llm, name, _boom)
    assert await llm.generate("s", "u", "hybrid") == ("", "none")


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["gemini", "groq", "ollama"])
async def test_live_providers(provider):
    out = await getattr(llm, provider)("Reply with one word.", "Say hi")
    assert out


@pytest.mark.asyncio
async def test_rate_limited_provider_is_skipped(monkeypatch):
    calls = []

    async def limited(*a):
        calls.append(1)
        raise RuntimeError("429 RESOURCE_EXHAUSTED")
    monkeypatch.setattr(settings, "gemini_api_key", "x")
    monkeypatch.setattr(settings, "groq_api_key", "")
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    monkeypatch.setattr(llm, "gemini", limited)
    monkeypatch.setattr(llm, "ollama", _ok)
    monkeypatch.setattr(llm, "_cooldown", {})
    await llm.generate("s", "u")
    await llm.generate("s", "u")
    assert len(calls) == 1
