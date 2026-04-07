# src/explosionsschutz/services/ex_doc_prefill.py
"""
AI prefill service for Ex-Dokument fields.

Delegates to iil-fieldprefill shared package (ADR-107).
Domain-specific: action codes, source labels, scope.

Used by: doc_template_views.instance_llm_prefill
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Action codes for aifw model routing (quality_level differentiation)
ACTION_EX_DOC_PREFILL = "ex_doc_prefill"
ACTION_EX_DOC_PREFILL_TABLE = "ex_doc_prefill_table"

# Scope for fieldprefill system prompt (registered in ExplosionsschutzConfig.ready())
PREFILL_SCOPE = "explosionsschutz.ex_doc"


def prefill_ex_doc_field(
    *,
    field_key: str,
    llm_hint: str,
    ai_sources: list[str],
    tenant_id: str,
    instance: Any = None,
    existing_values: dict | None = None,
    extracted_texts: list[str] | None = None,
    field_type: str = "textarea",
) -> str:
    """AI-prefill a single Ex-Dokument field via iil-fieldprefill.

    Args:
        field_key: Field identifier (e.g. "geltungsbereich")
        llm_hint: Template-defined AI prompt for this field
        ai_sources: Source type keys (e.g. ["sds", "zonenplan"])
        tenant_id: Tenant UUID string
        instance: ExDocInstance (optional, for retriever context)
        existing_values: Already filled field values dict
        extracted_texts: Pre-extracted reference documents
        field_type: "textarea", "table", "text" for action routing

    Returns:
        Generated text content for the field.
    """
    from fieldprefill import prefill_field

    from explosionsschutz.ex_doc_constants import ai_source_full_labels

    _src_labels = ai_source_full_labels()
    source_type_names = [
        _src_labels.get(s, s) for s in ai_sources
    ]

    action_code = (
        ACTION_EX_DOC_PREFILL_TABLE
        if field_type == "table"
        else ACTION_EX_DOC_PREFILL
    )

    result = prefill_field(
        field_key=field_key,
        prompt=llm_hint,
        action_code=action_code,
        max_tokens=500,
        sources=ai_sources,
        context=existing_values,
        scope=PREFILL_SCOPE,
        tenant_id=tenant_id,
        instance=instance,
        extracted_texts=extracted_texts,
        source_type_names=source_type_names,
        response_format="table" if field_type == "table" else "text",
    )

    if result.error:
        raise RuntimeError(f"LLM prefill failed: {result.error}")

    logger.info(
        "Ex-Doc prefill '%s': %d tokens (model=%s, %dms)",
        field_key,
        result.tokens_used,
        result.model or "unknown",
        result.latency_ms,
    )
    return result.content
