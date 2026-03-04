"""
GBU-Dokumentenspeicherung (Phase 2D).

Speichert PDF-Bytes als DocumentVersion und verknüpft sie
mit der HazardAssessmentActivity.

Strategie: lokal via Django DEFAULT_FILE_STORAGE
(FileSystemStorage in dev, S3 in prod via django-storages).
"""
import hashlib
import logging
from uuid import UUID

from django.core.files.base import ContentFile
from django.db import transaction

logger = logging.getLogger(__name__)

_GBU_CATEGORY = "arbeitssicherheit"


@transaction.atomic
def store_gbu_pdf(
    activity_id: UUID,
    tenant_id: UUID,
    pdf_bytes: bytes,
) -> "DocumentVersion":  # noqa: F821
    """
    PDF-Bytes als DocumentVersion persistieren und in
    HazardAssessmentActivity.gbu_document verknüpfen.

    Returns: DocumentVersion
    """
    from documents.models import Document, DocumentVersion
    from gbu.models.activity import HazardAssessmentActivity

    activity = HazardAssessmentActivity.objects.select_for_update().get(
        id=activity_id, tenant_id=tenant_id
    )
    title = f"GBU – {activity.activity_description[:80]}"

    doc, _ = Document.objects.get_or_create(
        tenant_id=tenant_id,
        title=title,
        defaults={"category": _GBU_CATEGORY},
    )
    last = doc.versions.order_by("-version").first()
    next_v = (last.version + 1) if last else 1

    filename = f"gbu_{activity_id}_v{next_v}.pdf"
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    s3_key = f"tenants/{tenant_id}/gbu/{activity_id}/gbu_v{next_v}.pdf"

    _write_storage(s3_key, pdf_bytes, "application/pdf")

    version = DocumentVersion.objects.create(
        tenant_id=tenant_id,
        document=doc,
        version=next_v,
        filename=filename,
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        sha256=sha256,
        s3_key=s3_key,
    )

    activity.gbu_document = version
    activity.save(update_fields=["gbu_document", "updated_at"])

    logger.info(
        "[GBU] GBU-PDF gespeichert: %s v%d (%d bytes)",
        activity_id, next_v, len(pdf_bytes),
    )
    return version


@transaction.atomic
def store_ba_pdf(
    activity_id: UUID,
    tenant_id: UUID,
    pdf_bytes: bytes,
) -> "DocumentVersion":  # noqa: F821
    """
    Betriebsanweisung-PDF als DocumentVersion persistieren und
    in HazardAssessmentActivity.ba_document verknüpfen.

    Returns: DocumentVersion
    """
    from documents.models import Document, DocumentVersion
    from gbu.models.activity import HazardAssessmentActivity

    activity = HazardAssessmentActivity.objects.select_for_update().get(
        id=activity_id, tenant_id=tenant_id
    )
    title = f"BA – {activity.activity_description[:80]}"

    doc, _ = Document.objects.get_or_create(
        tenant_id=tenant_id,
        title=title,
        defaults={"category": _GBU_CATEGORY},
    )
    last = doc.versions.order_by("-version").first()
    next_v = (last.version + 1) if last else 1

    filename = f"ba_{activity_id}_v{next_v}.pdf"
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    s3_key = f"tenants/{tenant_id}/gbu/{activity_id}/ba_v{next_v}.pdf"

    _write_storage(s3_key, pdf_bytes, "application/pdf")

    version = DocumentVersion.objects.create(
        tenant_id=tenant_id,
        document=doc,
        version=next_v,
        filename=filename,
        content_type="application/pdf",
        size_bytes=len(pdf_bytes),
        sha256=sha256,
        s3_key=s3_key,
    )

    activity.ba_document = version
    activity.save(update_fields=["ba_document", "updated_at"])

    logger.info(
        "[GBU] BA-PDF gespeichert: %s v%d (%d bytes)",
        activity_id, next_v, len(pdf_bytes),
    )
    return version


def _write_storage(key: str, content: bytes, content_type: str) -> None:
    """
    Schreibt Bytes in DEFAULT_FILE_STORAGE.

    In Produktion: S3 via django-storages.
    In Entwicklung: MEDIA_ROOT/Dateisystem.
    """
    from django.core.files.storage import default_storage

    cf = ContentFile(content, name=key)
    if default_storage.exists(key):
        default_storage.delete(key)
    default_storage.save(key, cf)
