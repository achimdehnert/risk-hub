"""Substances service layer (ADR-041).

SDS upload, approval, and S3 operations.
Views must not call .create() / .save() / .get_or_create() directly.
"""

import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@transaction.atomic
def upload_sds_revision(
    tenant_id,
    substance,
    pdf_content: bytes,
    filename: str,
    content_type: str,
    revision_date: str,
    notes: str = "",
):
    """Upload SDS PDF to S3 and create Document + SdsRevision.

    Returns the new SdsRevision instance.
    Raises RuntimeError on S3 failure.
    """
    from common.s3 import s3_client
    from documents.models import Document, DocumentVersion

    from .models import SdsRevision

    sha256 = hashlib.sha256(pdf_content).hexdigest()
    s3_key = f"sds/{tenant_id}/{substance.pk}/{sha256[:16]}_{filename}"

    try:
        s3 = s3_client()
        s3.put_object(
            Bucket=getattr(settings, "S3_BUCKET", "risk-hub"),
            Key=s3_key,
            Body=pdf_content,
            ContentType=content_type or "application/pdf",
        )
    except Exception as exc:
        raise RuntimeError(f"S3-Upload fehlgeschlagen: {exc}") from exc

    doc, _ = Document.objects.get_or_create(
        tenant_id=tenant_id,
        title=f"SDB {substance.name}",
        defaults={"category": "sds"},
    )
    next_version = doc.versions.count() + 1
    doc_version = DocumentVersion.objects.create(
        tenant_id=tenant_id,
        document=doc,
        version=next_version,
        filename=filename,
        content_type=content_type or "application/pdf",
        size_bytes=len(pdf_content),
        sha256=sha256,
        s3_key=s3_key,
    )

    existing_count = SdsRevision.objects.filter(
        substance=substance,
    ).count()
    sds = SdsRevision.objects.create(
        tenant_id=tenant_id,
        substance=substance,
        revision_number=existing_count + 1,
        revision_date=revision_date,
        document=doc_version,
        status=SdsRevision.Status.DRAFT,
        notes=notes,
    )

    logger.info(
        "SDS revision %s uploaded for substance %s",
        sds.revision_number,
        substance.name,
    )
    return sds


def approve_sds_revision(sds, user_id=None):
    """Approve an SDS revision and archive previous ones.

    Returns the updated SdsRevision.
    """
    from .models import SdsRevision

    sds.substance.sds_revisions.filter(
        status=SdsRevision.Status.APPROVED,
    ).update(status=SdsRevision.Status.ARCHIVED)

    sds.status = SdsRevision.Status.APPROVED
    sds.approved_by = user_id
    sds.approved_at = timezone.now()
    sds.save()

    logger.info("SDS revision %s approved", sds.pk)
    return sds
