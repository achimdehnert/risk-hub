"""DSB Datenpannen-Workflow Views (Art. 33 DSGVO)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django_tenancy.module_access import require_module

from dsb.breach_workflow import advance_breach_workflow, send_initial_breach_confirmation
from dsb.models.breach import Breach, BreachStatus, BREACH_TRANSITIONS


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
def breach_list(request: HttpRequest) -> HttpResponse:
    """Liste aller Datenpannen mit Workflow-Status."""
    tid = _tenant_id(request)
    qs = Breach.objects.filter(tenant_id=tid).select_related("mandate")
    open_count = qs.filter(is_open=True).count() if False else qs.exclude(
        workflow_status=BreachStatus.CLOSED
    ).count()
    overdue_count = sum(1 for b in qs if b.is_overdue)
    return render(request, "dsb/breach_list.html", {
        "rows": qs[:200],
        "open_count": open_count,
        "overdue_count": overdue_count,
    })


@login_required
@require_module("dsb")
def breach_create(request: HttpRequest) -> HttpResponse:
    """Neue Datenpanne erfassen."""
    from dsb.forms_breach import BreachCreateForm
    tid = _tenant_id(request)
    if request.method == "POST":
        form = BreachCreateForm(request.POST, tenant_id=tid)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tenant_id = tid
            obj.workflow_status = BreachStatus.REPORTED
            obj.created_by_id = _user_id(request)
            obj.save()
            form.save_m2m()
            send_initial_breach_confirmation(obj)
            messages.success(
                request,
                f"Datenpanne erfasst. "
                + (f"Bestätigungs-E-Mail an {obj.reported_by_email} gesendet." if obj.reported_by_email else "")
            )
            return redirect("dsb:breach-detail", pk=obj.pk)
    else:
        form = BreachCreateForm(tenant_id=tid)
    return render(request, "dsb/breach_form.html", {
        "form": form,
        "title": "Datenpanne erfassen (Art. 33 DSGVO)",
    })


@login_required
@require_module("dsb")
def breach_detail(request: HttpRequest, pk) -> HttpResponse:
    """Detailansicht + Workflow-Steuerung."""
    tid = _tenant_id(request)
    obj = get_object_or_404(
        Breach.objects.select_related("mandate").prefetch_related("affected_categories"),
        pk=pk, tenant_id=tid,
    )
    from dsb.models.document import DsbDocument
    next_steps = BREACH_TRANSITIONS.get(obj.workflow_status, [])
    docs = DsbDocument.objects.filter(tenant_id=tid, ref_type="breach", ref_id=obj.pk)
    return render(request, "dsb/breach_detail.html", {
        "obj": obj,
        "next_steps": next_steps,
        "status_choices": BreachStatus,
        "docs": docs,
    })


@login_required
@require_module("dsb")
def breach_advance(request: HttpRequest, pk) -> HttpResponse:
    """Workflow-Schritt ausführen (POST)."""
    if request.method != "POST":
        return redirect("dsb:breach-detail", pk=pk)

    tid = _tenant_id(request)
    obj = get_object_or_404(Breach, pk=pk, tenant_id=tid)

    new_status = request.POST.get("new_status")
    notes = request.POST.get("notes", "").strip()
    authority_name = request.POST.get("authority_name", "").strip()
    authority_reference = request.POST.get("authority_reference", "").strip()
    send_mail = request.POST.get("send_mail", "1") == "1"

    allowed = [s.value for s in BREACH_TRANSITIONS.get(obj.workflow_status, [])]
    if new_status not in allowed:
        messages.error(request, f"Ungültiger Übergang: {new_status}")
        return redirect("dsb:breach-detail", pk=pk)

    advance_breach_workflow(
        obj, new_status,
        notes=notes,
        authority_name=authority_name,
        authority_reference=authority_reference,
        send_mail=send_mail,
    )

    label = BreachStatus(new_status).label
    mail_info = " E-Mail wurde versendet." if send_mail and obj.reported_by_email else ""
    messages.success(request, f"Status: {label}.{mail_info}")
    return redirect("dsb:breach-detail", pk=pk)
