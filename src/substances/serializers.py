# src/substances/serializers.py
"""DRF Serializers für Substances Module."""

from rest_framework import serializers
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


class PartySerializer(serializers.ModelSerializer):
    """Serializer für Party."""

    class Meta:
        model = Party
        fields = [
            "id", "name", "party_type", "email", "phone",
            "address", "website", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class IdentifierSerializer(serializers.ModelSerializer):
    """Serializer für Identifier."""

    class Meta:
        model = Identifier
        fields = ["id", "id_type", "id_value"]
        read_only_fields = ["id"]


class HazardStatementRefSerializer(serializers.ModelSerializer):
    """Serializer für H-Sätze Referenz."""

    class Meta:
        model = HazardStatementRef
        fields = ["code", "text_de", "text_en", "category"]


class PrecautionaryStatementRefSerializer(serializers.ModelSerializer):
    """Serializer für P-Sätze Referenz."""

    class Meta:
        model = PrecautionaryStatementRef
        fields = ["code", "text_de", "text_en", "category"]


class PictogramRefSerializer(serializers.ModelSerializer):
    """Serializer für Piktogramme Referenz."""

    class Meta:
        model = PictogramRef
        fields = ["code", "name_de", "name_en", "svg_path", "description"]


class SdsRevisionSerializer(serializers.ModelSerializer):
    """Serializer für SDS-Revision."""

    hazard_statements = HazardStatementRefSerializer(many=True, read_only=True)
    precautionary_statements = PrecautionaryStatementRefSerializer(
        many=True, read_only=True
    )
    pictograms = PictogramRefSerializer(many=True, read_only=True)
    substance_name = serializers.CharField(
        source="substance.name", read_only=True
    )

    class Meta:
        model = SdsRevision
        fields = [
            "id", "substance", "substance_name",
            "revision_number", "revision_date",
            "status", "signal_word",
            "hazard_statements", "precautionary_statements", "pictograms",
            "approved_by", "approved_at", "notes",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "approved_by", "approved_at", "created_at", "updated_at"
        ]


class SubstanceSerializer(serializers.ModelSerializer):
    """Serializer für Substance (Liste)."""

    cas_number = serializers.CharField(read_only=True)
    manufacturer_name = serializers.CharField(
        source="manufacturer.name", read_only=True
    )
    current_sds_status = serializers.SerializerMethodField()

    class Meta:
        model = Substance
        fields = [
            "id", "name", "trade_name", "cas_number",
            "status", "storage_class", "is_cmr",
            "manufacturer", "manufacturer_name",
            "current_sds_status",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_current_sds_status(self, obj):
        sds = obj.current_sds
        return sds.status if sds else None


class SubstanceDetailSerializer(serializers.ModelSerializer):
    """Serializer für Substance (Detail)."""

    identifiers = IdentifierSerializer(many=True, read_only=True)
    manufacturer = PartySerializer(read_only=True)
    supplier = PartySerializer(read_only=True)
    current_sds = SdsRevisionSerializer(read_only=True)

    class Meta:
        model = Substance
        fields = [
            "id", "name", "trade_name", "description",
            "status", "storage_class", "is_cmr",
            "manufacturer", "supplier",
            "identifiers", "current_sds",
            "flash_point_c", "ignition_temperature_c",
            "lower_explosion_limit", "upper_explosion_limit",
            "temperature_class", "explosion_group", "vapor_density",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SiteInventoryItemSerializer(serializers.ModelSerializer):
    """Serializer für SiteInventoryItem."""

    substance_name = serializers.CharField(
        source="substance.name", read_only=True
    )
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = SiteInventoryItem
        fields = [
            "id", "substance", "substance_name",
            "site", "site_name",
            "quantity", "unit", "state", "storage_location",
            "responsible_user",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
