# src/explosionsschutz/template_views.py
"""
Template-basierte Views für Explosionsschutz-Modul (HTML-Seiten)
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .calculations import list_substances
from .forms import (
    AreaForm,
    ConceptDxfImportForm,
    EquipmentForm,
    ExplosionConceptForm,
    InspectionForm,
    ProtectionMeasureForm,
    VerificationDocumentForm,
    ZoneCalculationForm,
    ZoneDefinitionForm,
    ZoneProposalForm,
)
from .models import (
    Area,
    Equipment,
    ExplosionConcept,
    IgnitionSource,
    ProtectionMeasure,
    ZoneDefinition,
)

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, View):
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
        from . import services

        return services.get_dashboard_stats(tenant_id)

    def _get_recent_activities(self, tenant_id, limit: int = 8):
        """Holt letzte Aktivitäten aus Konzepten, Berechnungen und Prüfungen."""
        from . import services

        return services.get_recent_activities(tenant_id, limit)


class AreaListView(LoginRequiredMixin, View):
    """Liste aller Bereiche"""

    template_name = "explosionsschutz/areas/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        from . import services

        search = request.GET.get("search", "")
        hazard = request.GET.get("hazard")
        areas = services.get_area_queryset(tenant_id, search=search, hazard_filter=hazard)

        areas_list = []
        for area in areas:
            areas_list.append(
                {
                    "id": area.id,
                    "code": area.code,
                    "name": area.name,
                    "has_explosion_hazard": area.has_explosion_hazard,
                    "concepts_count": area.explosion_concepts.count(),
                    "equipment_count": area.equipment.count(),
                }
            )

        return render(request, self.template_name, {"areas": areas_list})


class AreaDetailView(LoginRequiredMixin, View):
    """Detailansicht eines Bereichs"""

    template_name = "explosionsschutz/areas/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        concepts = area.explosion_concepts.all()
        equipment = area.equipment.select_related("equipment_type").all()

        zones_count = sum(c.zones.count() for c in concepts)

        site_name = self._resolve_site_name(area.site_id)

        return render(
            request,
            self.template_name,
            {
                "area": area,
                "concepts": concepts,
                "equipment": equipment,
                "zones_count": zones_count,
                "site_name": site_name,
            },
        )

    @staticmethod
    def _resolve_site_name(site_id):
        """Resolve site_id UUID to a human-readable name."""
        if not site_id:
            return "—"
        from tenancy.models import Organization, Site

        site = Site.objects.filter(pk=site_id).first()
        if site:
            return site.name
        org = Organization.objects.filter(tenant_id=site_id).first()
        if org:
            return org.name
        return "—"


class ConceptListView(LoginRequiredMixin, View):
    """Liste aller Ex-Konzepte"""

    template_name = "explosionsschutz/concepts/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        from . import services

        search = request.GET.get("search", "")
        status_filter = request.GET.get("status")
        concepts = services.get_concept_queryset(tenant_id, search=search, status_filter=status_filter)

        return render(request, self.template_name, {"concepts": concepts})


class ConceptDetailView(LoginRequiredMixin, View):
    """Detailansicht eines Ex-Konzepts"""

    template_name = "explosionsschutz/concepts/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"), pk=pk
        )
        zones = concept.zones.all()
        measures = concept.measures.all()
        documents = concept.documents.all()

        from .models import ExDocInstance, ExDocTemplate

        doc_instances = (
            ExDocInstance.objects.filter(
                concept=concept,
                tenant_id=tenant_id,
            )
            .select_related("template")
            .order_by("-updated_at")
        )
        from .ex_doc_constants import SYSTEM_TENANT_ID

        doc_templates = ExDocTemplate.objects.filter(
            Q(tenant_id=tenant_id) | Q(tenant_id=SYSTEM_TENANT_ID),
            status=ExDocTemplate.Status.ACCEPTED,
        ).order_by("name")

        from approvals.models import ApprovalRequest

        active_approval = ApprovalRequest.objects.filter(
            tenant_id=tenant_id,
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            status__in=[ApprovalRequest.Status.PENDING, ApprovalRequest.Status.IN_REVIEW],
        ).first()

        try:
            from django.apps import apps
            DocTemplate = apps.get_model("doc_templates", "DocumentTemplate")
            external_doc_templates = DocTemplate.objects.filter(
                tenant_id=tenant_id
            ).exclude(status="archived").order_by("scope", "name")
        except Exception:
            external_doc_templates = []

        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "zones": zones,
                "measures": measures,
                "documents": documents,
                "doc_instances": doc_instances,
                "doc_templates": doc_templates,
                "external_doc_templates": external_doc_templates,
                "active_approval": active_approval,
                "zone_form": ZoneDefinitionForm(),
                "measure_form": ProtectionMeasureForm(),
                "document_form": VerificationDocumentForm(),
            },
        )

    def post(self, request, pk):
        """Submit concept for approval or record a decision (HTMX-compatible)."""
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=pk)

        action = request.POST.get("action")
        user_id = getattr(request.user, "id", None)

        if action == "submit_approval":
            from approvals.services import submit_for_approval

            try:
                submit_for_approval(
                    tenant_id=tenant_id,
                    entity_type="explosionsschutz.ExplosionConcept",
                    entity_id=concept.id,
                    user_id=user_id,
                )
                from . import services

                services.submit_concept_approval_transition(concept.id, tenant_id)
                messages.success(request, "Freigabeprozess gestartet.")
            except ValueError as exc:
                messages.error(request, str(exc))

        elif action in ("approve_step", "reject_step"):
            from approvals.models import ApprovalDecision, ApprovalRequest
            from approvals.services import decide

            request_id = request.POST.get("request_id")
            comment = request.POST.get("comment", "")
            outcome = (
                ApprovalDecision.Outcome.APPROVED
                if action == "approve_step"
                else ApprovalDecision.Outcome.REJECTED
            )
            try:
                decide(
                    request_id=request_id,
                    outcome=outcome,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    comment=comment,
                )
                messages.success(
                    request,
                    "Freigabe erteilt." if action == "approve_step" else "Freigabe abgelehnt.",
                )
            except (ValueError, ApprovalRequest.DoesNotExist) as exc:
                messages.error(request, str(exc))

        if request.headers.get("HX-Request"):
            return HttpResponse(
                '<div id="approval-status" hx-swap-oob="true">'
                + "".join(
                    f'<div class="alert alert-{"success" if m.level == 25 else "danger"}">'
                    f"{m.message}</div>"
                    for m in messages.get_messages(request)
                )
                + "</div>",
                content_type="text/html",
            )

        return redirect("explosionsschutz:concept-detail-html", pk=pk)


class EquipmentListView(LoginRequiredMixin, View):
    """Liste aller Betriebsmittel"""

    template_name = "explosionsschutz/equipment/list.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        from . import services

        search = request.GET.get("search", "")
        status_filter = request.GET.get("status")
        equipment = services.get_equipment_queryset(tenant_id, search=search, status_filter=status_filter)

        return render(request, self.template_name, {"equipment": equipment})


class EquipmentDetailView(LoginRequiredMixin, View):
    """Detailansicht eines Betriebsmittels"""

    template_name = "explosionsschutz/equipment/detail.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        from . import services

        equipment = get_object_or_404(services.get_equipment_queryset(tenant_id), pk=pk)
        inspections = equipment.inspections.order_by("-inspection_date")

        return render(
            request,
            self.template_name,
            {
                "equipment": equipment,
                "inspections": inspections,
            },
        )


# =============================================================================
# FORM VIEWS (Create/Edit)
# =============================================================================


class AreaCreateView(LoginRequiredMixin, View):
    """Bereich erstellen"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request):
        form = AreaForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neuer Bereich",
            },
        )

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            messages.error(request, "Mandant konnte nicht ermittelt werden. Bitte erneut anmelden.")
            return redirect("explosionsschutz:area-list-html")
        form = AreaForm(request.POST)
        if form.is_valid():
            from . import services

            area = form.save(commit=False)
            services.create_area(tenant_id, area)
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neuer Bereich",
            },
        )


class AreaEditView(LoginRequiredMixin, View):
    """Bereich bearbeiten"""

    template_name = "explosionsschutz/areas/form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        form = AreaForm(instance=area)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Bereich bearbeiten: {area.code}",
                "area": area,
            },
        )

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            from . import services

            updated_area = form.save(commit=False)
            services.update_area(updated_area)
            return redirect("explosionsschutz:area-detail-html", pk=area.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Bereich bearbeiten: {area.code}",
                "area": area,
            },
        )


class ConceptCreateView(LoginRequiredMixin, View):
    """Konzept erstellen"""

    template_name = "explosionsschutz/concepts/form.html"

    def _get_doc_templates(self, tenant_id):
        try:
            from django.apps import apps
            DocTemplate = apps.get_model("doc_templates", "DocumentTemplate")
            return DocTemplate.objects.filter(tenant_id=tenant_id).exclude(status="archived").order_by("scope", "name")
        except Exception:
            return []

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = ExplosionConceptForm(tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Konzept",
                "doc_templates": self._get_doc_templates(tenant_id),
            },
        )

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            messages.error(request, "Mandant konnte nicht ermittelt werden. Bitte erneut anmelden.")
            return redirect("explosionsschutz:concept-list-html")
        form = ExplosionConceptForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            from . import services

            concept = form.save(commit=False)
            services.create_concept_from_form(tenant_id, concept)
            return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Konzept",
                "doc_templates": self._get_doc_templates(tenant_id),
            },
        )


class ConceptFinalizeView(LoginRequiredMixin, View):
    """Schritt 6: Konzept zusammenführen → OutputDocument aus doc_templates.DocumentTemplate erstellen."""

    template_name = "explosionsschutz/concepts/finalize.html"

    def _get_doc_templates(self, tenant_id):
        from django.apps import apps
        DocTemplate = apps.get_model("doc_templates", "DocumentTemplate")
        return DocTemplate.objects.filter(tenant_id=tenant_id).exclude(status="archived").order_by("scope", "name")

    def _get_projects(self, tenant_id):
        from projects.models import Project
        return Project.objects.filter(tenant_id=tenant_id).order_by("name")

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        return render(request, self.template_name, {
            "concept": concept,
            "doc_templates": self._get_doc_templates(tenant_id),
            "projects": self._get_projects(tenant_id),
        })

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)

        template_id = request.POST.get("doc_template_id")
        project_id = request.POST.get("project_id") or (concept.project_id)
        title = request.POST.get("title", "").strip() or concept.title

        if not template_id or not project_id:
            messages.error(request, "Bitte Vorlage und Projekt auswählen.")
            return render(request, self.template_name, {
                "concept": concept,
                "doc_templates": self._get_doc_templates(tenant_id),
                "projects": self._get_projects(tenant_id),
                "error": "Vorlage und Projekt sind Pflichtfelder.",
            })

        from django.apps import apps

        from projects.models import Project
        from projects.services import create_output_document

        DocTemplate = apps.get_model("doc_templates", "DocumentTemplate")
        try:
            tmpl = DocTemplate.objects.get(pk=template_id, tenant_id=tenant_id)
            project = Project.objects.get(pk=project_id, tenant_id=tenant_id)
        except Exception as e:
            messages.error(request, f"Vorlage oder Projekt nicht gefunden: {e}")
            return redirect("explosionsschutz:concept-finalize", pk=pk)

        doc = create_output_document(
            tenant_id=tenant_id,
            project=project,
            template=tmpl,
            title=title,
            created_by=request.user,
        )

        # Konzept mit Projekt verknüpfen falls noch nicht
        from . import services

        services.link_concept_to_project(concept.pk, project.pk, tenant_id)

        messages.success(request, f"Dokument '{doc.title}' erstellt — jetzt editieren.")
        return redirect("projects:output-document-edit", pk=project.pk, doc_pk=doc.pk)


class ConceptEditView(LoginRequiredMixin, View):
    """Konzept bearbeiten"""

    template_name = "explosionsschutz/concepts/form.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        form = ExplosionConceptForm(instance=concept, tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Konzept bearbeiten: {concept.title}",
                "concept": concept,
            },
        )

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        form = ExplosionConceptForm(request.POST, instance=concept, tenant_id=tenant_id)
        if form.is_valid():
            from . import services

            updated_concept = form.save(commit=False)
            services.update_concept_from_form(updated_concept)
            return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": f"Konzept bearbeiten: {concept.title}",
                "concept": concept,
            },
        )


class ConceptValidateView(LoginRequiredMixin, View):
    """Konzept validieren (Status → in_review)"""

    def post(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=tenant_id)
        if concept.status == ExplosionConcept.Status.DRAFT:
            from . import services

            updated = services.submit_concept_for_review(
                concept.pk, tenant_id, user_id=request.user.pk
            )
            messages.success(request, f'Konzept "{updated.title}" zur Prüfung freigegeben.')
        return redirect("explosionsschutz:concept-detail-html", pk=pk)


class EquipmentCreateView(LoginRequiredMixin, View):
    """Equipment erstellen"""

    template_name = "explosionsschutz/equipment/form.html"

    def get(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        form = EquipmentForm(tenant_id=tenant_id)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Betriebsmittel",
            },
        )

    def post(self, request):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            messages.error(request, "Mandant konnte nicht ermittelt werden. Bitte erneut anmelden.")
            return redirect("explosionsschutz:equipment-list-html")
        form = EquipmentForm(request.POST, tenant_id=tenant_id)
        if form.is_valid():
            from . import services

            equipment = form.save(commit=False)
            services.create_equipment_from_form(tenant_id, equipment)
            return redirect("explosionsschutz:equipment-detail-html", pk=equipment.pk)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "title": "Neues Betriebsmittel",
            },
        )


class ToolsView(LoginRequiredMixin, View):
    """Berechnungstools für Explosionsschutz"""

    template_name = "explosionsschutz/tools.html"

    def get(self, request):
        substances = list_substances()
        return render(
            request,
            self.template_name,
            {
                "substances": substances,
                "substance_count": len(substances),
            },
        )


class AreaDxfUploadView(LoginRequiredMixin, View):
    """DXF-Upload für einen Bereich — parst Räume/Flächen via nl2cad-core/areas."""

    template_name = "explosionsschutz/areas/dxf_upload.html"

    def get(self, request, pk):
        from .services.dxf_service import is_dwg_conversion_available

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        return render(
            request, self.template_name,
            {"area": area, "dwg_available": is_dwg_conversion_available()},
        )

    def post(self, request, pk):
        import logging

        from .services.dxf_service import DXFService, is_dwg_conversion_available

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        dxf_file = request.FILES.get("dxf_file")
        if not dxf_file:
            return render(
                request, self.template_name,
                {"area": area, "error": "Keine DXF-Datei hochgeladen."},
            )

        fname_lower = dxf_file.name.lower()
        if not fname_lower.endswith((".dxf", ".dwg")):
            return render(
                request, self.template_name,
                {"area": area, "error": "Nur .dxf oder .dwg Dateien sind erlaubt."},
            )

        raw_bytes = dxf_file.read()
        service = DXFService()
        result = service.process_upload(raw_bytes, dxf_file.name)

        if not result.success:
            return render(
                request, self.template_name,
                {
                    "area": area,
                    "error": result.error,
                    "parse_hints": result.parse_hints,
                    "dwg_available": is_dwg_conversion_available(),
                },
            )

        from . import services

        area.dxf_file = dxf_file
        area.dxf_analysis_json = result.analysis_json
        area.brandschutz_analysis_json = None

        # SVG-Preview generieren
        try:
            from .services.svg_export import generate_svg_for_area
            generate_svg_for_area(area)
        except Exception as exc:
            logger.warning("[AreaDxfUpload] SVG-Generierung: %s", exc)

        services.update_area(area)

        logger.info(
            "[AreaDxfUpload] %s: %d Räume, %.1f m² gespeichert (Plantyp: %s)",
            area.code, result.rooms_count, result.total_area_m2, result.plan_type,
        )
        return redirect("explosionsschutz:area-brandschutz", pk=area.pk)


class AreaIFCUploadView(LoginRequiredMixin, View):
    """IFC-Upload für einen Bereich — parst Räume/Geschosse via nl2cad-core IFCParser."""

    template_name = "explosionsschutz/areas/ifc_upload.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        return render(request, self.template_name, {"area": area})

    def post(self, request, pk):
        import logging

        from nl2cad.core.exceptions import IFCParseError, UnsupportedFormatError
        from nl2cad.core.parsers.ifc_parser import IFCParser

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        ifc_file = request.FILES.get("ifc_file")
        if not ifc_file:
            return render(
                request,
                self.template_name,
                {"area": area, "error": "Keine IFC-Datei hochgeladen."},
            )

        if not ifc_file.name.lower().endswith(".ifc"):
            return render(
                request,
                self.template_name,
                {"area": area, "error": "Nur .ifc Dateien sind erlaubt."},
            )

        try:
            parser = IFCParser()
            ifc_model = parser.parse_bytes(ifc_file.read(), ifc_file.name)
        except (IFCParseError, UnsupportedFormatError) as exc:
            logger.warning("[AreaIFCUpload] Parse-Fehler %s: %s", area.code, exc)
            return render(
                request,
                self.template_name,
                {"area": area, "error": f"IFC konnte nicht gelesen werden: {exc}"},
            )

        analysis = {
            "schema": ifc_model.schema,
            "project_name": ifc_model.project_name,
            "building_name": ifc_model.building_name,
            "floor_count": ifc_model.floor_count,
            "rooms_count": len(ifc_model.rooms),
            "total_area_m2": round(ifc_model.total_area_m2, 2),
            "floors": [
                {
                    "name": f.name,
                    "elevation_m": round(f.elevation_m, 2),
                    "rooms_count": len(f.rooms),
                    "doors_count": len(f.doors),
                    "walls_count": len(f.walls),
                }
                for f in ifc_model.floors
            ],
            "rooms": [
                {
                    "name": r.name,
                    "number": r.number,
                    "floor_name": r.floor_name,
                    "area_m2": round(r.area_m2, 2),
                    "height_m": round(r.height_m, 2),
                    "volume_m3": round(r.volume_m3, 2),
                    "usage_category": r.usage_category,
                }
                for r in ifc_model.rooms
            ],
            "fire_doors": [
                {
                    "name": d.name,
                    "fire_rating": d.fire_rating,
                    "width_m": round(d.width_m, 2),
                    "floor_guid": d.floor_guid,
                }
                for f in ifc_model.floors
                for d in f.doors
                if d.is_fire_door
            ],
        }

        from . import services

        services.update_area_analysis(area, analysis)

        logger.info(
            "[AreaIFCUpload] %s: schema=%s, %d Räume, %.1f m² gespeichert",
            area.code,
            ifc_model.schema,
            len(ifc_model.rooms),
            ifc_model.total_area_m2,
        )
        return redirect("explosionsschutz:area-brandschutz", pk=area.pk)


class ZoneCalculateView(LoginRequiredMixin, View):
    """
    TRGS 721 Zonenberechnung via riskfw.
    GET  → leeres Formular für eine Zone
    POST → berechnet + archiviert ZoneCalculationResult, Ergebnis inline
    HTMX: hx-post, hx-target="#zone-calc-result"
    """

    template_name = "explosionsschutz/zones/calculate.html"
    partial_template = "explosionsschutz/zones/_calc_result.html"

    def get(self, request, zone_pk):
        import logging

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        zone = get_object_or_404(
            ZoneDefinition.objects.filter(base_filter).select_related("concept"),
            pk=zone_pk,
        )
        form = ZoneCalculationForm(initial={"zone_id": zone.pk})
        history = zone.calculations.order_by("-calculated_at")[:5]
        logger.debug("[ZoneCalculate] GET zone=%s", zone_pk)
        return render(
            request,
            self.template_name,
            {
                "zone": zone,
                "form": form,
                "history": history,
            },
        )

    def post(self, request, zone_pk):
        import logging

        from django.core.exceptions import ValidationError as DjangoValidationError

        from .services import CalculateZoneCmd, calculate_and_store_zone

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        zone = get_object_or_404(
            ZoneDefinition.objects.filter(base_filter).select_related("concept"),
            pk=zone_pk,
        )
        form = ZoneCalculationForm(request.POST)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(
                    request,
                    self.partial_template,
                    {
                        "form": form,
                        "zone": zone,
                        "error": None,
                        "result": None,
                    },
                )
            history = zone.calculations.order_by("-calculated_at")[:5]
            return render(
                request,
                self.template_name,
                {
                    "zone": zone,
                    "form": form,
                    "history": history,
                },
            )

        cmd = CalculateZoneCmd(
            zone_id=zone.pk,
            release_rate_kg_s=form.cleaned_data["release_rate_kg_s"],
            ventilation_rate_m3_s=form.cleaned_data["ventilation_rate_m3_s"],
            release_type=form.cleaned_data["release_type"],
            notes=form.cleaned_data.get("notes", ""),
        )
        try:
            calc = calculate_and_store_zone(
                cmd=cmd,
                tenant_id=tenant_id,
                user_id=getattr(request.user, "id", None),
            )
            logger.info(
                "[ZoneCalculate] Zone %s: %s r=%.3fm",
                zone_pk,
                calc.calculated_zone_type,
                calc.calculated_radius_m,
            )
        except DjangoValidationError as exc:
            error_msg = " ".join(exc.messages)
            if is_htmx:
                return render(
                    request,
                    self.partial_template,
                    {
                        "form": form,
                        "zone": zone,
                        "error": error_msg,
                        "result": None,
                    },
                )
            history = zone.calculations.order_by("-calculated_at")[:5]
            return render(
                request,
                self.template_name,
                {
                    "zone": zone,
                    "form": form,
                    "history": history,
                    "error": error_msg,
                },
            )

        if is_htmx:
            return render(
                request,
                self.partial_template,
                {
                    "form": ZoneCalculationForm(initial={"zone_id": zone.pk}),
                    "zone": zone,
                    "result": calc,
                    "error": None,
                },
            )
        return redirect("explosionsschutz:concept-detail-html", pk=zone.concept_id)


class ConceptDxfImportView(LoginRequiredMixin, View):
    """
    DXF-Import für Ex-Zonen via nl2cad-brandschutz.
    GET  → Upload-Formular
    POST → import_zones_from_dxf() → Anzahl + Liste neuer Zonen
    HTMX: hx-post, hx-target="#dxf-import-result"
    """

    template_name = "explosionsschutz/concepts/dxf_import.html"
    partial_template = "explosionsschutz/concepts/_dxf_import_result.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=pk)
        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "form": ConceptDxfImportForm(),
            },
        )

    def post(self, request, pk):
        import logging

        from django.core.exceptions import ValidationError as DjangoValidationError

        from .services import import_zones_from_dxf

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=pk)
        form = ConceptDxfImportForm(request.POST, request.FILES)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(
                    request,
                    self.partial_template,
                    {
                        "concept": concept,
                        "form": form,
                        "error": None,
                        "count": None,
                        "zones": [],
                    },
                )
            return render(
                request,
                self.template_name,
                {
                    "concept": concept,
                    "form": form,
                },
            )

        dxf_bytes = form.cleaned_data["dxf_file"].read()
        try:
            count = import_zones_from_dxf(
                concept_id=concept.pk,
                dxf_bytes=dxf_bytes,
                tenant_id=tenant_id,
                user_id=getattr(request.user, "id", None),
            )
            logger.info("[DxfImport] Concept %s: %d Zonen importiert", pk, count)
        except DjangoValidationError as exc:
            error_msg = " ".join(exc.messages)
            if is_htmx:
                return render(
                    request,
                    self.partial_template,
                    {
                        "concept": concept,
                        "form": form,
                        "error": error_msg,
                        "count": None,
                        "zones": [],
                    },
                )
            return render(
                request,
                self.template_name,
                {
                    "concept": concept,
                    "form": form,
                    "error": error_msg,
                },
            )

        new_zones = concept.zones.order_by("-created_at")[:count]
        if is_htmx:
            return render(
                request,
                self.partial_template,
                {
                    "concept": concept,
                    "form": ConceptDxfImportForm(),
                    "error": None,
                    "count": count,
                    "zones": new_zones,
                },
            )
        return redirect("explosionsschutz:concept-detail-html", pk=concept.pk)


class AreaBrandschutzView(LoginRequiredMixin, View):
    """Brandschutz-Layer-Analyse für einen Bereich via nl2cad-brandschutz."""

    template_name = "explosionsschutz/areas/brandschutz.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        analyse = area.brandschutz_analysis_json
        dxf_data = area.dxf_analysis_json
        dxf_empty = bool(dxf_data) and dxf_data.get("rooms_count", -1) == 0 and dxf_data.get("layers_count", 0) > 0
        return render(
            request,
            self.template_name,
            {
                "area": area,
                "analyse": analyse,
                "dxf_data": dxf_data,
                "has_dxf": bool(area.dxf_file),
                "dxf_empty": dxf_empty,
            },
        )

    def post(self, request, pk):
        import logging
        import tempfile

        from brandschutz.analyzer import BrandschutzAnalyzer

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        if not area.dxf_file:
            return render(
                request,
                self.template_name,
                {
                    "area": area,
                    "error": "Kein DXF hochgeladen. Bitte zuerst DXF hochladen.",
                    "has_dxf": False,
                },
            )

        try:
            import ezdxf

            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                for chunk in area.dxf_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            doc = ezdxf.readfile(tmp_path)
        except Exception as exc:
            logger.warning("[AreaBrandschutz] DXF-Lesefehler %s: %s", pk, exc)
            return render(
                request,
                self.template_name,
                {
                    "area": area,
                    "error": f"DXF konnte nicht gelesen werden: {exc}",
                    "has_dxf": True,
                },
            )

        analyzer = BrandschutzAnalyzer()
        result = analyzer.analyze_dxf(doc, etage=area.code or "EG")

        area.brandschutz_analysis_json = result.to_dict()
        area.save()

        logger.info(
            "[AreaBrandschutz] %s: %d Fluchtwege, %d Mängel",
            area.code,
            len(result.fluchtwege),
            len(result.maengel),
        )
        return redirect("explosionsschutz:area-brandschutz", pk=area.pk)


class AreaExZonenAnalyseView(LoginRequiredMixin, View):
    """
    ATEX Ex-Zonen-Analyse — on-demand aus gecachtem dxf_analysis_json.

    Erkennt Zone 0/1/2 (Gas) und 20/21/22 (Staub) aus Layer-/Raumnamen.
    Kein erneuter DXF-Upload nötig.
    """

    template_name = "explosionsschutz/areas/ex_zonen_analyse.html"

    def get(self, request, pk):
        import logging

        from nl2cad.core.analyzers.ex_zonen_analyzer import ExZonenAnalyzer

        from .services.dxf_service import reconstruct_dxf_model

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        dxf_data = area.dxf_analysis_json
        if not dxf_data:
            return render(request, self.template_name, {
                "area": area, "has_dxf": False, "result": None,
            })

        try:
            room_height_m = float(request.GET.get("room_height_m", 3.0))
            model = reconstruct_dxf_model(dxf_data)
            result = ExZonenAnalyzer(room_height_m=room_height_m).analyze(model)
        except Exception as exc:
            logger.warning("[ExZonenAnalyse] Fehler %s: %s", pk, exc)
            return render(request, self.template_name, {
                "area": area, "has_dxf": True, "result": None,
                "error": f"Analyse fehlgeschlagen: {exc}",
            })

        return render(request, self.template_name, {
            "area": area,
            "has_dxf": True,
            "result": result,
            "dxf_data": dxf_data,
            "room_height_m": room_height_m,
        })


class AreaMengenView(LoginRequiredMixin, View):
    """
    Mengenermittlung + GAEB-Positions-Grundlage — on-demand aus dxf_analysis_json.

    Liefert Wand-/Bodenflächen, Türen, Fenster, DIN 276 Kostengruppen
    und GAEB-Positionen mit indikativer Kostenschätzung.
    """

    template_name = "explosionsschutz/areas/mengen.html"

    def get(self, request, pk):
        import logging

        from nl2cad.core.analyzers.bauteil_mengen_extractor import BauteilmengenExtractor

        from .services.dxf_service import reconstruct_dxf_model

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        dxf_data = area.dxf_analysis_json
        if not dxf_data:
            return render(request, self.template_name, {
                "area": area, "has_dxf": False, "mengen": None,
            })

        try:
            room_height_m = float(request.GET.get("room_height_m", 3.0))
            bgf_zuschlag = float(request.GET.get("bgf_zuschlag", 1.15))
            model = reconstruct_dxf_model(dxf_data)
            entity_stats = dxf_data.get("entity_stats", {})
            extractor = BauteilmengenExtractor(
                room_height_m=room_height_m,
                bgf_zuschlag=bgf_zuschlag,
            )
            mengen = extractor.extract(model, entity_stats=entity_stats)
        except Exception as exc:
            logger.warning("[Mengenermittlung] Fehler %s: %s", pk, exc)
            return render(request, self.template_name, {
                "area": area, "has_dxf": True, "mengen": None,
                "error": f"Mengenermittlung fehlgeschlagen: {exc}",
            })

        return render(request, self.template_name, {
            "area": area,
            "has_dxf": True,
            "mengen": mengen,
            "dxf_data": dxf_data,
            "room_height_m": room_height_m,
            "bgf_zuschlag": bgf_zuschlag,
        })


# =============================================================================
# HTMX PARTIALS — Zone / Measure / Ignition inline management
# =============================================================================


class HtmxAddZoneView(LoginRequiredMixin, View):
    """
    HTMX: Zone inline zu Concept hinzufügen.
    POST → Zone erstellen, Partial mit aktueller Zonenliste zurückgeben.
    """

    partial_template = "explosionsschutz/partials/_zone_list.html"

    def post(self, request, concept_pk):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return HttpResponseForbidden("Mandant nicht ermittelt.")
        base_filter = Q(tenant_id=tenant_id)
        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=concept_pk)

        form = ZoneDefinitionForm(request.POST)
        if form.is_valid():
            zone = form.save(commit=False)
            zone.tenant_id = tenant_id
            zone.concept = concept
            zone.save()

        zones = concept.zones.all()
        zone_form = ZoneDefinitionForm()
        return render(
            request,
            self.partial_template,
            {"concept": concept, "zones": zones, "zone_form": zone_form, "htmx_response": True},
        )


class HtmxDeleteZoneView(LoginRequiredMixin, View):
    """HTMX: Zone löschen, aktualisierte Liste zurückgeben."""

    partial_template = "explosionsschutz/partials/_zone_list.html"

    def delete(self, request, zone_pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        zone = get_object_or_404(ZoneDefinition.objects.filter(base_filter), pk=zone_pk)
        concept = zone.concept
        zone.delete()

        zones = concept.zones.all()
        zone_form = ZoneDefinitionForm()
        return render(
            request,
            self.partial_template,
            {"concept": concept, "zones": zones, "zone_form": zone_form, "htmx_response": True},
        )


class HtmxAddMeasureView(LoginRequiredMixin, View):
    """
    HTMX: Schutzmaßnahme inline zu Concept hinzufügen.
    POST → Measure erstellen, Partial mit aktueller Liste zurückgeben.
    """

    partial_template = "explosionsschutz/partials/_measure_list.html"

    def post(self, request, concept_pk):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return HttpResponseForbidden("Mandant nicht ermittelt.")
        base_filter = Q(tenant_id=tenant_id)
        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=concept_pk)

        form = ProtectionMeasureForm(request.POST)
        if form.is_valid():
            measure = form.save(commit=False)
            measure.tenant_id = tenant_id
            measure.concept = concept
            measure.save()
            measure_form = ProtectionMeasureForm()
        else:
            logger.warning("HtmxAddMeasureView invalid: %s", form.errors)
            measure_form = form

        measures = concept.measures.all()
        return render(
            request,
            self.partial_template,
            {
                "concept": concept,
                "measures": measures,
                "measure_form": measure_form,
                "htmx_response": True,
            },
        )


class HtmxDeleteMeasureView(LoginRequiredMixin, View):
    """HTMX: Maßnahme löschen, aktualisierte Liste zurückgeben."""

    partial_template = "explosionsschutz/partials/_measure_list.html"

    def delete(self, request, measure_pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        measure = get_object_or_404(ProtectionMeasure.objects.filter(base_filter), pk=measure_pk)
        concept = measure.concept
        measure.delete()

        measures = concept.measures.all()
        measure_form = ProtectionMeasureForm()
        return render(
            request,
            self.partial_template,
            {
                "concept": concept,
                "measures": measures,
                "measure_form": measure_form,
                "htmx_response": True,
            },
        )


class HtmxAddDocumentView(LoginRequiredMixin, View):
    """
    HTMX: Nachweisdokument inline zu Concept hinzufügen.
    POST → Document erstellen, Partial mit aktueller Liste zurückgeben.
    """

    partial_template = "explosionsschutz/partials/_document_list.html"

    def post(self, request, concept_pk):
        tenant_id = getattr(request, "tenant_id", None)
        if not tenant_id:
            return HttpResponseForbidden("Mandant nicht ermittelt.")
        base_filter = Q(tenant_id=tenant_id)
        concept = get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=concept_pk)

        form = VerificationDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.tenant_id = tenant_id
            doc.concept = concept
            doc.uploaded_by = request.user
            doc.save()

        documents = concept.documents.all()
        document_form = VerificationDocumentForm()
        return render(
            request,
            self.partial_template,
            {
                "concept": concept,
                "documents": documents,
                "document_form": document_form,
                "htmx_response": True,
            },
        )


class HtmxIgnitionAssessmentView(LoginRequiredMixin, View):
    """
    HTMX: Zündquellenbewertung für eine Zone.
    GET  → Formular mit 13 Zündquellen
    POST → Bewertung speichern via Service Layer
    """

    partial_template = "explosionsschutz/partials/_ignition_assessment.html"

    def get(self, request, zone_pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        zone = get_object_or_404(ZoneDefinition.objects.filter(base_filter), pk=zone_pk)

        assessments = {a.ignition_source: a for a in zone.ignition_assessments.all()}
        sources = [
            {
                "value": choice[0],
                "label": choice[1],
                "assessment": assessments.get(choice[0]),
            }
            for choice in IgnitionSource.choices
        ]

        return render(
            request,
            self.partial_template,
            {"zone": zone, "sources": sources},
        )

    def post(self, request, zone_pk):
        from .services import AssessIgnitionSourceCmd, assess_ignition_source

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        zone = get_object_or_404(ZoneDefinition.objects.filter(base_filter), pk=zone_pk)
        user_id = getattr(request.user, "id", None)

        ignition_source = request.POST.get("ignition_source")
        if ignition_source:
            cmd = AssessIgnitionSourceCmd(
                zone_id=zone.pk,
                ignition_source=ignition_source,
                is_present=request.POST.get("is_present") == "on",
                is_effective=request.POST.get("is_effective") == "on",
                mitigation=request.POST.get("mitigation", ""),
            )
            assess_ignition_source(cmd, tenant_id=tenant_id, user_id=user_id)

        assessments = {a.ignition_source: a for a in zone.ignition_assessments.all()}
        sources = [
            {
                "value": choice[0],
                "label": choice[1],
                "assessment": assessments.get(choice[0]),
            }
            for choice in IgnitionSource.choices
        ]

        return render(
            request,
            self.partial_template,
            {"zone": zone, "sources": sources, "saved": True},
        )


class HtmxZoneProposalView(LoginRequiredMixin, View):
    """
    HTMX: Zonenvorschlag basierend auf TRGS 721 Regelmatrix.
    POST → ZoneClassificationEngine aufrufen, Ergebnis als Partial.
    """

    partial_template = "explosionsschutz/partials/_zone_proposal.html"

    def get(self, request):
        form = ZoneProposalForm()
        return render(request, self.partial_template, {"form": form, "proposal": None})

    def post(self, request):
        from .services.zone_classification import ZoneClassificationEngine

        form = ZoneProposalForm(request.POST)
        proposal = None
        if form.is_valid():
            engine = ZoneClassificationEngine()
            proposal = engine.propose(
                release_grade=form.cleaned_data["release_grade"],
                ventilation_type=form.cleaned_data["ventilation_type"],
                atmosphere_type=form.cleaned_data["atmosphere_type"],
            )

        return render(
            request,
            self.partial_template,
            {"form": form, "proposal": proposal},
        )


class InspectionCreateView(LoginRequiredMixin, View):
    """Prüfung erfassen für ein Betriebsmittel"""

    template_name = "explosionsschutz/equipment/inspection_form.html"

    def get(self, request, equipment_pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        equipment = get_object_or_404(
            Equipment.objects.filter(base_filter).select_related("equipment_type"),
            pk=equipment_pk,
        )
        form = InspectionForm()
        return render(
            request,
            self.template_name,
            {"equipment": equipment, "form": form, "title": f"Prüfung: {equipment}"},
        )

    def post(self, request, equipment_pk):
        from .services import CreateInspectionCmd, create_inspection

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        equipment = get_object_or_404(
            Equipment.objects.filter(base_filter).select_related("equipment_type"),
            pk=equipment_pk,
        )
        form = InspectionForm(request.POST)
        if form.is_valid():
            cmd = CreateInspectionCmd(
                equipment_id=equipment.pk,
                inspection_type=form.cleaned_data["inspection_type"],
                inspection_date=str(form.cleaned_data["inspection_date"]),
                inspector_name=form.cleaned_data["inspector_name"],
                result=form.cleaned_data["result"],
                findings=form.cleaned_data.get("findings", ""),
                recommendations=form.cleaned_data.get("recommendations", ""),
                certificate_number=form.cleaned_data.get("certificate_number", ""),
            )
            user_id = getattr(request.user, "id", None)
            create_inspection(cmd, tenant_id=tenant_id, user_id=user_id)
            messages.success(request, "Prüfung erfolgreich erfasst.")
            return redirect("explosionsschutz:equipment-detail-html", pk=equipment.pk)
        return render(
            request,
            self.template_name,
            {"equipment": equipment, "form": form, "title": f"Prüfung: {equipment}"},
        )


class ConceptAiGenerateView(LoginRequiredMixin, View):
    """HTMX POST: KI-Vorschlag für einen Konzept-Abschnitt generieren (ADR-018).

    POST /ex/concepts/<pk>/ai/<chapter>/
    Antwort: HTMX-Partial _ai_diff.html oder _ai_error.html
    """

    ALLOWED_CHAPTERS = {"zones", "ignition", "measures", "summary"}

    def post(self, request, pk, chapter):
        from uuid import UUID

        from .ai.dtos import GenerateProposalCmd
        from .ai.feature_flags import ai_enabled_for_tenant
        from .services.ex_concept_ai import generate_chapter

        tenant_id = getattr(request, "tenant_id", None)

        if chapter not in self.ALLOWED_CHAPTERS:
            return HttpResponseForbidden(f"Unknown chapter: {chapter}")

        if not ai_enabled_for_tenant(tenant_id):
            return render(
                request,
                "explosionsschutz/ai/partials/_ai_error.html",
                {"error": "KI-Features sind für diesen Mandanten nicht aktiviert."},
            )

        if not request.user.has_perm("explosionsschutz.use_ai"):
            return render(
                request,
                "explosionsschutz/ai/partials/_ai_error.html",
                {"error": "Keine Berechtigung für KI-Generierung."},
            )

        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"), pk=pk
        )

        cmd = GenerateProposalCmd(
            concept_id=concept.pk,
            tenant_id=UUID(str(tenant_id)),
            chapter=chapter,
            additional_user_notes=request.POST.get("user_notes", ""),
        )

        result = generate_chapter(cmd)

        if not result.success:
            raw_error = result.error or ""
            if any(k in raw_error for k in ("api_key", "AuthenticationError", "Authentication")):
                display_error = "KI-Dienst nicht konfiguriert (API-Key fehlt). Bitte Administrator kontaktieren."
            elif "RateLimit" in raw_error or "rate_limit" in raw_error:
                display_error = "KI-Dienst momentan überlastet. Bitte in wenigen Minuten erneut versuchen."
            elif "Timeout" in raw_error or "timeout" in raw_error:
                display_error = "KI-Dienst hat nicht rechtzeitig geantwortet. Bitte erneut versuchen."
            else:
                display_error = "KI-Generierung fehlgeschlagen. Bitte erneut versuchen."
            return render(
                request,
                "explosionsschutz/ai/partials/_ai_error.html",
                {"error": display_error, "log_id": result.log_id},
            )

        return render(
            request,
            "explosionsschutz/ai/partials/_ai_diff.html",
            {
                "concept": concept,
                "chapter": chapter,
                "result": result,
                "log_id": result.log_id,
            },
        )


class ConceptAiAcceptView(LoginRequiredMixin, View):
    """HTMX POST: KI-Vorschlag durch Experten übernehmen (ADR-018).

    POST /ex/concepts/<pk>/ai/accept/<log_id>/
    """

    def post(self, request, pk, log_id):
        from .ai.dtos import AcceptProposalCmd
        from .services.ex_concept_ai import accept_proposal

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=pk)

        changes_made = request.POST.get("changes_made", "")
        proposal_text = request.POST.get("proposal_text", "")
        cmd = AcceptProposalCmd(
            generation_log_id=log_id,
            accepted_by_user_id=request.user.pk,
            changes_made=changes_made,
            proposal_text=proposal_text,
        )
        log, zone_results = accept_proposal(cmd)

        if request.headers.get("HX-Request"):
            return render(
                request,
                "explosionsschutz/ai/partials/_ai_accepted.html",
                {
                    "log_id": log_id,
                    "response_text": log.response_text,
                    "changes_made": changes_made,
                    "zone_results": zone_results,
                    "chapter": log.chapter,
                },
            )
        messages.success(request, "KI-Vorschlag übernommen.")
        return redirect("explosionsschutz:concept-detail-html", pk=pk)


class ConceptAiRejectView(LoginRequiredMixin, View):
    """HTMX POST: KI-Vorschlag ablehnen (ADR-018).

    POST /ex/concepts/<pk>/ai/reject/<log_id>/
    """

    def post(self, request, pk, log_id):
        from .ai.dtos import RejectProposalCmd
        from .services.ex_concept_ai import reject_proposal

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        get_object_or_404(ExplosionConcept.objects.filter(base_filter), pk=pk)

        cmd = RejectProposalCmd(
            generation_log_id=log_id,
            rejected_by_user_id=request.user.pk,
        )
        reject_proposal(cmd)

        if request.headers.get("HX-Request"):
            return render(
                request,
                "explosionsschutz/ai/partials/_ai_rejected.html",
                {"log_id": log_id},
            )
        messages.info(request, "KI-Vorschlag abgelehnt.")
        return redirect("explosionsschutz:concept-detail-html", pk=pk)
