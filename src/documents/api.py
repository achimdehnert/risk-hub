from datetime import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from documents.models import Document
from documents.services import get_document, list_documents
from permissions.authz import PermissionDenied

router = Router(tags=["documents"])


class DocumentOut(Schema):
    id: UUID
    tenant_id: UUID
    title: str
    category: str
    created_at: datetime


def _to_document_out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        tenant_id=d.tenant_id,
        title=d.title,
        category=d.category,
        created_at=d.created_at,
    )


@router.get("", response=list[DocumentOut])
def api_list_documents(request, limit: int = 100):
    try:
        return [_to_document_out(d) for d in list_documents(limit=limit)]
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))


@router.get("/{document_id}", response=DocumentOut)
def api_get_document(request, document_id: UUID):
    try:
        return _to_document_out(get_document(document_id=document_id))
    except PermissionDenied as exc:
        raise HttpError(403, str(exc))
    except Document.DoesNotExist:
        raise HttpError(404, "Not found")
