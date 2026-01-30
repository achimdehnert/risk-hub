"""Document views."""

from uuid import UUID

from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, render

from documents.models import Document


def _require_tenant(request: HttpRequest) -> HttpResponse | None:
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is None:
        return HttpResponseForbidden("Missing tenant")
    return None


def document_list(request: HttpRequest) -> HttpResponse:
    """List all documents."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    documents = (
        Document.objects.filter(tenant_id=request.tenant_id)
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents},
    )


def document_detail(request: HttpRequest, document_id: UUID) -> HttpResponse:
    """View document details."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    document = get_object_or_404(
        Document,
        id=document_id,
        tenant_id=request.tenant_id,
    )
    return render(
        request,
        "documents/document_detail.html",
        {"document": document},
    )
