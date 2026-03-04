# src/explosionsschutz/template_views.py
"""
Template-basierte Views für Explosionsschutz-Modul (HTML-Seiten)
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import (
    AreaForm,
    ConceptDxfImportForm,
    ExplosionConceptForm,
    EquipmentForm,
    ZoneCalculationForm,
)
from .calculations import list_substances
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
            areas = areas.filter(
                explosion_concepts__status__in=["approved", "in_review"]
            ).distinct()
        elif hazard == "0":
            areas = areas.exclude(
                explosion_concepts__status__in=["approved", "in_review"]
            )

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


class ToolsView(View):
    """Berechnungstools für Explosionsschutz"""

    template_name = "explosionsschutz/tools.html"

    def get(self, request):
        substances = list_substances()
        return render(request, self.template_name, {
            "substances": substances,
            "substance_count": len(substances),
        })


class AreaDxfUploadView(View):
    """DXF-Upload für einen Bereich — parst Räume/Flächen via nl2cad-core/areas."""

    template_name = "explosionsschutz/areas/dxf_upload.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)
        return render(request, self.template_name, {"area": area})

    def post(self, request, pk):
        import logging
        from nl2cad.core.parsers.dxf_parser import DXFParser
        from nl2cad.areas.din277 import DIN277Calculator

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        dxf_file = request.FILES.get("dxf_file")
        if not dxf_file:
            return render(request, self.template_name, {
                "area": area,
                "error": "Keine DXF-Datei hochgeladen.",
            })

        if not dxf_file.name.lower().endswith(".dxf"):
            return render(request, self.template_name, {
                "area": area,
                "error": "Nur .dxf Dateien sind erlaubt.",
            })

        try:
            parser = DXFParser()
            dxf_model = parser.parse_bytes(dxf_file.read(), dxf_file.name)
        except Exception as exc:
            logger.warning("[AreaDxfUpload] Parse-Fehler %s: %s", area.code, exc)
            return render(request, self.template_name, {
                "area": area,
                "error": f"DXF konnte nicht gelesen werden: {exc}",
            })

        calc = DIN277Calculator()
        rooms_input = [
            {"name": r.name, "area_m2": r.area_m2, "din277_code": r.din277_code}
            for r in dxf_model.rooms
        ]
        din_result = calc.calculate(rooms_input)

        analysis = {
            "dxf_version": dxf_model.dxf_version,
            "layers_count": len(dxf_model.layers),
            "rooms_count": len(dxf_model.rooms),
            "total_area_m2": round(dxf_model.total_area_m2, 2),
            "rooms": [
                {
                    "name": r.name,
                    "layer": r.layer,
                    "area_m2": round(r.area_m2, 2),
                    "perimeter_m": round(r.perimeter_m, 2),
                    "din277_code": r.din277_code,
                }
                for r in dxf_model.rooms
            ],
            "din277": {
                "ngf_m2": round(din_result.ngf_m2, 2),
                "nf_m2": round(din_result.nf_m2, 2),
                "vf_m2": round(din_result.vf_m2, 2),
                "ff_m2": round(din_result.ff_m2, 2),
            },
        }

        area.dxf_file = dxf_file
        area.dxf_analysis_json = analysis
        area.brandschutz_analysis_json = None  # Neu analysieren nach Upload
        area.save()

        logger.info(
            "[AreaDxfUpload] %s: %d Räume, %.1f m² gespeichert",
            area.code,
            len(dxf_model.rooms),
            dxf_model.total_area_m2,
        )
        return redirect("explosionsschutz:area-brandschutz", pk=area.pk)


class ZoneCalculateView(View):
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
        return render(request, self.template_name, {
            "zone": zone,
            "form": form,
            "history": history,
        })

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
                return render(request, self.partial_template, {
                    "form": form, "zone": zone, "error": None, "result": None,
                })
            history = zone.calculations.order_by("-calculated_at")[:5]
            return render(request, self.template_name, {
                "zone": zone, "form": form, "history": history,
            })

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
                zone_pk, calc.calculated_zone_type, calc.calculated_radius_m,
            )
        except DjangoValidationError as exc:
            error_msg = " ".join(exc.messages)
            if is_htmx:
                return render(request, self.partial_template, {
                    "form": form, "zone": zone, "error": error_msg, "result": None,
                })
            history = zone.calculations.order_by("-calculated_at")[:5]
            return render(request, self.template_name, {
                "zone": zone, "form": form,
                "history": history, "error": error_msg,
            })

        if is_htmx:
            return render(request, self.partial_template, {
                "form": ZoneCalculationForm(initial={"zone_id": zone.pk}),
                "zone": zone,
                "result": calc,
                "error": None,
            })
        return redirect(
            "explosionsschutz:concept-detail-html", pk=zone.concept_id
        )


class ConceptDxfImportView(View):
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
        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter), pk=pk
        )
        return render(request, self.template_name, {
            "concept": concept,
            "form": ConceptDxfImportForm(),
        })

    def post(self, request, pk):
        import logging
        from django.core.exceptions import ValidationError as DjangoValidationError
        from .services import import_zones_from_dxf

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter), pk=pk
        )
        form = ConceptDxfImportForm(request.POST, request.FILES)
        is_htmx = request.headers.get("HX-Request") == "true"

        if not form.is_valid():
            if is_htmx:
                return render(request, self.partial_template, {
                    "concept": concept, "form": form,
                    "error": None, "count": None, "zones": [],
                })
            return render(request, self.template_name, {
                "concept": concept, "form": form,
            })

        dxf_bytes = form.cleaned_data["dxf_file"].read()
        try:
            count = import_zones_from_dxf(
                concept_id=concept.pk,
                dxf_bytes=dxf_bytes,
                tenant_id=tenant_id,
                user_id=getattr(request.user, "id", None),
            )
            logger.info(
                "[DxfImport] Concept %s: %d Zonen importiert", pk, count
            )
        except DjangoValidationError as exc:
            error_msg = " ".join(exc.messages)
            if is_htmx:
                return render(request, self.partial_template, {
                    "concept": concept, "form": form,
                    "error": error_msg, "count": None, "zones": [],
                })
            return render(request, self.template_name, {
                "concept": concept, "form": form, "error": error_msg,
            })

        new_zones = concept.zones.order_by("-created_at")[:count]
        if is_htmx:
            return render(request, self.partial_template, {
                "concept": concept, "form": ConceptDxfImportForm(),
                "error": None, "count": count, "zones": new_zones,
            })
        return redirect(
            "explosionsschutz:concept-detail-html", pk=concept.pk
        )


class AreaBrandschutzView(View):
    """Brandschutz-Layer-Analyse für einen Bereich via nl2cad-brandschutz."""

    template_name = "explosionsschutz/areas/brandschutz.html"

    def get(self, request, pk):
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        analyse = area.brandschutz_analysis_json
        return render(request, self.template_name, {
            "area": area,
            "analyse": analyse,
            "has_dxf": bool(area.dxf_file),
        })

    def post(self, request, pk):
        import logging
        import tempfile
        from nl2cad.brandschutz.analyzer import BrandschutzAnalyzer

        logger = logging.getLogger(__name__)
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()
        area = get_object_or_404(Area.objects.filter(base_filter), pk=pk)

        if not area.dxf_file:
            return render(request, self.template_name, {
                "area": area,
                "error": "Kein DXF hochgeladen. Bitte zuerst DXF hochladen.",
                "has_dxf": False,
            })

        try:
            import ezdxf
            with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
                for chunk in area.dxf_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            doc = ezdxf.readfile(tmp_path)
        except Exception as exc:
            logger.warning("[AreaBrandschutz] DXF-Lesefehler %s: %s", pk, exc)
            return render(request, self.template_name, {
                "area": area,
                "error": f"DXF konnte nicht gelesen werden: {exc}",
                "has_dxf": True,
            })

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
