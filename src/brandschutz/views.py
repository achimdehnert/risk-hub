"""Brandschutz views — concept list, detail, sections, extinguishers, escape routes."""

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from common.tenant import require_tenant as _require_tenant

from .models import (
    EscapeRoute,
    FireExtinguisher,
    FireProtectionConcept,
    FireProtectionMeasure,
)


class ConceptListView(View):
    template_name = "brandschutz/concept_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concepts = (
            FireProtectionConcept.objects.filter(tenant_id=request.tenant_id)
            .select_related("site")
            .order_by("-created_at")
        )
        return render(request, self.template_name, {"concepts": concepts})


class ConceptDetailView(View):
    template_name = "brandschutz/concept_detail.html"

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept.objects.select_related("site"),
            pk=pk,
            tenant_id=request.tenant_id,
        )
        sections = concept.sections.prefetch_related(
            "escape_routes", "fire_extinguishers", "measures"
        )
        measures = concept.measures.filter(section__isnull=True)
        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "sections": sections,
                "measures": measures,
            },
        )


class ExtinguisherListView(View):
    """Alle Feuerlöscher eines Tenants — Übersicht / Prüfkalender."""

    template_name = "brandschutz/extinguisher_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        extinguishers = (
            FireExtinguisher.objects.filter(tenant_id=request.tenant_id)
            .select_related("section__concept")
            .order_by("next_inspection_date", "section")
        )
        status_filter = request.GET.get("status")
        if status_filter:
            extinguishers = extinguishers.filter(status=status_filter)
        return render(
            request,
            self.template_name,
            {
                "extinguishers": extinguishers,
                "status_choices": FireExtinguisher.Status.choices,
                "current_status": status_filter,
            },
        )


class EscapeRouteListView(View):
    """Alle Fluchtwege eines Tenants — Übersicht / Mängelstatus."""

    template_name = "brandschutz/escape_route_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        routes = (
            EscapeRoute.objects.filter(tenant_id=request.tenant_id)
            .select_related("section__concept")
            .order_by("status", "section")
        )
        status_filter = request.GET.get("status")
        if status_filter:
            routes = routes.filter(status=status_filter)
        return render(
            request,
            self.template_name,
            {
                "routes": routes,
                "status_choices": EscapeRoute.Status.choices,
                "current_status": status_filter,
            },
        )


class MeasureUpdateView(View):
    """HTMX-partial: Maßnahmenstatus aktualisieren."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        measure = get_object_or_404(
            FireProtectionMeasure,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        new_status = request.POST.get("status")
        if new_status in dict(FireProtectionMeasure.Status.choices):
            measure.status = new_status
            if new_status == FireProtectionMeasure.Status.IMPLEMENTED:
                from django.utils import timezone

                measure.completed_at = timezone.now()
            measure.save(update_fields=["status", "completed_at", "updated_at"])
            messages.success(request, f"Maßnahme '{measure.title}' aktualisiert.")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "brandschutz/partials/measure_row.html",
                {"measure": measure},
            )
        return redirect("brandschutz:concept-detail", pk=measure.concept_id)
