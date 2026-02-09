"""LLM Gateway client for AI-assisted hazard analysis."""

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = getattr(settings, "LLM_GATEWAY_TIMEOUT", 120)


async def llm_complete(
    prompt: str,
    system: str = "",
    model: str = "default",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Send a completion request to the LLM Gateway."""
    url = f"{settings.LLM_GATEWAY_URL}/v1/chat/completions"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]


def llm_complete_sync(
    prompt: str,
    system: str = "",
    model: str = "default",
    temperature: float = 0.3,
    max_tokens: int = 2000,
) -> str:
    """Synchronous version of llm_complete."""
    url = f"{settings.LLM_GATEWAY_URL}/v1/chat/completions"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data["choices"][0]["message"]["content"]
