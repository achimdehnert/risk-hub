from __future__ import annotations

import logging

from .models import IntakeUpload, IntakeResult
from .registry import get_handler, suggested_for

logger = logging.getLogger(__name__)


def ingest_file(upload: IntakeUpload) -> None:
    """
    Phase 1: Extrahiert Text + erkennt Dokumenttyp via iil-ingest.
    Setzt suggested_targets via Cerebras LLM (aifw section_hint / intake_routing).
    Speichert Ergebnis in upload.
    """
    try:
        from ingest import IngestPipeline  # iil-ingest (ADR-170)

        with upload.file.open("rb") as f:
            raw = f.read()

        doc = IngestPipeline().run(raw, upload.original_filename)
        upload.doc_type = doc.doc_type or "UNKNOWN"
        upload.doc_type_confidence = doc.confidence or "LOW"
        upload.extracted_text = doc.content.text or ""
    except ImportError:
        logger.warning("iil-ingest not available — skipping extraction")
        upload.doc_type = "UNKNOWN"
        upload.doc_type_confidence = "LOW"
        upload.extracted_text = ""

    upload.suggested_targets = suggested_for(upload.doc_type)
    upload.save(update_fields=[
        "doc_type", "doc_type_confidence", "extracted_text",
        "suggested_targets", "updated_at",
    ])


def route(upload: IntakeUpload) -> list[IntakeResult]:
    """
    Phase 2: Routing zu den vom Nutzer ausgewählten Handlers.
    Gibt Liste der IntakeResult-Objekte zurück.
    """
    upload.status = IntakeUpload.STATUS_PROCESSING
    upload.save(update_fields=["status", "updated_at"])

    results: list[IntakeResult] = []
    for target_code in upload.selected_targets:
        handler = get_handler(target_code)
        if handler is None:
            logger.warning("no handler registered for target_code=%s", target_code)
            continue
        try:
            result = handler.run(upload)
        except Exception as exc:
            logger.exception("handler %s failed for upload %s", target_code, upload.pk)
            result = IntakeResult(
                upload=upload,
                target_code=target_code,
                status=IntakeResult.STATUS_ERROR,
                error_message=str(exc),
            )
            result.save()
        results.append(result)

    upload.status = (
        IntakeUpload.STATUS_DONE
        if results and all(r.status == IntakeResult.STATUS_OK for r in results)
        else IntakeUpload.STATUS_ERROR
    )
    upload.save(update_fields=["status", "updated_at"])
    return results
