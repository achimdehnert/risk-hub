# src/training/views.py
"""Views für Unterweisungen (UC-009)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import TrainingSessionForm, TrainingTopicForm
from .models import TrainingSession, TrainingTopic
from .services import (
    create_training_attendance,
    get_all_training_topics,
    get_member_users,
    get_training_sessions,
    get_training_topics,
    get_users_by_ids,
)


def _tenant(request):
    return getattr(request, "tenant_id", None)


# ─── Dashboard ──────────────────────────────────────────────────────────────


@login_required
def dashboard(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    topics = get_training_topics(tenant_id)
    sessions = get_training_sessions(tenant_id)
    upcoming = sessions.filter(
        status=TrainingSession.Status.PLANNED,
        session_date__gte=timezone.now().date(),
    ).order_by("session_date")[:5]
    recent = sessions.filter(
        status=TrainingSession.Status.COMPLETED,
    ).order_by("-session_date")[:5]
    overdue_count = topics.filter(
        sessions__isnull=True,
    ).count()

    return render(
        request,
        "training/dashboard.html",
        {
            "topics_count": topics.count(),
            "sessions_planned": sessions.filter(status="planned").count(),
            "sessions_completed": sessions.filter(status="completed").count(),
            "overdue_count": overdue_count,
            "upcoming": upcoming,
            "recent": recent,
        },
    )


# ─── Topic CRUD ─────────────────────────────────────────────────────────────


@login_required
def topic_list(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    topics = (
        get_all_training_topics(tenant_id)
        .select_related("site", "department")
        .annotate(session_count=Count("sessions"))
        .order_by("title")
    )
    return render(request, "training/topic_list.html", {"topics": topics})


@login_required
def topic_create(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = TrainingTopicForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.tenant_id = tenant_id
            topic.save()
            messages.success(request, f"Thema '{topic.title}' angelegt.")
            return redirect("training:topic-detail", pk=topic.pk)
    else:
        form = TrainingTopicForm(tenant_id=tenant_id)

    return render(
        request,
        "training/topic_form.html",
        {
            "form": form,
            "title": "Neues Unterweisungsthema",
        },
    )


@login_required
def topic_detail(request, pk):
    tenant_id = _tenant(request)
    topic = get_object_or_404(TrainingTopic, pk=pk, tenant_id=tenant_id)
    sessions = topic.sessions.order_by("-session_date")
    return render(
        request,
        "training/topic_detail.html",
        {
            "topic": topic,
            "sessions": sessions,
        },
    )


@login_required
def topic_edit(request, pk):
    tenant_id = _tenant(request)
    topic = get_object_or_404(TrainingTopic, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        form = TrainingTopicForm(request.POST, instance=topic, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, f"Thema '{topic.title}' aktualisiert.")
            return redirect("training:topic-detail", pk=topic.pk)
    else:
        form = TrainingTopicForm(instance=topic, tenant_id=tenant_id)

    return render(
        request,
        "training/topic_form.html",
        {
            "form": form,
            "title": f"Thema bearbeiten: {topic.title}",
            "topic": topic,
        },
    )


# ─── Session CRUD ───────────────────────────────────────────────────────────


@login_required
def session_list(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    status_filter = request.GET.get("status", "")
    sessions = (
        get_training_sessions(tenant_id)
        .select_related("topic")
        .annotate(attendee_count=Count("attendances"))
        .order_by("-session_date")
    )
    if status_filter:
        sessions = sessions.filter(status=status_filter)

    return render(
        request,
        "training/session_list.html",
        {
            "sessions": sessions,
            "current_status": status_filter,
        },
    )


@login_required
def session_create(request):
    tenant_id = _tenant(request)
    if not tenant_id:
        return render(request, "403.html", status=403)

    topic_id = request.GET.get("topic")

    if request.method == "POST":
        form = TrainingSessionForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            session = form.save(commit=False)
            session.tenant_id = tenant_id
            session.trainer_id = request.user.pk
            session.save()
            messages.success(request, "Unterweisung angelegt.")
            return redirect("training:session-detail", pk=session.pk)
    else:
        initial = {}
        if topic_id:
            initial["topic"] = topic_id
        initial["session_date"] = timezone.now().date().isoformat()
        form = TrainingSessionForm(tenant_id=tenant_id, initial=initial)

    return render(
        request,
        "training/session_form.html",
        {
            "form": form,
            "title": "Neue Unterweisung planen",
        },
    )


@login_required
def session_detail(request, pk):
    tenant_id = _tenant(request)
    session = get_object_or_404(
        get_training_sessions(tenant_id).select_related("topic"),
        pk=pk,
    )
    attendances = session.attendances.order_by("status", "created_at")

    # Resolve user names
    user_ids = [a.user_id for a in attendances]
    users = {u.pk: u for u in get_users_by_ids(user_ids)}
    for att in attendances:
        att.user_obj = users.get(att.user_id)

    return render(
        request,
        "training/session_detail.html",
        {
            "session": session,
            "attendances": attendances,
        },
    )


@login_required
def session_edit(request, pk):
    tenant_id = _tenant(request)
    session = get_object_or_404(TrainingSession, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        form = TrainingSessionForm(request.POST, instance=session, tenant_id=tenant_id)
        if form.is_valid():
            form.save()
            messages.success(request, "Unterweisung aktualisiert.")
            return redirect("training:session-detail", pk=session.pk)
    else:
        form = TrainingSessionForm(instance=session, tenant_id=tenant_id)

    return render(
        request,
        "training/session_form.html",
        {
            "form": form,
            "title": "Unterweisung bearbeiten",
            "session": session,
        },
    )


@login_required
def session_complete(request, pk):
    tenant_id = _tenant(request)
    session = get_object_or_404(TrainingSession, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        session.status = TrainingSession.Status.COMPLETED
        session.save(update_fields=["status", "updated_at"])
        messages.success(request, "Unterweisung als durchgeführt markiert.")
    return redirect("training:session-detail", pk=session.pk)


# ─── Attendance ─────────────────────────────────────────────────────────────


@login_required
def attendance_manage(request, pk):
    tenant_id = _tenant(request)
    session = get_object_or_404(TrainingSession, pk=pk, tenant_id=tenant_id)

    # Available users in tenant
    available_users = get_member_users(tenant_id).order_by("last_name", "first_name")

    if request.method == "POST":
        # Process attendance form
        selected_ids = request.POST.getlist("user_ids")
        request.POST.getlist("att_status")

        # Delete existing and recreate
        session.attendances.all().delete()
        for uid in selected_ids:
            status = request.POST.get(f"status_{uid}", "present")
            create_training_attendance(tenant_id, session, uid, status)
        messages.success(request, f"{len(selected_ids)} Teilnahme(n) erfasst.")
        return redirect("training:session-detail", pk=session.pk)

    existing = {a.user_id: a for a in session.attendances.all()}

    return render(
        request,
        "training/attendance_form.html",
        {
            "session": session,
            "available_users": available_users,
            "existing": existing,
        },
    )
