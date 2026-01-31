# src/explosionsschutz/template_views.py
"""
Template-basierte Views für Explosionsschutz-Modul (HTML-Seiten)
"""

from uuid import UUID

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import AreaForm, ExplosionConceptForm, EquipmentForm
from .models import (
    Area,
    ExplosionConcept,
    ZoneDefinition,
    Equipment,
    ReferenceStandard,
    MeasureCatalog,
)


class HomeView(View):
    """Homepage für Explosionsschutz-Modul"""

    template_name = "explosionsschutz/home.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)

        stats = self._get_stats(tenant_id)
        recent_activities = self._get_recent_activities(tenant_id)

        return render(request, self.template_name, {
            "stats": stats,
            "recent_activities": recent_activities,
        })

    def _get_stats(self, tenant_id):
        """Berechnet Dashboard-Statistiken"""
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

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

        return {
            "areas": areas,
            "concepts": concepts.count(),
            "concepts_draft": concepts.filter(status="draft").count(),
            "concepts_approved": concepts.filter(status="approved").count(),
            "zones": zones,
            "equipment": equipment.count(),
            "inspections_due": equipment.filter(
                next_inspection_date__isnull=False
            ).count(),
            "standards": standards,
            "measures": measures,
        }

    def _get_recent_activities(self, tenant_id):
        """Holt letzte Aktivitäten (Placeholder)"""
        return []


class AreaListView(View):
    """Liste aller Bereiche"""

    template_name = "explosionsschutz/areas/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        areas = Area.objects.filter(base_filter).prefetch_related(
            "explosion_concepts", "equipment"
        )

        search = request.GET.get("search", "")
        if search:
            areas = areas.filter(Q(code__icontains=search) | Q(name__icontains=search))

        hazard = request.GET.get("hazard")
        if hazard == "1":
            areas = areas.filter(has_explosion_hazard=True)
        elif hazard == "0":
            areas = areas.filter(has_explosion_hazard=False)

        areas_list = []
        for area in areas:
            areas_list.append({
                "id": area.id,
                "code": area.code,
                "name": area.name,
                "has_explosion_hazard": area.has_explosion_hazard,
                "concepts_count": area.explosion_concepts.count(),
                "equipment_count": area.equipment.count(),
            })

        return render(request, self.template_name, {"areas": areas_list})


class AreaDetailView(View):
    """Detailansicht eines Bereichs"""

    template_name = "explosionsschutz/areas/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        concepts = area.explosion_concepts.all()
        equipment = area.equipment.select_related("equipment_type").all()

        zones_count = sum(c.zones.count() for c in concepts)

        return render(request, self.template_name, {
            "area": area,
            "concepts": concepts,
            "equipment": equipment,
            "zones_count": zones_count,
        })


class ConceptListView(View):
    """Liste aller Ex-Konzepte"""

    template_name = "explosionsschutz/concepts/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concepts = ExplosionConcept.objects.filter(base_filter).select_related(
            "area"
        ).prefetch_related("zones")

        search = request.GET.get("search", "")
        if search:
            concepts = concepts.filter(title__icontains=search)

        status_filter = request.GET.get("status")
        if status_filter:
            concepts = concepts.filter(status=status_filter)

        concepts = concepts.order_by("-created_at")

        return render(request, self.template_name, {"concepts": concepts})


class ConceptDetailView(View):
    """Detailansicht eines Ex-Konzepts"""

    template_name = "explosionsschutz/concepts/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk
        )
        zones = concept.zones.all()
        measures = concept.measures.all()
        documents = concept.documents.all()

        return render(request, self.template_name, {
            "concept": concept,
            "zones": zones,
            "measures": measures,
            "documents": documents,
        })


class EquipmentListView(View):
    """Liste aller Betriebsmittel"""

    template_name = "explosionsschutz/equipment/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        equipment = Equipment.objects.filter(base_filter).select_related(
            "equipment_type", "area", "zone"
        )

        search = request.GET.get("search", "")
        if search:
            equipment = equipment.filter(serial_number__icontains=search)

        status_filter = request.GET.get("status")
        if status_filter:
            equipment = equipment.filter(status=status_filter)

        equipment = equipment.order_by("-created_at")

        return render(request, self.template_name, {"equipment": equipment})


class EquipmentDetailView(View):
    """Detailansicht eines Betriebsmittels"""

    template_name = "explosionsschutz/equipment/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        equipment = get_object_or_404(
            Equipment.objects.filter(base_filter).select_related(
                "equipment_type", "area", "zone"
            ),
            pk=pk
        )
        inspections = equipment.inspections.order_by("-inspection_date")

        return render(request, self.template_name, {
            "equipment": equipment,
            "inspections": inspections,
        })


# =============================================================================
# FORM VIEWS (Create/Edit)
# =============================================================================

class AreaCreateView(View):
    """Bereich erstellen"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request):
        form = AreaForm()
        return render(request, self.template_name, {
            "form": form,
            "title": "Neuer Bereich",
        })

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = AreaForm(request.POST)
        if form.is_valid():
            area = form.save(commit=False)
            area.tenant_id = tenant_id
            area.site_id = tenant_id  # Use tenant as site for now
            area.save()
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(request, self.template_name, {
            "form": form,
            "title": "Neuer Bereich",
        })


class AreaEditView(View):
    """Bereich bearbeiten"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        form = AreaForm(instance=area)
        return render(request, self.template_name, {
            "form": form,
            "title": f"Bereich bearbeiten: {area.code}",
            "area": area,
        })

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(request, self.template_name, {
            "form": form,
            "title": f"Bereich bearbeiten: {area.code}",
            "area": area,
        })


class ConceptCreateView(View):
    """Konzept erstellen"""

    template_name = "explosionsschutz/concepts/form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = ExplosionConceptForm(tenant_id=tenant_id)
        return render(request, self.template_name, {
            "form": form,
            "title": "Neues Konzept",
        })

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = ExplosionConceptForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            concept = form.save(commit=False)
            concept.tenant_id = tenant_id
            concept.save()
            return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)
        return render(request, self.template_name, {
            "form": form,
            "title": "Neues Konzept",
        })


class EquipmentCreateView(View):
    """Equipment erstellen"""

    template_name = "explosionsschutz/equipment/form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = EquipmentForm(tenant_id=tenant_id)
        return render(request, self.template_name, {
            "form": form,
            "title": "Neues Betriebsmittel",
        })

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = EquipmentForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.tenant_id = tenant_id
            equipment.save()
            return redirect(
                "explosionsschutz:equipment-detail-html", pk=equipment.pk
            )
        return render(request, self.template_name, {
            "form": form,
            "title": "Neues Betriebsmittel",
        })
