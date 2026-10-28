"""LLM providers with cloud -> local fallback. Every provider returns plain text or raises."""
import asyncio
import logging
import time
from typing import Literal

import httpx

from .config import settings

log = logging.getLogger("hisab.llm")
_gemini = None
_cooldown: dict[str, float] = {}  # provider -> unix time until which it is skipped (rate limited)
COOLDOWN_S = 30


def _gemini_client():
    global _gemini
    if _gemini is None:
        from google import genai
        _gemini = genai.Client(api_key=settings.gemini_api_key)
    return _gemini


async def gemini(system: str, user: str) -> str:
    from google.genai import types
    r = await _gemini_client().aio.models.generate_content(
        model=settings.gemini_model, contents=user,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.3, max_output_tokens=700))
    return (r.text or "").strip()


async def _openai_compat(url: str, key: str, model: str, system: str, user: str) -> str:
    body = {"model": model, "temperature": 0.3, "max_tokens": 1200,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(url, headers={"Authorization": f"Bearer {key}"}, json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


async def groq(system: str, user: str) -> str:
    return await _openai_compat("https://api.groq.com/openai/v1/chat/completions", settings.groq_api_key,
                                settings.groq_model, system, user)


async def openrouter(system: str, user: str) -> str:
    return await _openai_compat("https://openrouter.ai/api/v1/chat/completions", settings.openrouter_api_key,
                                settings.openrouter_model, system, user)


async def ollama(system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=120) as http:
        r = await http.post(f"{settings.ollama_url}/api/chat", json={
            "model": settings.ollama_model, "stream": False, "keep_alive": "30m",
            "options": {"temperature": 0.3, "num_predict": 500},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def _chain(mode: str) -> list[tuple[str, object, float]]:
    local = [(f"ollama:{settings.ollama_model}", ollama, settings.local_timeout_s)]
    if mode == "local":
        return local
    cloud = []
    if settings.gemini_api_key:
        cloud.append((f"gemini:{settings.gemini_model}", gemini, settings.llm_timeout_s))
    if settings.groq_api_key:
        cloud.append((f"groq:{settings.groq_model}", groq, settings.llm_timeout_s))
    if settings.openrouter_api_key:
        cloud.append((f"openrouter:{settings.openrouter_model}", openrouter, settings.llm_timeout_s))
    return cloud + local


async def generate(system: str, user: str, mode: Literal["hybrid", "local"] = "hybrid") -> tuple[str, str]:
    for name, fn, timeout in _chain(mode):
        if _cooldown.get(name, 0) > time.time():
            continue
        try:
            text = await asyncio.wait_for(fn(system, user), timeout=timeout)
            if text:
                return text, name
        except Exception as e:  # noqa: BLE001 - any provider failure falls through to the next
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate" in msg.lower():
                _cooldown[name] = time.time() + COOLDOWN_S
            log.warning("LLM %s failed: %s", name, msg[:200])
    return "", "none"


async def translate_to_english(text: str, mode: str = "hybrid") -> str:
    out, _ = await generate("Translate the user's banking message to English. Output only the translation, one line.",
                            text, mode)
    return out.splitlines()[0].strip() if out else text


async def warmup() -> None:
    """Load the local model into GPU memory so the first offline answer is fast."""
    try:
        await asyncio.wait_for(ollama("Reply OK.", "ping"), timeout=60)
    except Exception as e:  # noqa: BLE001
        log.warning("Ollama warmup failed: %s", e)
