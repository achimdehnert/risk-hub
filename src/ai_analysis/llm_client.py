"""LLM client for AI-assisted hazard analysis — powered by iil-aifw."""

import logging
from typing import Any
from uuid import UUID

from aifw.service import LLMResult, completion, sync_completion

logger = logging.getLogger(__name__)

ACTION_HAZARD_ANALYSIS = "hazard_analysis"
ACTION_SUBSTANCE_RISK = "substance_risk"


async def llm_complete(
    prompt: str,
    system: str = "",
    action_code: str = ACTION_HAZARD_ANALYSIS,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    tenant_id: UUID | str | None = None,
    object_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Async LLM completion via aifw — DB-driven model routing."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    result: LLMResult = await completion(
        action_code=action_code,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tenant_id=tenant_id,
        object_id=object_id,
        metadata=metadata,
    )

    if not result.success:
        raise RuntimeError(f"LLM call failed: {result.error}")

    return result.content


def llm_complete_sync(
    prompt: str,
    system: str = "",
    action_code: str = ACTION_HAZARD_ANALYSIS,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    tenant_id: UUID | str | None = None,
    object_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Synchronous LLM completion via aifw — safe in Django views + Celery."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    result: LLMResult = sync_completion(
        action_code=action_code,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tenant_id=tenant_id,
        object_id=object_id,
        metadata=metadata,
    )

    if not result.success:
        raise RuntimeError(f"LLM call failed: {result.error}")

    return result.content
