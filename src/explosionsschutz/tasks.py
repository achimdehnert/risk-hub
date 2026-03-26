"""Celery tasks for concept document processing (ADR-147).

Uses the reusable task factory from iil-concept-templates.
Only the risk-hub-specific parts are defined here:
- get_pdf_bytes: S3/MinIO download via documents app
- llm_fn: aifw.sync_completion wrapper
"""

import logging
from uuid import UUID

from concept_templates.contrib.django.tasks import make_extract_and_analyze_task

from explosionsschutz.models import ExConceptDocument

logger = logging.getLogger(__name__)

ACTION_CONCEPT_ANALYSIS = "concept_analysis"


def _llm_sync_wrapper(system_prompt: str, user_prompt: str) -> str:
    """Wire concept-templates analyzer to aifw.service.sync_completion."""
    from ai_analysis.llm_client import llm_complete_sync

    return llm_complete_sync(
        prompt=user_prompt,
        system=system_prompt,
        action_code=ACTION_CONCEPT_ANALYSIS,
        temperature=0.2,
        max_tokens=4000,
    )


def _get_pdf_bytes(concept_doc, tenant_id: UUID) -> bytes | None:
    """Download PDF from S3/MinIO using the linked Document."""
    from documents.models import Document

    doc = Document.objects.filter(
        tenant_id=tenant_id,
        concept_ref_id=concept_doc.concept_id,
        scope=concept_doc.scope or "explosionsschutz",
    ).first()

    if not doc:
        logger.warning("No Document for concept %s", concept_doc.concept_id)
        return None

    latest_version = doc.versions.order_by("-version").first()
    if not latest_version:
        logger.warning("No versions for document %s", doc.id)
        return None

    try:
        from django.conf import settings

        from common.s3 import s3_client

        client = s3_client()
        response = client.get_object(
            Bucket=settings.S3_BUCKET,
            Key=latest_version.s3_key,
        )
        return response["Body"].read()
    except Exception as exc:
        logger.warning("S3 download failed: %s", exc)
        return None


# ── Task (created via factory) ──────────────────────────────────
extract_and_analyze_task = make_extract_and_analyze_task(
    model_class=ExConceptDocument,
    get_pdf_bytes=_get_pdf_bytes,
    llm_fn=_llm_sync_wrapper,
    task_name="explosionsschutz.tasks.extract_and_analyze",
)
