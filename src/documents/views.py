"""Document views — list, detail, upload, download."""

from uuid import UUID

from django.contrib import messages
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from documents.models import Document, DocumentVersion
from documents.services import download_url, upload_document


def document_list(request: HttpRequest) -> HttpResponse:
    """List all documents."""
    err = _require_tenant(request)
    if err:
        return err

    documents = (
        Document.objects.filter(tenant_id=request.tenant_id)
        .prefetch_related("versions")
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents},
    )


def document_detail(
    request: HttpRequest,
    document_id: UUID,
) -> HttpResponse:
    """View document details with version history."""
    err = _require_tenant(request)
    if err:
        return err

    document = get_object_or_404(
        Document.objects.prefetch_related("versions"),
        id=document_id,
        tenant_id=request.tenant_id,
    )
    versions = document.versions.order_by("-version")
    return render(
        request,
        "documents/document_detail.html",
        {"document": document, "versions": versions},
    )


def document_upload(request: HttpRequest) -> HttpResponse:
    """Upload a new document or new version."""
    err = _require_tenant(request)
    if err:
        return err

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "general")
        file = request.FILES.get("file")

        if not title or not file:
            messages.error(
                request, "Titel und Datei sind erforderlich."
            )
            return render(
                request,
                "documents/upload.html",
                {"categories": Document.CATEGORY_CHOICES},
            )

        try:
            version = upload_document(
                title=title,
                category=category,
                file=file,
                tenant_id=request.tenant_id,
                user_id=getattr(request.user, "id", None),
            )
            messages.success(
                request,
                f"{title} v{version.version} hochgeladen.",
            )
            return redirect(
                "documents:document_detail",
                document_id=version.document.id,
            )
        except Exception as exc:
            messages.error(request, f"Upload fehlgeschlagen: {exc}")

    return render(
        request,
        "documents/upload.html",
        {"categories": Document.CATEGORY_CHOICES},
    )


def document_download(
    request: HttpRequest,
    version_id: UUID,
) -> HttpResponse:
    """Redirect to presigned S3 download URL."""
    err = _require_tenant(request)
    if err:
        return err

    version = get_object_or_404(
        DocumentVersion,
        id=version_id,
        tenant_id=request.tenant_id,
    )
    url = download_url(version)
    return HttpResponseRedirect(url)
