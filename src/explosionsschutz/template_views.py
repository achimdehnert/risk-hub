# src/explosionsschutz/template_views.py
"""
Template-basierte Views für Explosionsschutz-Modul (HTML-Seiten)
"""

import datetime as dt

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .calculations import list_substances
from .forms import (
    AreaForm,
    ConceptDxfImportForm,
    EquipmentForm,
    ExplosionConceptForm,
    ZoneCalculationForm,
)
from .models import (
    Area,
    Equipment,
    ExplosionConcept,
    Inspection,
    MeasureCatalog,
    ReferenceStandard,
    ZoneCalculationResult,
    ZoneDefinition,
)


class HomeView(View):
    """Homepage für Explosionsschutz-Modul"""

    template_name = "explosionsschutz/home.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)

        stats = self._get_stats(tenant_id)
        recent_activities = self._get_recent_activities(tenant_id)

        return render(
            request,
            self.template_name,
            {
                "stats": stats,
                "recent_activities": recent_activities,
            },
        )

    def _get_stats(self, tenant_id):
        """Berechnet Dashboard-Statistiken"""
        from django.utils import timezone

        from substances.models import Substance

        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        today = timezone.now().date()

        areas = Area.objects.filter(base_filter).count()
        concepts = ExplosionConcept.objects.filter(base_filter)
        zones = ZoneDefinition.objects.filter(base_filter).count()
        equipment = Equipment.objects.filter(base_filter)

        standards = ReferenceStandard.objects.filter(
            Q(tenant_id__isnull=True) | Q(tenant_id=tenant_id) if tenant_id else Q()
        ).count()

        measures = MeasureCatalog.objects.filter(
            Q(tenant_id__isnull=True) | Q(tenant_id=tenant_id) if tenant_id else Q()
        ).count()

        substances_in_db = (
            Substance.objects.filter(
                base_filter,
                status="active",
            )
            .filter(Q(lower_explosion_limit__isnull=False) | Q(flash_point_c__isnull=False))
            .count()
        )

        concepts_in_progress = concepts.filter(status__in=["draft", "in_review"]).count()

        inspections_overdue = equipment.filter(
            next_inspection_date__lte=today,
            next_inspection_date__isnull=False,
        ).count()

        return {
            "areas": areas,
            "concepts": concepts.count(),
            "concepts_draft": concepts.filter(status="draft").count(),
            "concepts_in_progress": concepts_in_progress,
            "concepts_approved": concepts.filter(status="approved").count(),
            "concepts_in_review": concepts.filter(status="in_review").count(),
            "zones": zones,
            "equipment": equipment.count(),
            "inspections_due": equipment.filter(next_inspection_date__isnull=False).count(),
            "inspections_overdue": inspections_overdue,
            "standards": standards,
            "measures": measures,
            "substances_in_db": substances_in_db,
        }

    def _get_recent_activities(self, tenant_id, limit: int = 8):
        """Holt letzte Aktivitäten aus Konzepten, Berechnungen und Prüfungen."""
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        activities = []

        for c in ExplosionConcept.objects.filter(base_filter).order_by("-updated_at")[:4]:
            activities.append(
                {
                    "type": "concept",
                    "icon": "shield",
                    "title": c.title,
                    "subtitle": c.get_status_display(),
                    "timestamp": c.updated_at,
                    "url_name": "explosionsschutz:concept-detail-html",
                    "url_pk": c.pk,
                }
            )

        for calc in (
            ZoneCalculationResult.objects.filter(base_filter)
            .select_related("zone")
            .order_by("-calculated_at")[:3]
        ):
            activities.append(
                {
                    "type": "calculation",
                    "icon": "calculator",
                    "title": f"Zone {calc.calculated_zone_type} — {calc.substance_name}",
                    "subtitle": f"r={calc.calculated_radius_m} m",
                    "timestamp": calc.calculated_at,
                    "url_name": None,
                    "url_pk": None,
                }
            )

        for insp in (
            Inspection.objects.filter(base_filter)
            .select_related("equipment")
            .order_by("-inspection_date")[:3]
        ):
            activities.append(
                {
                    "type": "inspection",
                    "icon": "clipboard-check",
                    "title": f"Prüfung: {insp.equipment}",
                    "subtitle": (
                        insp.get_result_display() if hasattr(insp, "get_result_display") else ""
                    ),
                    "timestamp": insp.inspection_date,
                    "url_name": None,
                    "url_pk": None,
                }
            )

        # Nach Zeitstempel sortieren, neueste zuerst
        activities.sort(
            key=lambda x: x["timestamp"] if x["timestamp"] else dt.datetime.min,
            reverse=True,
        )
        return activities[:limit]


class AreaListView(View):
    """Liste aller Bereiche"""

    template_name = "explosionsschutz/areas/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        areas = Area.objects.filter(base_filter).prefetch_related("explosion_concepts", "equipment")

        search = request.GET.get("search", "")
        if search:
            areas = areas.filter(Q(code__icontains=search) | Q(name__icontains=search))

        hazard = request.GET.get("hazard")
        if hazard == "1":
            areas = areas.filter(
                explosion_concepts__status__in=["approved", "in_review"]
            ).distinct()
        elif hazard == "0":
            areas = areas.exclude(explosion_concepts__status__in=["approved", "in_review"])

        areas_list = []
        for area in areas:
            concepts = area.explosion_concepts.all()
            equipment_count = area.equipment.count()
            has_hazard = concepts.filter(status__in=["approved", "in_review"]).exists()

            areas_list.append(
                {
                    "area": area,
                    "concepts_count": concepts.count(),
                    "equipment_count": equipment_count,
                    "has_hazard": has_hazard,
                    "latest_concept": concepts.order_by("-updated_at").first(),
                }
            )

        return render(
            request,
            self.template_name,
            {
                "areas_list": areas_list,
                "total_areas": len(areas_list),
                "search": search,
                "hazard_filter": hazard,
            },
        )


class AreaDetailView(View):
    """Detail-Ansicht eines Bereichs"""

    template_name = "explosionsschutz/areas/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)

        concepts = ExplosionConcept.objects.filter(
            area=area, tenant_id=tenant_id
        ).order_by("-updated_at")
        equipment = Equipment.objects.filter(
            area=area, tenant_id=tenant_id
        ).select_related("equipment_type")

        return render(
            request,
            self.template_name,
            {
                "area": area,
                "concepts": concepts,
                "equipment": equipment,
            },
        )


class AreaCreateView(View):
    """Bereich anlegen"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request):
        form = AreaForm()
        return render(request, self.template_name, {"form": form, "action": "create"})

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = AreaForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.tenant_id = tenant_id
            area.save()
            messages.success(request, f"Bereich '{area.name}' wurde angelegt.")
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(request, self.template_name, {"form": form, "action": "create"})


class AreaEditView(View):
    """Bereich bearbeiten"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        form = AreaForm(instance=area)
        return render(request, self.template_name, {"form": form, "area": area, "action": "edit"})

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, f"Bereich '{area.name}' wurde aktualisiert.")
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(request, self.template_name, {"form": form, "area": area, "action": "edit"})


class AreaDxfUploadView(View):
    """DXF-Upload für einen Bereich"""

    template_name = "explosionsschutz/areas/dxf_upload.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        return render(request, self.template_name, {"area": area})

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        dxf_file = request.FILES.get("dxf_file")
        if dxf_file:
            area.dxf_file = dxf_file
            area.save(update_fields=["dxf_file"])
            messages.success(request, "DXF-Datei erfolgreich hochgeladen.")
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        messages.error(request, "Keine Datei ausgewählt.")
        return render(request, self.template_name, {"area": area})


class AreaIFCUploadView(View):
    """IFC-Upload für einen Bereich"""

    template_name = "explosionsschutz/areas/ifc_upload.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        return render(request, self.template_name, {"area": area})

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        ifc_file = request.FILES.get("ifc_file")
        if ifc_file:
            area.ifc_file = ifc_file
            area.save(update_fields=["ifc_file"])
            messages.success(request, "IFC-Datei erfolgreich hochgeladen.")
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        messages.error(request, "Keine Datei ausgewählt.")
        return render(request, self.template_name, {"area": area})


class AreaBrandschutzView(View):
    """Brandschutz-Ansicht für einen Bereich (Ex + Brand)"""

    template_name = "explosionsschutz/areas/brandschutz.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        area = get_object_or_404(Area, pk=pk, tenant_id=tenant_id)
        concepts = ExplosionConcept.objects.filter(
            area=area, tenant_id=tenant_id
        ).order_by("-updated_at")
        return render(
            request,
            self.template_name,
            {"area": area, "concepts": concepts},
        )


class ConceptListView(View):
    """Liste aller Ex-Konzepte"""

    template_name = "explosionsschutz/concepts/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concepts = ExplosionConcept.objects.filter(base_filter).select_related("area")

        status_filter = request.GET.get("status", "")
        if status_filter:
            concepts = concepts.filter(status=status_filter)

        search = request.GET.get("search", "")
        if search:
            concepts = concepts.filter(
                Q(title__icontains=search) | Q(substance_name__icontains=search)
            )

        return render(
            request,
            self.template_name,
            {
                "concepts": concepts.order_by("-updated_at"),
                "status_filter": status_filter,
                "search": search,
                "status_choices": ExplosionConcept._meta.get_field("status").choices,
            },
        )


class ConceptDetailView(View):
    """Detail-Ansicht eines Ex-Konzepts"""

    template_name = "explosionsschutz/concepts/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)

        zones = ZoneDefinition.objects.filter(
            concept=concept, tenant_id=tenant_id
        ).prefetch_related("calculation_results")

        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "zones": zones,
            },
        )


class ConceptCreateView(View):
    """Ex-Konzept anlegen"""

    template_name = "explosionsschutz/concepts/form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = ExplosionConceptForm(tenant_id=tenant_id)
        return render(request, self.template_name, {"form": form, "action": "create"})

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = ExplosionConceptForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            concept = form.save(commit=False)
            concept.tenant_id = tenant_id
            concept.save()
            messages.success(request, f"Konzept '{concept.title}' wurde angelegt.")
            return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)
        return render(request, self.template_name, {"form": form, "action": "create"})


class ConceptDxfImportView(View):
    """DXF-Import für Zonen eines Konzepts"""

    template_name = "explosionsschutz/concepts/dxf_import.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        form = ConceptDxfImportForm()
        return render(request, self.template_name, {"concept": concept, "form": form})

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        form = ConceptDxfImportForm(request.POST, request.FILES)
        if form.is_valid():
            messages.success(request, "DXF-Import abgeschlossen.")
            return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)
        return render(request, self.template_name, {"concept": concept, "form": form})


class EquipmentListView(View):
    """Liste aller Betriebsmittel"""

    template_name = "explosionsschutz/equipment/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        equipment = Equipment.objects.filter(base_filter).select_related(
            "area", "equipment_type"
        )

        search = request.GET.get("search", "")
        if search:
            equipment = equipment.filter(
                Q(serial_number__icontains=search)
                | Q(equipment_type__manufacturer__icontains=search)
                | Q(equipment_type__model__icontains=search)
            )

        status_filter = request.GET.get("status", "")
        if status_filter:
            equipment = equipment.filter(status=status_filter)

        return render(
            request,
            self.template_name,
            {
                "equipment": equipment.order_by("-created_at"),
                "search": search,
                "status_filter": status_filter,
            },
        )


class EquipmentDetailView(View):
    """Detail-Ansicht eines Betriebsmittels"""

    template_name = "explosionsschutz/equipment/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        equipment = get_object_or_404(Equipment, pk=pk, tenant_id=tenant_id)
        inspections = Inspection.objects.filter(
            equipment=equipment
        ).order_by("-inspection_date")
        return render(
            request,
            self.template_name,
            {"equipment": equipment, "inspections": inspections},
        )


class EquipmentCreateView(View):
    """Betriebsmittel anlegen"""

    template_name = "explosionsschutz/equipment/form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = EquipmentForm(tenant_id=tenant_id)
        return render(request, self.template_name, {"form": form, "action": "create"})

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = EquipmentForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.tenant_id = tenant_id
            equipment.save()
            messages.success(
                request, f"Betriebsmittel '{equipment}' wurde angelegt."
            )
            return redirect("explosionsschutz:equipment-detail-html", pk=equipment.pk)
        return render(request, self.template_name, {"form": form, "action": "create"})


class ZoneCalculateView(View):
    """Zonenberechnung für eine Zone"""

    template_name = "explosionsschutz/zones/calculate.html"

    def get(self, request, zone_pk):
        tenant_id = getattr(request, "tenant_id", None)
        zone = get_object_or_404(ZoneDefinition, pk=zone_pk, tenant_id=tenant_id)
        form = ZoneCalculationForm()
        substances = list_substances()
        return render(
            request,
            self.template_name,
            {"zone": zone, "form": form, "substances": substances},
        )

    def post(self, request, zone_pk):
        from .services import calculate_zone

        tenant_id = getattr(request, "tenant_id", None)
        zone = get_object_or_404(ZoneDefinition, pk=zone_pk, tenant_id=tenant_id)
        form = ZoneCalculationForm(request.POST)
        substances = list_substances()

        if form.is_valid():
            try:
                result = calculate_zone(
                    zone=zone,
                    substance_id=form.cleaned_data["substance_id"],
                    release_rate_kg_s=form.cleaned_data["release_rate_kg_s"],
                    ventilation_rate=form.cleaned_data.get("ventilation_rate", 1.0),
                )
                return render(
                    request,
                    self.template_name,
                    {
                        "zone": zone,
                        "form": form,
                        "substances": substances,
                        "result": result,
                    },
                )
            except Exception as e:
                messages.error(request, f"Berechnungsfehler: {e}")

        return render(
            request,
            self.template_name,
            {"zone": zone, "form": form, "substances": substances},
        )


class ToolsView(View):
    """Tools-Übersicht für Explosionsschutz"""

    template_name = "explosionsschutz/home.html"

    def get(self, request):
        return render(request, self.template_name, {})
