"""Document views — list, detail, upload, download."""

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from documents.models import Document, DocumentVersion
from documents.services import download_url, upload_document


@login_required
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


@login_required
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


@login_required
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
            messages.error(request, "Titel und Datei sind erforderlich.")
            return render(
                request,
                "documents/upload.html",
                {"categories": Document.Category.choices},
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
        {"categories": Document.Category.choices},
    )


@login_required
def document_bulk_upload(request: HttpRequest) -> HttpResponse:
    """Bulk upload multiple documents with shared category."""
    err = _require_tenant(request)
    if err:
        return err

    if request.method == "POST":
        category = request.POST.get("category", "general")
        files = request.FILES.getlist("files")

        if not files:
            messages.error(request, "Keine Dateien ausgewählt.")
            return render(
                request,
                "documents/bulk_upload.html",
                {"categories": Document.Category.choices},
            )

        results = []
        for file in files:
            title = file.name.rsplit(".", 1)[0] if "." in file.name else file.name
            try:
                version = upload_document(
                    title=title,
                    category=category,
                    file=file,
                    tenant_id=request.tenant_id,
                    user_id=getattr(request.user, "id", None),
                )
                results.append({"name": file.name, "ok": True, "version": version})
            except Exception as exc:
                results.append({"name": file.name, "ok": False, "error": str(exc)})

        ok_count = sum(1 for r in results if r["ok"])
        fail_count = len(results) - ok_count

        if fail_count == 0:
            messages.success(request, f"{ok_count} Dokument(e) hochgeladen.")
        else:
            messages.warning(
                request,
                f"{ok_count} hochgeladen, {fail_count} fehlgeschlagen.",
            )

        if request.headers.get("HX-Request"):
            return render(
                request,
                "documents/partials/upload_results.html",
                {"results": results},
            )

        return redirect("documents:document_list")

    return render(
        request,
        "documents/bulk_upload.html",
        {"categories": Document.Category.choices},
    )


@login_required
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
