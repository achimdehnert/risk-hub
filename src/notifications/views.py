"""Notification views — HTMX-powered bell dropdown + list."""

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from notifications.models import Notification
from notifications.services import (
    get_unread,
    get_unread_count,
    mark_all_read,
)


class NotificationListView(View):
    """Full notification list page."""

    template_name = "notifications/list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        user_id = getattr(request.user, "id", None)

        notifications = Notification.objects.filter(
            tenant_id=tenant_id,
        ).order_by("-created_at")[:100]

        unread_count = get_unread_count(tenant_id, user_id)

        return render(request, self.template_name, {
            "notifications": notifications,
            "unread_count": unread_count,
        })


class NotificationDropdownView(View):
    """HTMX partial: bell icon dropdown with unread notifications."""

    template_name = "notifications/partials/dropdown.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        user_id = getattr(request.user, "id", None)

        notifications = get_unread(tenant_id, user_id, limit=10)
        unread_count = get_unread_count(tenant_id, user_id)

        return render(request, self.template_name, {
            "notifications": notifications,
            "unread_count": unread_count,
        })


class NotificationBadgeView(View):
    """HTMX partial: just the badge count for polling."""

    template_name = "notifications/partials/badge.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        user_id = getattr(request.user, "id", None)
        count = get_unread_count(tenant_id, user_id)
        return render(request, self.template_name, {
            "unread_count": count,
        })


class NotificationMarkReadView(View):
    """Mark a single notification as read."""

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        notif = get_object_or_404(
            Notification,
            pk=pk,
            tenant_id=tenant_id,
        )
        notif.mark_read()

        if request.htmx:
            return HttpResponse(status=204)
        return JsonResponse({"status": "ok"})


class NotificationMarkAllReadView(View):
    """Mark all notifications as read for the current user."""

    def post(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        user_id = getattr(request.user, "id", None)
        count = mark_all_read(tenant_id, user_id)

        if request.htmx:
            return render(
                request,
                "notifications/partials/badge.html",
                {"unread_count": 0},
            )
        return JsonResponse({"marked_read": count})
