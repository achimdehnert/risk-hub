"""Celery tasks for concept document processing (ADR-147 Phase C).

extract_and_analyze_task — PDF-Extraktion + LLM-Strukturanalyse via aifw/promptfw
"""

import json
import logging
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)

ACTION_CONCEPT_ANALYSIS = "concept_analysis"


@shared_task(
    name="brandschutz.tasks.extract_and_analyze",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def extract_and_analyze_task(
    concept_doc_id: str,
    tenant_id: str,
) -> dict:
    """Extract text from uploaded PDF and run LLM structure analysis.

    Args:
        concept_doc_id: str (UUID of ConceptDocument)
        tenant_id: str (UUID of the tenant)

    Returns:
        dict with status, page_count, confidence
    """
    from brandschutz.models import ConceptDocument

    doc_id = UUID(concept_doc_id)
    tid = UUID(tenant_id)

    try:
        concept_doc = ConceptDocument.objects.get(
            id=doc_id,
            tenant_id=tid,
        )
    except ConceptDocument.DoesNotExist:
        logger.error("ConceptDocument %s not found for tenant %s", doc_id, tid)
        return {"status": "error", "error": "Document not found"}

    # ── Step 1: PDF Extraction ──────────────────────────────────
    if not concept_doc.has_extracted_text:
        concept_doc.status = "extracting"
        concept_doc.save(update_fields=["status"])

        try:
            pdf_bytes = _download_pdf_bytes(concept_doc, tid)
            if pdf_bytes is None:
                concept_doc.status = "failed"
                concept_doc.error_message = "PDF-Bytes konnten nicht geladen werden."
                concept_doc.save(update_fields=["status", "error_message"])
                return {"status": "error", "error": "No PDF bytes"}

            from concept_templates.extractor import extract_text_from_pdf

            result = extract_text_from_pdf(pdf_bytes)

            concept_doc.extracted_text = result.text
            concept_doc.page_count = result.page_count
            concept_doc.extraction_warnings = json.dumps(result.warnings)
            concept_doc.status = "extracted"
            concept_doc.save(
                update_fields=[
                    "extracted_text",
                    "page_count",
                    "extraction_warnings",
                    "status",
                ]
            )

            logger.info(
                "Extracted %d chars from %d pages for '%s'",
                len(result.text),
                result.page_count,
                concept_doc.title,
            )

        except Exception as exc:
            concept_doc.status = "failed"
            concept_doc.error_message = f"Extraktion fehlgeschlagen: {exc}"
            concept_doc.save(update_fields=["status", "error_message"])
            logger.warning("Extraction failed for %s: %s", doc_id, exc)
            raise

    # ── Step 2: LLM Structure Analysis ──────────────────────────
    if concept_doc.extracted_text and not concept_doc.has_template:
        concept_doc.status = "analyzing"
        concept_doc.save(update_fields=["status"])

        try:
            from concept_templates.analyzer import analyze_document_structure

            analysis = analyze_document_structure(
                text=concept_doc.extracted_text,
                scope=concept_doc.scope or "brandschutz",
                title=concept_doc.title,
                page_count=concept_doc.page_count or 0,
                llm_fn=_llm_sync_wrapper,
            )

            from concept_templates.export import to_json

            concept_doc.template_json = to_json(analysis.proposed_template)
            concept_doc.analysis_confidence = analysis.confidence
            concept_doc.status = "analyzed"
            concept_doc.save(
                update_fields=[
                    "template_json",
                    "analysis_confidence",
                    "status",
                ]
            )

            logger.info(
                "Analyzed '%s': confidence=%.2f, %d sections",
                concept_doc.title,
                analysis.confidence,
                len(analysis.proposed_template.sections),
            )

            return {
                "status": "analyzed",
                "page_count": concept_doc.page_count,
                "confidence": analysis.confidence,
                "sections": len(analysis.proposed_template.sections),
            }

        except Exception as exc:
            concept_doc.status = "failed"
            concept_doc.error_message = f"Analyse fehlgeschlagen: {exc}"
            concept_doc.save(update_fields=["status", "error_message"])
            logger.warning("Analysis failed for %s: %s", doc_id, exc)
            raise

    return {
        "status": concept_doc.status,
        "page_count": concept_doc.page_count,
    }


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


def _download_pdf_bytes(concept_doc, tenant_id: UUID) -> bytes | None:
    """Download the PDF from S3/MinIO using the linked Document."""
    from documents.models import Document

    # Find the Document linked via concept_ref_id
    doc = Document.objects.filter(
        tenant_id=tenant_id,
        concept_ref_id=concept_doc.concept_id,
        scope=concept_doc.scope or "brandschutz",
    ).first()

    if not doc:
        logger.warning("No Document found for concept %s", concept_doc.concept_id)
        return None

    latest_version = doc.versions.order_by("-version").first()
    if not latest_version:
        logger.warning("No versions for document %s", doc.id)
        return None

    # Download from S3
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
        logger.warning("S3 download failed for %s: %s", latest_version.s3_key, exc)
        return None
