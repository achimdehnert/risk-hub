"""
GBU Celery-Tasks (Phase 2D).

generate_documents_task — erzeugt GBU-PDF + BA-PDF nach Freigabe.

Wird nach approve_activity() per delay() angestoßen.
Nutzt shared_task → kein App-Import nötig.
"""
import logging
from uuid import UUID

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="gbu.tasks.generate_documents",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def generate_documents_task(activity_id: str, tenant_id: str) -> dict:
    """
    GBU-PDF und Betriebsanweisung (BA) für eine Tätigkeit erzeugen.

    Args:
        activity_id: str (UUID der HazardAssessmentActivity)
        tenant_id: str (UUID des Tenants)

    Returns:
        dict mit gbu_version_id und ba_version_id
    """
    from gbu.services.document_store import store_ba_pdf, store_gbu_pdf
    from gbu.services.pdf_service import render_ba_pdf, render_gbu_pdf

    act_uuid = UUID(activity_id)
    ten_uuid = UUID(tenant_id)

    try:
        gbu_bytes = render_gbu_pdf(act_uuid, ten_uuid)
        gbu_version = store_gbu_pdf(act_uuid, ten_uuid, gbu_bytes)
        logger.info("[GBU Task] GBU-PDF erzeugt: %s", gbu_version.id)
    except Exception as exc:
        logger.exception("[GBU Task] GBU-PDF fehlgeschlagen: %s", exc)
        raise generate_documents_task.retry(exc=exc)

    try:
        ba_bytes = render_ba_pdf(act_uuid, ten_uuid)
        ba_version = store_ba_pdf(act_uuid, ten_uuid, ba_bytes)
        logger.info("[GBU Task] BA-PDF erzeugt: %s", ba_version.id)
    except Exception as exc:
        logger.exception("[GBU Task] BA-PDF fehlgeschlagen: %s", exc)
        raise generate_documents_task.retry(exc=exc)

    return {
        "activity_id": activity_id,
        "gbu_version_id": str(gbu_version.id),
        "ba_version_id": str(ba_version.id),
    }
