"""DSB Löschungsworkflow Views (Art. 17 DSGVO)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django_tenancy.module_access import require_module

from dsb.deletion_workflow import advance_workflow, send_initial_confirmation
from dsb.models.deletion_request import (
    DeletionRequest,
    DeletionRequestStatus,
    WORKFLOW_TRANSITIONS,
)


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


def _user_id(request: HttpRequest):
    u = getattr(request, "user", None)
    return u.pk if u and hasattr(u, "pk") else None


@login_required
@require_module("dsb")
def deletion_request_list(request: HttpRequest) -> HttpResponse:
    """Liste aller Löschanträge."""
    tid = _tenant_id(request)
    qs = DeletionRequest.objects.filter(tenant_id=tid).select_related("mandate")
    open_count = qs.filter(
        status__in=[
            DeletionRequestStatus.PENDING,
            DeletionRequestStatus.AUTH_SENT,
            DeletionRequestStatus.AUTH_RECEIVED,
            DeletionRequestStatus.DELETION_ORDERED,
            DeletionRequestStatus.DELETION_CONFIRMED,
            DeletionRequestStatus.NOTIFIED,
        ]
    ).count()
    return render(request, "dsb/deletion_request_list.html", {
        "rows": qs[:200],
        "open_count": open_count,
    })


@login_required
@require_module("dsb")
def deletion_request_create(request: HttpRequest) -> HttpResponse:
    """Neuen Löschantrag anlegen."""
    from dsb.forms_deletion import DeletionRequestForm
    tid = _tenant_id(request)
    if request.method == "POST":
        form = DeletionRequestForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.created_by_id = _user_id(request)
            obj.updated_by_id = _user_id(request)
            obj.status = DeletionRequestStatus.PENDING
            obj.save()
            send_initial_confirmation(obj)
            messages.success(request, f"Löschantrag für {obj.subject_name} angelegt. Bestätigungs-E-Mail wurde versendet.")
            return redirect("dsb:deletion-request-detail", pk=obj.pk)
    else:
        form = DeletionRequestForm(tenant_id=tid)
    return render(request, "dsb/deletion_request_form.html", {
        "form": form,
        "title": "Neuer Löschantrag (Art. 17 DSGVO)",
    })


@login_required
@require_module("dsb")
def deletion_request_detail(request: HttpRequest, pk) -> HttpResponse:
    """Detailansicht + Workflow-Steuerung."""
    tid = _tenant_id(request)
    obj = get_object_or_404(
        DeletionRequest.objects.select_related("mandate"),
        pk=pk, tenant_id=tid,
    )
    from dsb.models.document import DsbDocument
    next_steps = WORKFLOW_TRANSITIONS.get(obj.status, [])
    docs = DsbDocument.objects.filter(tenant_id=tid, ref_type="deletion", ref_id=obj.pk)
    return render(request, "dsb/deletion_request_detail.html", {
        "obj": obj,
        "next_steps": next_steps,
        "status_choices": DeletionRequestStatus,
        "docs": docs,
    })


@login_required
@require_module("dsb")
def deletion_request_advance(request: HttpRequest, pk) -> HttpResponse:
    """Workflow-Schritt ausführen (POST)."""
    if request.method != "POST":
        return redirect("dsb:deletion-request-detail", pk=pk)

    tid = _tenant_id(request)
    obj = get_object_or_404(DeletionRequest, pk=pk, tenant_id=tid)

    new_status = request.POST.get("new_status")
    notes = request.POST.get("notes", "").strip()
    send_mail = request.POST.get("send_mail", "1") == "1"

    allowed = [s.value for s in WORKFLOW_TRANSITIONS.get(obj.status, [])]
    if new_status not in allowed:
        messages.error(request, f"Ungültiger Übergang: {new_status}")
        return redirect("dsb:deletion-request-detail", pk=pk)

    advance_workflow(obj, new_status, notes=notes, send_mail=send_mail)

    label = DeletionRequestStatus(new_status).label
    mail_info = " E-Mail wurde versendet." if send_mail else ""
    messages.success(request, f"Status geändert zu: {label}.{mail_info}")
    return redirect("dsb:deletion-request-detail", pk=pk)
