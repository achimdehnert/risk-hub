# src/substances/views.py
"""API Views für Substances Module."""

from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import (
    Party,
    Substance,
    Identifier,
    SdsRevision,
    SiteInventoryItem,
    HazardStatementRef,
    PrecautionaryStatementRef,
    PictogramRef,
)
from .serializers import (
    PartySerializer,
    SubstanceSerializer,
    SubstanceDetailSerializer,
    SdsRevisionSerializer,
    SiteInventoryItemSerializer,
    HazardStatementRefSerializer,
    PrecautionaryStatementRefSerializer,
    PictogramRefSerializer,
)


# =============================================================================
# BASE VIEWSETS
# =============================================================================

class TenantAwareViewSet(viewsets.ModelViewSet):
    """Basis-ViewSet mit Tenant-Filterung."""

    def get_tenant_id(self):
        """Holt Tenant-ID aus Request."""
        return getattr(self.request, "tenant_id", None)

    def get_queryset(self):
        """Filtert nach Tenant."""
        qs = super().get_queryset()
        tenant_id = self.get_tenant_id()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def perform_create(self, serializer):
        """Setzt Tenant-ID bei Erstellung."""
        tenant_id = self.get_tenant_id()
        user_id = self.request.user.id if self.request.user else None
        serializer.save(tenant_id=tenant_id, created_by=user_id)


class ReadOnlyRefViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-Only ViewSet für Referenzdaten."""
    permission_classes = [permissions.AllowAny]


# =============================================================================
# PARTY
# =============================================================================

class PartyViewSet(TenantAwareViewSet):
    """API für Hersteller/Lieferanten."""
    queryset = Party.objects.all()
    serializer_class = PartySerializer
    filterset_fields = ["party_type"]
    search_fields = ["name", "email"]
    ordering = ["name"]


# =============================================================================
# SUBSTANCE
# =============================================================================

class SubstanceViewSet(TenantAwareViewSet):
    """API für Gefahrstoffe."""
    queryset = Substance.objects.select_related(
        "manufacturer", "supplier"
    ).prefetch_related("identifiers", "sds_revisions")
    serializer_class = SubstanceSerializer
    filterset_fields = ["status", "storage_class", "is_cmr"]
    search_fields = ["name", "trade_name", "description"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SubstanceDetailSerializer
        return SubstanceSerializer

    @action(detail=True, methods=["get"])
    def sds_history(self, request, pk=None):
        """Gibt SDS-Revisionsverlauf zurück."""
        substance = self.get_object()
        revisions = substance.sds_revisions.all()
        serializer = SdsRevisionSerializer(revisions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        """Gibt Inventar-Einträge für diesen Stoff zurück."""
        substance = self.get_object()
        items = substance.inventory_items.select_related("site").all()
        serializer = SiteInventoryItemSerializer(items, many=True)
        return Response(serializer.data)


# =============================================================================
# SDS REVISION
# =============================================================================

class SdsRevisionViewSet(TenantAwareViewSet):
    """API für SDS-Revisionen."""
    queryset = SdsRevision.objects.select_related(
        "substance"
    ).prefetch_related(
        "hazard_statements",
        "precautionary_statements",
        "pictograms",
    )
    serializer_class = SdsRevisionSerializer
    filterset_fields = ["status", "signal_word", "substance_id"]
    search_fields = ["substance__name"]
    ordering = ["-revision_date"]


class SdsUploadView(APIView):
    """Upload einer neuen SDS-Revision."""

    def post(self, request, pk):
        """Lädt neues SDS hoch."""
        # TODO: Implementieren mit document-upload
        return Response(
            {"message": "SDS upload not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class SdsApproveView(APIView):
    """Freigabe einer SDS-Revision."""

    def post(self, request, pk):
        """Gibt SDS frei."""
        from django.utils import timezone

        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user else None

        try:
            sds = SdsRevision.objects.get(id=pk, tenant_id=tenant_id)

            # Vorherige freigegebene Revisionen archivieren
            sds.substance.sds_revisions.filter(
                status=SdsRevision.Status.APPROVED
            ).update(status=SdsRevision.Status.ARCHIVED)

            # Diese Revision freigeben
            sds.status = SdsRevision.Status.APPROVED
            sds.approved_by = user_id
            sds.approved_at = timezone.now()
            sds.save()

            return Response(
                SdsRevisionSerializer(sds).data,
                status=status.HTTP_200_OK
            )
        except SdsRevision.DoesNotExist:
            return Response(
                {"error": "SDS nicht gefunden"},
                status=status.HTTP_404_NOT_FOUND
            )


# =============================================================================
# SITE INVENTORY
# =============================================================================

class SiteInventoryViewSet(TenantAwareViewSet):
    """API für Standort-Inventar."""
    queryset = SiteInventoryItem.objects.select_related("substance", "site")
    serializer_class = SiteInventoryItemSerializer
    filterset_fields = ["site_id", "substance_id", "state"]
    search_fields = ["substance__name", "storage_location"]
    ordering = ["substance__name"]


# =============================================================================
# REFERENZDATEN
# =============================================================================

class HazardStatementRefViewSet(ReadOnlyRefViewSet):
    """API für H-Sätze Referenz."""
    queryset = HazardStatementRef.objects.all()
    serializer_class = HazardStatementRefSerializer
    filterset_fields = ["category"]
    search_fields = ["code", "text_de"]


class PrecautionaryStatementRefViewSet(ReadOnlyRefViewSet):
    """API für P-Sätze Referenz."""
    queryset = PrecautionaryStatementRef.objects.all()
    serializer_class = PrecautionaryStatementRefSerializer
    filterset_fields = ["category"]
    search_fields = ["code", "text_de"]


class PictogramRefViewSet(ReadOnlyRefViewSet):
    """API für Piktogramme Referenz."""
    queryset = PictogramRef.objects.all()
    serializer_class = PictogramRefSerializer
    search_fields = ["code", "name_de"]


# =============================================================================
# EXPORTS
# =============================================================================

class HazardRegisterExportView(APIView):
    """Export Gefahrstoffverzeichnis als Excel."""

    def get(self, request):
        """Generiert Excel-Export."""
        from .exports import generate_hazard_register_excel

        tenant_id = getattr(request, "tenant_id", None)
        site_id = request.query_params.get("site_id")

        try:
            buffer = generate_hazard_register_excel(tenant_id, site_id)
            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument"
                             ".spreadsheetml.sheet"
            )
            response["Content-Disposition"] = (
                'attachment; filename="Gefahrstoffverzeichnis.xlsx"'
            )
            return response
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
