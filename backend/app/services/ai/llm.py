"""Optional LLM providers with graceful fallback."""

import logging

import httpx

from app.config import settings
from app.core.http_timeouts import outbound_timeout

logger = logging.getLogger(__name__)


def resolve_provider() -> str:
    if not settings.ai_assistant_enabled:
        return "local"
    provider = (settings.ai_provider or "local").lower()
    if provider == "openai" and settings.openai_api_key:
        return "openai"
    if provider == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    if provider == "openai" and settings.openai_api_key:
        return "openai"
    if provider == "anthropic" and settings.anthropic_api_key:
        return "anthropic"
    return "local"


async def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    provider = resolve_provider()
    if provider == "local":
        return None
    try:
        if provider == "openai":
            return await _call_openai(system_prompt, user_prompt)
        if provider == "anthropic":
            return await _call_anthropic(system_prompt, user_prompt)
    except Exception as exc:
        logger.warning("LLM call failed, falling back to local: %s", exc)
    return None


async def _call_openai(system_prompt: str, user_prompt: str) -> str:
    async with httpx.AsyncClient(timeout=outbound_timeout()) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 800,
            },
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()


async def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    async with httpx.AsyncClient(timeout=outbound_timeout()) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 800,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        res.raise_for_status()
        return res.json()["content"][0]["text"].strip()
