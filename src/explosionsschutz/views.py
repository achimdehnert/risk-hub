# src/explosionsschutz/views.py
"""
Django REST Framework Views für Explosionsschutz-Modul

Features:
- TenantAwareViewSet für Multi-Tenancy
- Custom Actions für Workflow
- Optimierte Queries mit select_related/prefetch_related
"""

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.views import (
    TenantAwareViewSet,
    ReadOnlyMasterDataViewSet,
)

from .models import (
    ReferenceStandard,
    MeasureCatalog,
    SafetyFunction,
    EquipmentType,
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    Inspection,
    VerificationDocument,
    ZoneIgnitionSourceAssessment,
)
from .serializers import (
    ReferenceStandardSerializer,
    MeasureCatalogSerializer,
    SafetyFunctionSerializer,
    EquipmentTypeSerializer,
    AreaSerializer,
    AreaDetailSerializer,
    ExplosionConceptSerializer,
    ExplosionConceptDetailSerializer,
    ZoneDefinitionSerializer,
    ProtectionMeasureSerializer,
    EquipmentSerializer,
    EquipmentDetailSerializer,
    InspectionSerializer,
    VerificationDocumentSerializer,
    ZoneIgnitionSourceAssessmentSerializer,
)
from .services import (
    create_explosion_concept,
    validate_explosion_concept,
    archive_explosion_concept,
    CreateExplosionConceptCmd,
    ValidateExplosionConceptCmd,
)
from .calculations import (
    get_substance_properties,
    list_substances,
    calculate_zone_extent,
    analyze_ventilation_effectiveness,
    check_equipment_suitability,
)


# =============================================================================
# STAMMDATEN VIEWSETS
# =============================================================================

class ReferenceStandardViewSet(ReadOnlyMasterDataViewSet):
    """API für Regelwerksreferenzen"""
    queryset = ReferenceStandard.objects.all()
    serializer_class = ReferenceStandardSerializer
    filterset_fields = ["category", "is_system"]
    search_fields = ["code", "title"]
    ordering = ["code"]


class MeasureCatalogViewSet(ReadOnlyMasterDataViewSet):
    """API für Maßnahmenkatalog"""
    queryset = MeasureCatalog.objects.prefetch_related("reference_standards")
    serializer_class = MeasureCatalogSerializer
    filterset_fields = ["default_type", "is_system"]
    search_fields = ["code", "title"]
    ordering = ["code"]


class SafetyFunctionViewSet(ReadOnlyMasterDataViewSet):
    """API für MSR-Sicherheitsfunktionen"""
    queryset = SafetyFunction.objects.prefetch_related("reference_standards")
    serializer_class = SafetyFunctionSerializer
    filterset_fields = ["performance_level", "sil_level", "is_system"]
    search_fields = ["name"]
    ordering = ["name"]


class EquipmentTypeViewSet(ReadOnlyMasterDataViewSet):
    """API für Betriebsmitteltypen"""
    queryset = EquipmentType.objects.all()
    serializer_class = EquipmentTypeSerializer
    filterset_fields = [
        "atex_group",
        "atex_category",
        "protection_type",
        "temperature_class",
        "is_system",
    ]
    search_fields = ["manufacturer", "model", "certificate_number"]
    ordering = ["manufacturer", "model"]


# =============================================================================
# CORE VIEWSETS
# =============================================================================

class AreaViewSet(TenantAwareViewSet):
    """API für Betriebsbereiche"""
    queryset = Area.objects.all()
    filterset_fields = ["site_id"]
    search_fields = ["code", "name"]
    ordering = ["code"]
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return AreaDetailSerializer
        return AreaSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            return qs.prefetch_related(
                "concepts",
                "equipment",
            )
        return qs


class ExplosionConceptViewSet(TenantAwareViewSet):
    """API für Explosionsschutzkonzepte"""
    queryset = ExplosionConcept.objects.select_related("area")
    filterset_fields = ["status", "is_validated", "area_id"]
    search_fields = ["title", "area__name"]
    ordering = ["-created_at"]
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return ExplosionConceptDetailSerializer
        return ExplosionConceptSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            return qs.prefetch_related(
                "zones",
                "zones__ignition_assessments",
                "measures",
                "documents",
            )
        return qs
    
    def perform_create(self, serializer):
        """Verwendet Service Layer für Erstellung"""
        tenant_id = self.get_tenant_id()
        user_id = self.request.user.id if self.request.user else None
        
        cmd = CreateExplosionConceptCmd(
            area_id=serializer.validated_data["area"].id,
            substance_id=serializer.validated_data["substance"].id,
            title=serializer.validated_data["title"],
            assessment_id=serializer.validated_data.get("assessment_id"),
        )
        
        concept = create_explosion_concept(cmd, tenant_id, user_id)
        serializer.instance = concept
    
    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        """Validiert ein Ex-Konzept"""
        concept = self.get_object()
        tenant_id = self.get_tenant_id()
        user_id = request.user.id if request.user else None
        
        try:
            cmd = ValidateExplosionConceptCmd(
                concept_id=concept.id,
                notes=request.data.get("notes"),
            )
            validated = validate_explosion_concept(cmd, tenant_id, user_id)
            return Response(
                ExplosionConceptSerializer(validated).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archiviert ein Ex-Konzept"""
        concept = self.get_object()
        tenant_id = self.get_tenant_id()
        user_id = request.user.id if request.user else None
        
        try:
            archived = archive_explosion_concept(concept.id, tenant_id, user_id)
            return Response(
                ExplosionConceptSerializer(archived).data,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=["get"])
    def export_pdf(self, request, pk=None):
        """Exportiert Ex-Konzept als PDF"""
        concept = self.get_object()
        return Response(
            {"message": "PDF export not yet implemented", "concept_id": str(concept.id)},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )

    @action(detail=True, methods=["get"])
    def export_docx(self, request, pk=None):
        """Exportiert Ex-Konzept als Word-Dokument"""
        from django.http import HttpResponse
        from .document_generator import ExSchutzDocumentGenerator

        concept = self.get_object()
        generator = ExSchutzDocumentGenerator(concept)

        try:
            generator.create_document()
            buffer = generator.save_to_buffer()
            filename = generator.get_filename()

            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document"
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except ImportError:
            return Response(
                {"error": "python-docx nicht installiert"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )

    @action(detail=True, methods=["get"])
    def preview_html(self, request, pk=None):
        """HTML-Vorschau des Ex-Konzepts"""
        from django.http import HttpResponse
        from .document_generator import ExSchutzDocumentGenerator

        concept = self.get_object()
        generator = ExSchutzDocumentGenerator(concept)
        html = generator.get_html_preview()

        return HttpResponse(html, content_type="text/html")


class ZoneDefinitionViewSet(TenantAwareViewSet):
    """API für Zonendefinitionen"""
    queryset = ZoneDefinition.objects.select_related("concept", "reference_standard")
    serializer_class = ZoneDefinitionSerializer
    filterset_fields = ["zone_type", "concept_id"]
    search_fields = ["name"]
    ordering = ["concept_id", "zone_type"]
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related("ignition_assessments")


class ProtectionMeasureViewSet(TenantAwareViewSet):
    """API für Schutzmaßnahmen"""
    queryset = ProtectionMeasure.objects.select_related(
        "concept",
        "catalog_reference",
        "safety_function"
    )
    serializer_class = ProtectionMeasureSerializer
    filterset_fields = ["category", "status", "concept_id"]
    search_fields = ["title", "description"]
    ordering = ["concept_id", "category"]


class EquipmentViewSet(TenantAwareViewSet):
    """API für Betriebsmittel"""
    queryset = Equipment.objects.select_related("equipment_type", "area", "zone")
    filterset_fields = ["status", "area_id", "zone_id", "equipment_type_id"]
    search_fields = ["serial_number", "asset_number"]
    ordering = ["-created_at"]
    
    def get_serializer_class(self):
        if self.action == "retrieve":
            return EquipmentDetailSerializer
        return EquipmentSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "retrieve":
            return qs.prefetch_related("inspections")
        return qs
    
    @action(detail=False, methods=["get"])
    def due_for_inspection(self, request):
        """Listet Betriebsmittel mit fälliger Prüfung"""
        qs = self.get_queryset().filter(
            Q(next_inspection_date__lte=timezone.now().date()) |
            Q(next_inspection_date__isnull=True, status="active")
        )
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class InspectionViewSet(TenantAwareViewSet):
    """API für Prüfungen"""
    queryset = Inspection.objects.select_related("equipment", "equipment__equipment_type")
    serializer_class = InspectionSerializer
    filterset_fields = ["inspection_type", "result", "equipment_id"]
    search_fields = ["inspector_name", "certificate_number"]
    ordering = ["-inspection_date"]


class VerificationDocumentViewSet(TenantAwareViewSet):
    """API für Nachweisdokumente"""
    queryset = VerificationDocument.objects.select_related("concept")
    serializer_class = VerificationDocumentSerializer
    filterset_fields = ["document_type", "concept_id"]
    search_fields = ["title", "issued_by"]
    ordering = ["-issued_at"]


# =============================================================================
# REPORTS & DASHBOARD
# =============================================================================

class DashboardView(APIView):
    """Dashboard-Übersicht für Explosionsschutz"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"error": "Tenant erforderlich"}, status=400)
        
        today = timezone.now().date()
        
        # Statistiken
        concepts = ExplosionConcept.objects.filter(tenant_id=tenant_id)
        equipment = Equipment.objects.filter(tenant_id=tenant_id)
        
        return Response({
            "concepts": {
                "total": concepts.count(),
                "draft": concepts.filter(status="draft").count(),
                "approved": concepts.filter(status="approved").count(),
                "archived": concepts.filter(status="archived").count(),
            },
            "equipment": {
                "total": equipment.count(),
                "active": equipment.filter(status="active").count(),
                "inspection_due": equipment.filter(
                    next_inspection_date__lte=today
                ).count(),
                "inspection_soon": equipment.filter(
                    next_inspection_date__gt=today,
                    next_inspection_date__lte=today + timezone.timedelta(days=30)
                ).count(),
            },
            "zones": {
                "by_type": list(
                    ZoneDefinition.objects.filter(tenant_id=tenant_id)
                    .values("zone_type")
                    .annotate(count=Count("id"))
                    .order_by("zone_type")
                ),
            },
            "measures": {
                "open": ProtectionMeasure.objects.filter(
                    tenant_id=tenant_id, status="open"
                ).count(),
                "overdue": ProtectionMeasure.objects.filter(
                    tenant_id=tenant_id,
                    status__in=["open", "in_progress"],
                    due_date__lt=today
                ).count(),
            },
        })


class InspectionsDueReportView(APIView):
    """Report: Fällige und bald fällige Prüfungen"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"error": "Tenant erforderlich"}, status=400)
        
        days = int(request.query_params.get("days", 30))
        today = timezone.now().date()
        
        equipment = Equipment.objects.filter(
            tenant_id=tenant_id,
            status="active"
        ).select_related("equipment_type", "area", "zone")
        
        overdue = equipment.filter(next_inspection_date__lt=today)
        due_soon = equipment.filter(
            next_inspection_date__gte=today,
            next_inspection_date__lte=today + timezone.timedelta(days=days)
        )
        
        return Response({
            "overdue": EquipmentSerializer(overdue, many=True).data,
            "due_within_days": EquipmentSerializer(due_soon, many=True).data,
            "days": days,
        })


class ZoneSummaryReportView(APIView):
    """Report: Zonenübersicht nach Bereich"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        tenant_id = getattr(request.user, "tenant_id", None)
        if not tenant_id:
            return Response({"error": "Tenant erforderlich"}, status=400)
        
        areas = Area.objects.filter(tenant_id=tenant_id).prefetch_related(
            "concepts__zones"
        )
        
        result = []
        for area in areas:
            zones_by_type = {}
            for concept in area.concepts.filter(status="approved"):
                for zone in concept.zones.all():
                    zones_by_type[zone.zone_type] = zones_by_type.get(zone.zone_type, 0) + 1
            
            result.append({
                "area_id": str(area.id),
                "area_code": area.code,
                "area_name": area.name,
                "zones": zones_by_type,
                "has_ex_hazard": area.has_explosion_hazard,
            })
        
        return Response(result)


# =============================================================================
# CALCULATION TOOLS (migriert von expert_hub)
# =============================================================================


class SubstanceListView(APIView):
    """Liste aller verfügbaren Stoffe in der Datenbank."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        return Response({
            "success": True,
            "substances": list_substances(),
            "count": len(list_substances()),
        })


class SubstanceDetailView(APIView):
    """Stoffeigenschaften für einen bestimmten Stoff."""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, name: str):
        result = get_substance_properties(name)
        if result.get("success"):
            return Response(result)
        return Response(result, status=404)


class ZoneCalculateView(APIView):
    """
    Zonenberechnung nach TRGS 721.
    
    POST: {
        "release_rate_kg_s": 0.001,
        "ventilation_rate_m3_s": 0.5,
        "substance_name": "aceton",  // optional
        "room_volume_m3": 100,       // optional
        "release_type": "jet"        // jet, pool, diffuse
    }
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data
        
        try:
            result = calculate_zone_extent(
                release_rate_kg_s=float(data.get("release_rate_kg_s", 0.001)),
                ventilation_rate_m3_s=float(data.get("ventilation_rate_m3_s", 0.5)),
                substance_name=data.get("substance_name"),
                room_volume_m3=float(data["room_volume_m3"]) if data.get("room_volume_m3") else None,
                release_type=data.get("release_type", "jet"),
            )
            return Response(result)
        except (ValueError, TypeError) as e:
            return Response({"success": False, "error": str(e)}, status=400)


class EquipmentCheckView(APIView):
    """
    Equipment-Eignungsprüfung nach ATEX.
    
    POST: {
        "ex_marking": "II 2G Ex d IIB T4",
        "zone": "1"
    }
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data
        
        ex_marking = data.get("ex_marking", "")
        zone = data.get("zone", "1")
        
        if not ex_marking:
            return Response({
                "success": False,
                "error": "ex_marking ist erforderlich"
            }, status=400)
        
        result = check_equipment_suitability(ex_marking, zone)
        return Response(result)


class VentilationAnalyzeView(APIView):
    """
    Lüftungseffektivität nach TRGS 722.
    
    POST: {
        "room_volume_m3": 100,
        "air_flow_m3_h": 1000,
        "ventilation_type": "technisch"  // technisch, natürlich, keine
    }
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data
        
        try:
            result = analyze_ventilation_effectiveness(
                room_volume_m3=float(data.get("room_volume_m3", 100)),
                air_flow_m3_h=float(data.get("air_flow_m3_h", 1000)),
                ventilation_type=data.get("ventilation_type", "technisch"),
            )
            return Response(result)
        except (ValueError, TypeError) as e:
            return Response({"success": False, "error": str(e)}, status=400)
