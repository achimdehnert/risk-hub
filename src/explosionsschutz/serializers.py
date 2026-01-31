# src/explosionsschutz/serializers.py
"""
Django REST Framework Serializers für Explosionsschutz-Modul
"""

from rest_framework import serializers

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


# =============================================================================
# STAMMDATEN SERIALIZERS
# =============================================================================

class ReferenceStandardSerializer(serializers.ModelSerializer):
    """Serializer für Regelwerksreferenzen"""

    class Meta:
        model = ReferenceStandard
        fields = [
            "id",
            "code",
            "title",
            "category",
            "url",
            "valid_from",
            "valid_until",
            "is_system",
        ]
        read_only_fields = ["id", "is_system"]


class MeasureCatalogSerializer(serializers.ModelSerializer):
    """Serializer für Maßnahmenkatalog"""

    reference_standards = ReferenceStandardSerializer(many=True, read_only=True)
    reference_standard_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = MeasureCatalog
        fields = [
            "id",
            "code",
            "title",
            "description_template",
            "default_type",
            "reference_standards",
            "reference_standard_ids",
            "is_system",
        ]
        read_only_fields = ["id", "is_system"]


class SafetyFunctionSerializer(serializers.ModelSerializer):
    """Serializer für MSR-Sicherheitsfunktionen"""

    reference_standards = ReferenceStandardSerializer(many=True, read_only=True)

    class Meta:
        model = SafetyFunction
        fields = [
            "id",
            "name",
            "description",
            "performance_level",
            "sil_level",
            "monitoring_method",
            "test_interval_months",
            "reference_standards",
            "is_system",
        ]
        read_only_fields = ["id", "is_system"]


class EquipmentTypeSerializer(serializers.ModelSerializer):
    """Serializer für Betriebsmitteltypen"""

    full_atex_marking = serializers.ReadOnlyField()
    allowed_zones = serializers.ReadOnlyField()

    class Meta:
        model = EquipmentType
        fields = [
            "id",
            "manufacturer",
            "model",
            "description",
            "atex_group",
            "atex_category",
            "protection_type",
            "explosion_group",
            "temperature_class",
            "epl",
            "ip_rating",
            "ambient_temp_min",
            "ambient_temp_max",
            "default_inspection_interval_months",
            "datasheet_url",
            "certificate_number",
            "notified_body",
            "full_atex_marking",
            "allowed_zones",
            "is_system",
        ]
        read_only_fields = ["id", "full_atex_marking", "allowed_zones", "is_system"]


# =============================================================================
# CORE SERIALIZERS
# =============================================================================

class AreaSerializer(serializers.ModelSerializer):
    """Serializer für Betriebsbereiche"""

    class Meta:
        model = Area
        fields = [
            "id",
            "site_id",
            "code",
            "name",
            "description",
            "has_explosion_hazard",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AreaDetailSerializer(AreaSerializer):
    """Detail-Serializer für Betriebsbereiche mit Relationen"""

    concept_count = serializers.SerializerMethodField()
    equipment_count = serializers.SerializerMethodField()

    class Meta(AreaSerializer.Meta):
        fields = AreaSerializer.Meta.fields + [
            "concept_count",
            "equipment_count",
        ]

    def get_concept_count(self, obj):
        return obj.concepts.count()

    def get_equipment_count(self, obj):
        return obj.equipment.count()


class ZoneIgnitionSourceAssessmentSerializer(serializers.ModelSerializer):
    """Serializer für Zündquellenbewertung"""

    ignition_source_display = serializers.CharField(
        source="get_ignition_source_display",
        read_only=True
    )

    class Meta:
        model = ZoneIgnitionSourceAssessment
        fields = [
            "id",
            "ignition_source",
            "ignition_source_display",
            "is_present",
            "is_effective",
            "mitigation",
            "assessed_by_id",
            "assessed_at",
        ]
        read_only_fields = ["id", "assessed_at"]


class ZoneDefinitionSerializer(serializers.ModelSerializer):
    """Serializer für Zonendefinitionen"""

    zone_type_display = serializers.CharField(
        source="get_zone_type_display",
        read_only=True
    )
    reference_standard = ReferenceStandardSerializer(read_only=True)
    reference_standard_id = serializers.UUIDField(write_only=True, required=False)
    ignition_assessments = ZoneIgnitionSourceAssessmentSerializer(
        many=True,
        read_only=True
    )
    required_equipment_category = serializers.ReadOnlyField()

    class Meta:
        model = ZoneDefinition
        fields = [
            "id",
            "concept_id",
            "zone_type",
            "zone_type_display",
            "name",
            "extent",
            "extent_horizontal_m",
            "extent_vertical_m",
            "justification",
            "reference_standard",
            "reference_standard_id",
            "reference_section",
            "ignition_assessments",
            "required_equipment_category",
        ]
        read_only_fields = ["id", "required_equipment_category"]


class ProtectionMeasureSerializer(serializers.ModelSerializer):
    """Serializer für Schutzmaßnahmen"""

    category_display = serializers.CharField(
        source="get_category_display",
        read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    catalog_reference = MeasureCatalogSerializer(read_only=True)
    catalog_reference_id = serializers.UUIDField(write_only=True, required=False)
    safety_function = SafetyFunctionSerializer(read_only=True)
    safety_function_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = ProtectionMeasure
        fields = [
            "id",
            "concept_id",
            "category",
            "category_display",
            "title",
            "description",
            "catalog_reference",
            "catalog_reference_id",
            "safety_function",
            "safety_function_id",
            "status",
            "status_display",
            "responsible_user_id",
            "due_date",
            "verified_by_id",
            "verified_at",
            "verification_notes",
            "is_safety_device",
        ]
        read_only_fields = ["id", "verified_at"]


class VerificationDocumentSerializer(serializers.ModelSerializer):
    """Serializer für Nachweisdokumente"""

    document_type_display = serializers.CharField(
        source="get_document_type_display",
        read_only=True
    )

    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "concept_id",
            "document_id",
            "title",
            "document_type",
            "document_type_display",
            "issued_by",
            "issued_at",
            "valid_until",
            "notes",
        ]
        read_only_fields = ["id"]


class ExplosionConceptSerializer(serializers.ModelSerializer):
    """Serializer für Explosionsschutzkonzepte"""

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    area_name = serializers.CharField(source="area.name", read_only=True)
    substance_name = serializers.CharField(source="substance.name", read_only=True)
    completion_percentage = serializers.ReadOnlyField()

    class Meta:
        model = ExplosionConcept
        fields = [
            "id",
            "area_id",
            "area_name",
            "substance_id",
            "substance_name",
            "assessment_id",
            "title",
            "version",
            "status",
            "status_display",
            "is_validated",
            "validated_by_id",
            "validated_at",
            "completion_percentage",
            "created_by_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "is_validated",
            "validated_by_id",
            "validated_at",
            "completion_percentage",
            "created_at",
            "updated_at",
        ]


class ExplosionConceptDetailSerializer(ExplosionConceptSerializer):
    """Detail-Serializer für Ex-Konzepte mit allen Relationen"""

    zones = ZoneDefinitionSerializer(many=True, read_only=True)
    measures = ProtectionMeasureSerializer(many=True, read_only=True)
    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta(ExplosionConceptSerializer.Meta):
        fields = ExplosionConceptSerializer.Meta.fields + [
            "zones",
            "measures",
            "documents",
        ]


class InspectionSerializer(serializers.ModelSerializer):
    """Serializer für Prüfungen"""

    inspection_type_display = serializers.CharField(
        source="get_inspection_type_display",
        read_only=True
    )
    result_display = serializers.CharField(
        source="get_result_display",
        read_only=True
    )
    equipment_serial = serializers.CharField(
        source="equipment.serial_number",
        read_only=True
    )
    equipment_type = serializers.CharField(
        source="equipment.equipment_type.model",
        read_only=True
    )

    class Meta:
        model = Inspection
        fields = [
            "id",
            "equipment_id",
            "equipment_serial",
            "equipment_type",
            "inspection_type",
            "inspection_type_display",
            "inspection_date",
            "inspector_name",
            "inspector_qualification",
            "result",
            "result_display",
            "findings",
            "recommendations",
            "certificate_number",
            "next_inspection_date",
            "created_by_id",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class EquipmentSerializer(serializers.ModelSerializer):
    """Serializer für Betriebsmittel"""

    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True
    )
    equipment_type_detail = EquipmentTypeSerializer(
        source="equipment_type",
        read_only=True
    )
    zone_type = serializers.CharField(source="zone.zone_type", read_only=True)
    is_inspection_due = serializers.ReadOnlyField()

    class Meta:
        model = Equipment
        fields = [
            "id",
            "equipment_type_id",
            "equipment_type_detail",
            "area_id",
            "zone_id",
            "zone_type",
            "serial_number",
            "asset_number",
            "location_detail",
            "status",
            "status_display",
            "installation_date",
            "last_inspection_date",
            "next_inspection_date",
            "inspection_interval_months",
            "is_inspection_due",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_inspection_due",
            "created_at",
            "updated_at",
        ]


class EquipmentDetailSerializer(EquipmentSerializer):
    """Detail-Serializer für Betriebsmittel mit Inspections"""

    inspections = InspectionSerializer(many=True, read_only=True)

    class Meta(EquipmentSerializer.Meta):
        fields = EquipmentSerializer.Meta.fields + ["inspections"]
