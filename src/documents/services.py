from uuid import UUID

from common.context import get_context

from documents.models import Document
from permissions.authz import require_permission


def list_documents(limit: int = 100) -> list[Document]:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("documents.read")

    return list(
        Document.objects.filter(tenant_id=ctx.tenant_id)
        .order_by("-created_at")[:limit]
    )


def get_document(document_id: UUID) -> Document:
    ctx = get_context()
    if ctx.tenant_id is None:
        raise ValueError("Tenant required")

    require_permission("documents.read")

    return Document.objects.get(
        id=document_id,
        tenant_id=ctx.tenant_id,
    )
