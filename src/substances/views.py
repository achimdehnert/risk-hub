# src/substances/views.py
"""API Views für Substances Module."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.views import ReadOnlyRefViewSet, TenantAwareViewSet

from .models import (
    HazardStatementRef,
    Party,
    PictogramRef,
    PrecautionaryStatementRef,
    SdsRevision,
    SiteInventoryItem,
    Substance,
)
from .serializers import (
    HazardStatementRefSerializer,
    PartySerializer,
    PictogramRefSerializer,
    PrecautionaryStatementRefSerializer,
    SdsRevisionSerializer,
    SiteInventoryItemSerializer,
    SubstanceDetailSerializer,
    SubstanceSerializer,
)

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

    queryset = Substance.objects.select_related("manufacturer", "supplier").prefetch_related(
        "identifiers", "sds_revisions"
    )
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

    queryset = SdsRevision.objects.select_related("substance").prefetch_related(
        "hazard_statements",
        "precautionary_statements",
        "pictograms",
    )
    serializer_class = SdsRevisionSerializer
    filterset_fields = ["status", "signal_word", "substance_id"]
    search_fields = ["substance__name"]
    ordering = ["-revision_date"]


class SdsUploadView(APIView):
    """Upload einer neuen SDS-Revision — speichert PDF in S3 + DocumentVersion."""

    def post(self, request, pk):
        from .services import upload_sds_revision

        tenant_id = getattr(request, "tenant_id", None)
        try:
            substance = Substance.objects.get(
                id=pk, tenant_id=tenant_id,
            )
        except Substance.DoesNotExist:
            return Response(
                {"error": "Stoff nicht gefunden"},
                status=status.HTTP_404_NOT_FOUND,
            )

        pdf_file = request.FILES.get("file")
        if not pdf_file:
            return Response(
                {"error": "Keine Datei hochgeladen"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        revision_date = request.data.get("revision_date")
        if not revision_date:
            return Response(
                {"error": "revision_date erforderlich (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sds = upload_sds_revision(
                tenant_id=tenant_id,
                substance=substance,
                pdf_content=pdf_file.read(),
                filename=pdf_file.name,
                content_type=(
                    pdf_file.content_type or "application/pdf"
                ),
                revision_date=revision_date,
                notes=request.data.get("notes", ""),
            )
        except RuntimeError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            SdsRevisionSerializer(sds).data,
            status=status.HTTP_201_CREATED,
        )


class SdsApproveView(APIView):
    """Freigabe einer SDS-Revision."""

    def post(self, request, pk):
        """Gibt SDS frei."""
        from .services import approve_sds_revision

        tenant_id = getattr(request, "tenant_id", None)
        user_id = request.user.id if request.user else None

        try:
            sds = SdsRevision.objects.get(
                id=pk, tenant_id=tenant_id,
            )
        except SdsRevision.DoesNotExist:
            return Response(
                {"error": "SDS nicht gefunden"},
                status=status.HTTP_404_NOT_FOUND,
            )

        sds = approve_sds_revision(sds, user_id=user_id)
        return Response(
            SdsRevisionSerializer(sds).data,
            status=status.HTTP_200_OK,
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
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = 'attachment; filename="Gefahrstoffverzeichnis.xlsx"'
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
