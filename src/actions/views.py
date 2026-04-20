# src/actions/views.py
"""Views für Maßnahmen-Tracking (UC-Q06)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ActionItemForm
from .models import ActionItem


def _tenant(request):
    return getattr(request, "tenant_id", None)


# ─── Dashboard ──────────────────────────────────────────────────────────────


@login_required
def dashboard(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    qs = ActionItem.objects.filter(tenant_id=tenant_id)
    open_count = qs.filter(status=ActionItem.Status.OPEN).count()
    in_progress_count = qs.filter(status=ActionItem.Status.IN_PROGRESS).count()
    completed_count = qs.filter(status=ActionItem.Status.COMPLETED).count()
    overdue_count = qs.filter(
        status__in=[ActionItem.Status.OPEN, ActionItem.Status.IN_PROGRESS],
        due_date__lt=timezone.now().date(),
    ).count()

    recent = qs.order_by("-updated_at")[:10]
    overdue = qs.filter(
        status__in=[ActionItem.Status.OPEN, ActionItem.Status.IN_PROGRESS],
        due_date__lt=timezone.now().date(),
    ).order_by("due_date")[:5]
    upcoming = qs.filter(
        status__in=[ActionItem.Status.OPEN, ActionItem.Status.IN_PROGRESS],
        due_date__gte=timezone.now().date(),
    ).order_by("due_date")[:5]

    return render(
        request,
        "actions/dashboard.html",
        {
            "open_count": open_count,
            "in_progress_count": in_progress_count,
            "completed_count": completed_count,
            "overdue_count": overdue_count,
            "recent": recent,
            "overdue": overdue,
            "upcoming": upcoming,
        },
    )


# ─── List ───────────────────────────────────────────────────────────────────


@login_required
def action_list(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")

    actions = ActionItem.objects.filter(tenant_id=tenant_id).order_by("-created_at")

    if status_filter:
        actions = actions.filter(status=status_filter)
    if priority_filter:
        actions = actions.filter(priority=int(priority_filter))

    return render(
        request,
        "actions/action_list.html",
        {
            "actions": actions,
            "current_status": status_filter,
            "current_priority": priority_filter,
        },
    )


# ─── Create ─────────────────────────────────────────────────────────────────


@login_required
def action_create(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = ActionItemForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.tenant_id = tenant_id
            action.save()
            messages.success(request, f"Maßnahme '{action.title}' angelegt.")
            return redirect("actions:action-detail", pk=action.pk)
    else:
        form = ActionItemForm()

    return render(
        request,
        "actions/action_form.html",
        {
            "form": form,
            "title": "Neue Maßnahme",
        },
    )


# ─── Detail ─────────────────────────────────────────────────────────────────


@login_required
def action_detail(request, pk):
    tenant_id = _tenant(request)
    action = get_object_or_404(ActionItem, pk=pk, tenant_id=tenant_id)
    return render(request, "actions/action_detail.html", {"action": action})


# ─── Edit ───────────────────────────────────────────────────────────────────


@login_required
def action_edit(request, pk):
    tenant_id = _tenant(request)
    action = get_object_or_404(ActionItem, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        form = ActionItemForm(request.POST, instance=action)
        if form.is_valid():
            form.save()
            messages.success(request, f"Maßnahme '{action.title}' aktualisiert.")
            return redirect("actions:action-detail", pk=action.pk)
    else:
        form = ActionItemForm(instance=action)

    return render(
        request,
        "actions/action_form.html",
        {
            "form": form,
            "title": "Maßnahme bearbeiten",
            "action_obj": action,
        },
    )


# ─── Complete ───────────────────────────────────────────────────────────────


@login_required
def action_complete(request, pk):
    tenant_id = _tenant(request)
    action = get_object_or_404(ActionItem, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        action.status = ActionItem.Status.COMPLETED
        action.completed_at = timezone.now()
        action.save(update_fields=["status", "completed_at", "updated_at"])
        messages.success(request, f"Maßnahme '{action.title}' als erledigt markiert.")
    return redirect("actions:action-detail", pk=action.pk)
