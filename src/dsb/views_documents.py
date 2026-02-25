"""DSB Dokument-Upload Views."""

import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django_tenancy.module_access import require_module

from dsb.models import Mandate
from dsb.models.document import DsbDocument


def _tenant_id(request: HttpRequest):
    tid = getattr(request, "tenant_id", None)
    if tid is not None:
        return tid
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        try:
            from django_tenancy.models import Membership
            m = (
                Membership.objects
                .filter(user=user)
                .select_related("organization")
                .order_by("created_at")
                .first()
            )
            if m and m.organization.is_active:
                return m.organization.tenant_id
        except Exception:
            pass
    return None


def _user_id(request):
    u = getattr(request, "user", None)
    return u.pk if u and hasattr(u, "pk") else None


@login_required
@require_module("dsb")
def document_list(request: HttpRequest) -> HttpResponse:
    """Alle DSB-Dokumente des Tenants."""
    tid = _tenant_id(request)
    ref_type = request.GET.get("ref_type", "")
    ref_id = request.GET.get("ref_id", "")

    qs = DsbDocument.objects.filter(tenant_id=tid).select_related("mandate")
    if ref_type:
        qs = qs.filter(ref_type=ref_type)
    if ref_id:
        qs = qs.filter(ref_id=ref_id)

    return render(request, "dsb/document_list.html", {
        "docs": qs[:200],
        "ref_type": ref_type,
        "ref_id": ref_id,
        "ref_type_choices": DsbDocument.RefType.choices,
    })


@login_required
@require_module("dsb")
def document_upload(request: HttpRequest) -> HttpResponse:
    """Dokument hochladen (PDF, DOCX, etc.)."""
    tid = _tenant_id(request)
    uid = _user_id(request)

    ref_type = request.GET.get("ref_type", DsbDocument.RefType.GENERAL)
    ref_id = request.GET.get("ref_id", "")
    mandate_id = request.GET.get("mandate", "")

    mandates = Mandate.objects.filter(tenant_id=tid, status="active") if tid else Mandate.objects.none()
    selected_mandate = None
    if mandate_id:
        selected_mandate = mandates.filter(pk=mandate_id).first()
    elif mandates.count() == 1:
        selected_mandate = mandates.first()

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        doc_ref_type = request.POST.get("ref_type", DsbDocument.RefType.GENERAL)
        doc_ref_id = request.POST.get("ref_id", "").strip() or None
        doc_mandate_id = request.POST.get("mandate", "").strip() or None
        document_date = request.POST.get("document_date", "").strip() or None

        if not uploaded_file:
            messages.error(request, "Bitte eine Datei auswählen.")
        elif not title:
            messages.error(request, "Bitte eine Bezeichnung eingeben.")
        else:
            try:
                mandate = Mandate.objects.get(pk=doc_mandate_id, tenant_id=tid) if doc_mandate_id else None
            except Mandate.DoesNotExist:
                mandate = None

            mime, _ = mimetypes.guess_type(uploaded_file.name)
            doc = DsbDocument(
                tenant_id=tid,
                mandate=mandate,
                ref_type=doc_ref_type,
                ref_id=doc_ref_id if doc_ref_id else None,
                title=title,
                description=description,
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size,
                mime_type=mime or "",
                uploaded_by_id=uid,
            )
            if document_date:
                from datetime import datetime
                try:
                    doc.document_date = datetime.strptime(document_date, "%Y-%m-%d").date()
                except ValueError:
                    pass
            doc.file = uploaded_file
            doc.save()

            messages.success(request, f"Dokument '{title}' erfolgreich hochgeladen.")

            # Redirect back to ref object if provided
            next_url = request.POST.get("next", "")
            if next_url:
                return redirect(next_url)
            return redirect("dsb:document-list")

    return render(request, "dsb/document_upload.html", {
        "mandates": mandates,
        "selected_mandate": selected_mandate,
        "ref_type": ref_type,
        "ref_id": ref_id,
        "ref_type_choices": DsbDocument.RefType.choices,
    })


@login_required
@require_module("dsb")
def document_download(request: HttpRequest, pk) -> HttpResponse:
    """Dokument herunterladen (tenant-geschützt)."""
    tid = _tenant_id(request)
    doc = get_object_or_404(DsbDocument, pk=pk, tenant_id=tid)
    try:
        response = FileResponse(
            doc.file.open("rb"),
            content_type=doc.mime_type or "application/octet-stream",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{doc.original_filename or doc.title}"'
        )
        return response
    except FileNotFoundError:
        raise Http404("Datei nicht gefunden.")


@login_required
@require_module("dsb")
def document_delete(request: HttpRequest, pk) -> HttpResponse:
    """Dokument löschen (POST)."""
    if request.method != "POST":
        return redirect("dsb:document-list")
    tid = _tenant_id(request)
    doc = get_object_or_404(DsbDocument, pk=pk, tenant_id=tid)
    title = doc.title
    try:
        doc.file.delete(save=False)
    except Exception:
        pass
    doc.delete()
    messages.success(request, f"Dokument '{title}' gelöscht.")
    next_url = request.POST.get("next", "")
    return redirect(next_url or "dsb:document-list")
