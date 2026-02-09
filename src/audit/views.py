"""Audit log viewer — filterable list with CSV export."""

import csv
import io

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View

from audit.models import AuditEvent


class AuditLogView(View):
    """Full audit log with filtering."""

    template_name = "audit/log.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        qs = AuditEvent.objects.filter(tenant_id=tenant_id)

        # Filters
        event_type = request.GET.get("event_type")
        resource_type = request.GET.get("resource_type")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        search = request.GET.get("q", "").strip()

        if event_type:
            qs = qs.filter(event_type=event_type)
        if resource_type:
            qs = qs.filter(resource_type__icontains=resource_type)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if search:
            qs = qs.filter(details__icontains=search)

        events = qs.order_by("-created_at")[:200]

        # Distinct values for filter dropdowns
        event_types = AuditEvent.EventType.choices
        resource_types = (
            AuditEvent.objects.filter(tenant_id=tenant_id)
            .values_list("resource_type", flat=True)
            .distinct()[:50]
        )

        return render(request, self.template_name, {
            "events": events,
            "event_types": event_types,
            "resource_types": resource_types,
            "filters": {
                "event_type": event_type or "",
                "resource_type": resource_type or "",
                "date_from": date_from or "",
                "date_to": date_to or "",
                "q": search,
            },
        })


class AuditLogCsvExportView(View):
    """Export filtered audit log as CSV."""

    def get(self, request: HttpRequest) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        qs = AuditEvent.objects.filter(tenant_id=tenant_id)

        event_type = request.GET.get("event_type")
        resource_type = request.GET.get("resource_type")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if event_type:
            qs = qs.filter(event_type=event_type)
        if resource_type:
            qs = qs.filter(resource_type__icontains=resource_type)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        events = qs.order_by("-created_at")[:5000]

        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";")
        writer.writerow([
            "Zeitpunkt", "Typ", "Ressource",
            "Ressource-ID", "Benutzer-ID",
            "IP-Adresse", "Details",
        ])

        for ev in events:
            writer.writerow([
                ev.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ev.event_type,
                ev.resource_type,
                str(ev.resource_id or ""),
                str(ev.user_id or ""),
                ev.ip_address or "",
                str(ev.details)[:500],
            ])

        response = HttpResponse(
            buf.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = (
            'attachment; filename="audit_log.csv"'
        )
        return response
