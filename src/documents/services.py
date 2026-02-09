"""Document service — CRUD, upload, download via S3."""

import hashlib
import logging
from uuid import UUID

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from common.context import get_context
from documents.models import Document, DocumentVersion
from permissions.authz import require_permission

logger = logging.getLogger(__name__)


def list_documents(limit: int = 100) -> list[Document]:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("documents.read")

    return list(
        Document.objects.filter(tenant_id=ctx.tenant_id)
        .prefetch_related("versions")
        .order_by("-created_at")[:limit]
    )


def get_document(document_id: UUID) -> Document:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("documents.read")

    return Document.objects.prefetch_related(
        "versions"
    ).get(
        id=document_id,
        tenant_id=ctx.tenant_id,
    )


@transaction.atomic
def upload_document(
    title: str,
    category: str,
    file: UploadedFile,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> DocumentVersion:
    """
    Upload a file and create or update a Document + Version.

    If a document with the same title exists for this tenant,
    a new version is created. Otherwise a new Document is created.
    """
    require_permission("documents.create")

    # Find or create the document
    doc, created = Document.objects.get_or_create(
        tenant_id=tenant_id,
        title=title,
        defaults={"category": category},
    )
    if not created and category:
        doc.category = category
        doc.save(update_fields=["category"])

    # Determine next version number
    last_version = (
        doc.versions.order_by("-version").first()
    )
    next_version = (last_version.version + 1) if last_version else 1

    # Read file content and compute hash
    content = file.read()
    sha256 = hashlib.sha256(content).hexdigest()

    # Build S3 key
    s3_key = (
        f"tenants/{tenant_id}/documents/"
        f"{doc.id}/v{next_version}/{file.name}"
    )

    # Upload to S3
    _upload_to_s3(s3_key, content, file.content_type)

    # Create version record
    version = DocumentVersion.objects.create(
        tenant_id=tenant_id,
        document=doc,
        version=next_version,
        filename=file.name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=sha256,
        s3_key=s3_key,
    )

    logger.info(
        "Uploaded document %s v%d (%d bytes, %s)",
        doc.title,
        next_version,
        len(content),
        sha256[:12],
    )
    return version


def download_url(version: DocumentVersion) -> str:
    """Generate a presigned download URL for a document version."""
    from common.s3 import s3_client

    client = s3_client()
    url = client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": version.s3_key,
        },
        ExpiresIn=3600,
    )
    return url


def _upload_to_s3(
    key: str,
    content: bytes,
    content_type: str,
) -> None:
    """Upload raw bytes to S3/MinIO."""
    from io import BytesIO

    from common.s3 import s3_client

    client = s3_client()
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=BytesIO(content),
        ContentLength=len(content),
        ContentType=content_type or "application/octet-stream",
    )
