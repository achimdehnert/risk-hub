# src/explosionsschutz/services/__init__.py
"""
Explosionsschutz Service Layer (v6)

Alle Mutationen laufen über diesen Service Layer:
- Command DTOs für typsichere Eingaben
- @transaction.atomic für Konsistenz
- emit_audit_event() für Compliance
- OutboxMessage für async Verarbeitung

Sub-Module:
- zone_classification: Regelbasierte Zoneneinteilung nach TRGS 721
"""

from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from permissions.authz import require_permission

from ..models import (
    Area,
    Equipment,
    EquipmentATEXCheck,
    EquipmentType,
    ExplosionConcept,
    IgnitionSource,
    Inspection,
    MeasureCatalog,
    ProtectionMeasure,
    ReferenceStandard,
    SafetyFunction,
    ZoneCalculationResult,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)

# =============================================================================
# COMMAND DTOs (Data Transfer Objects)
# =============================================================================


@dataclass(frozen=True)
class CreateExplosionConceptCmd:
    """Command für Erstellung eines neuen Ex-Konzepts"""

    area_id: UUID
    substance_id: UUID
    title: str
    assessment_id: UUID | None = None


@dataclass(frozen=True)
class UpdateExplosionConceptCmd:
    """Command für Aktualisierung eines Ex-Konzepts"""

    concept_id: UUID
    title: str | None = None
    substance_id: UUID | None = None


@dataclass(frozen=True)
class ValidateExplosionConceptCmd:
    """Command für Validierung/Freigabe eines Ex-Konzepts"""

    concept_id: UUID
    notes: str | None = None


@dataclass(frozen=True)
class CreateZoneDefinitionCmd:
    """Command für Erstellung einer Zonendefinition"""

    concept_id: UUID
    zone_type: str
    name: str
    extent: dict | None = None
    reference_standard_id: UUID | None = None
    justification: str | None = None


@dataclass(frozen=True)
class CreateProtectionMeasureCmd:
    """Command für Erstellung einer Schutzmaßnahme"""

    concept_id: UUID
    category: str
    title: str
    description: str | None = None
    catalog_reference_id: UUID | None = None
    safety_function_id: UUID | None = None
    due_date: str | None = None


@dataclass(frozen=True)
class CreateEquipmentCmd:
    """Command für Registrierung eines Betriebsmittels"""

    area_id: UUID
    equipment_type_id: UUID
    zone_id: UUID | None = None
    serial_number: str | None = None
    asset_number: str | None = None
    location_detail: str | None = None
    installation_date: str | None = None


@dataclass(frozen=True)
class CreateInspectionCmd:
    """Command für Erfassung einer Prüfung"""

    equipment_id: UUID
    inspection_type: str
    inspection_date: str
    inspector_name: str
    result: str
    findings: str | None = None
    recommendations: str | None = None
    certificate_number: str | None = None


@dataclass(frozen=True)
class AssessIgnitionSourceCmd:
    """Command für Zündquellenbewertung"""

    zone_id: UUID
    ignition_source: str
    is_present: bool
    is_effective: bool
    mitigation: str | None = None


# =============================================================================
# AUDIT EVENT CATEGORIES
# =============================================================================


class AuditCategory:
    """Konstanten für Audit-Event-Kategorien"""

    CONCEPT = "explosionsschutz.concept"
    ZONE = "explosionsschutz.zone"
    MEASURE = "explosionsschutz.measure"
    EQUIPMENT = "explosionsschutz.equipment"
    INSPECTION = "explosionsschutz.inspection"
    DOCUMENT = "explosionsschutz.document"
    IGNITION = "explosionsschutz.ignition"


# =============================================================================
# CONTEXT HELPER
# =============================================================================


def get_request_context():
    """
    Holt den aktuellen Request-Kontext (tenant_id, user_id).
    """
    try:
        from common.request_context import get_context

        return get_context()
    except ImportError:
        return None


def emit_audit_event(
    tenant_id: UUID,
    category: str,
    action: str,
    entity_type: str,
    entity_id: UUID,
    payload: dict,
    user_id: UUID | None = None,
):
    """
    Emittiert ein Audit-Event via common.context.
    """
    from common.context import emit_audit_event as _emit

    _emit(
        tenant_id=tenant_id,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        user_id=user_id,
    )


def create_outbox_message(
    tenant_id: UUID,
    topic: str,
    payload: dict,
):
    """
    Erstellt eine Outbox-Nachricht für async Verarbeitung.
    """
    from common.context import emit_outbox_event as _emit_outbox

    _emit_outbox(
        topic=topic,
        payload=payload,
        tenant_id=tenant_id,
    )


# =============================================================================
# SERVICE FUNCTIONS
# =============================================================================


@transaction.atomic
def create_explosion_concept(
    cmd: CreateExplosionConceptCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ExplosionConcept:
    """
    Erstellt ein neues Explosionsschutzkonzept.

    Audit: explosionsschutz.concept.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.create")

    area = Area.objects.get(id=cmd.area_id)
    if area.tenant_id != tenant_id:
        raise PermissionDenied("Area gehört nicht zum Tenant")

    from substances.models import Substance

    substance = Substance.objects.get(id=cmd.substance_id)

    existing_versions = ExplosionConcept.objects.filter(
        tenant_id=tenant_id, area_id=cmd.area_id
    ).count()
    next_version = existing_versions + 1

    concept = ExplosionConcept.objects.create(
        tenant_id=tenant_id,
        area=area,
        substance_id=cmd.substance_id,
        substance_name=substance.name,
        title=cmd.title.strip(),
        version=next_version,
        status=ExplosionConcept.Status.DRAFT,
        assessment_id=cmd.assessment_id,
        created_by=user_id,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.CONCEPT,
        action="created",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "title": concept.title,
            "version": concept.version,
            "area_id": str(concept.area_id),
            "substance_id": str(concept.substance_id),
            "substance_name": substance.name,
        },
        user_id=user_id,
    )

    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.concept.created",
        payload={
            "concept_id": str(concept.id),
            "area_id": str(concept.area_id),
            "version": concept.version,
        },
    )

    return concept


@transaction.atomic
def update_explosion_concept(
    cmd: UpdateExplosionConceptCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ExplosionConcept:
    """
    Aktualisiert ein bestehendes Ex-Konzept.

    Audit: explosionsschutz.concept.updated
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.create")

    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id, tenant_id=tenant_id
    )

    if concept.status != ExplosionConcept.Status.DRAFT:
        raise ValidationError("Nur Entwürfe können bearbeitet werden")

    changes = {}

    if cmd.title is not None and cmd.title != concept.title:
        changes["title"] = {"old": concept.title, "new": cmd.title}
        concept.title = cmd.title.strip()

    if cmd.substance_id is not None and cmd.substance_id != concept.substance_id:
        from substances.models import Substance

        new_substance = Substance.objects.get(id=cmd.substance_id)
        changes["substance"] = {
            "old": str(concept.substance_id),
            "new": str(cmd.substance_id),
        }
        concept.substance_id = cmd.substance_id
        concept.substance_name = new_substance.name

    if changes:
        concept.save()
        emit_audit_event(
            tenant_id=tenant_id,
            category=AuditCategory.CONCEPT,
            action="updated",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            payload={"changes": changes},
            user_id=user_id,
        )

    return concept


@transaction.atomic
def validate_explosion_concept(
    cmd: ValidateExplosionConceptCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ExplosionConcept:
    """
    Validiert/gibt ein Ex-Konzept frei.

    Audit: explosionsschutz.concept.validated
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.approve")

    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id, tenant_id=tenant_id
    )

    if concept.status != ExplosionConcept.Status.IN_REVIEW:
        raise ValidationError("Nur Konzepte in Prüfung können freigegeben werden")

    if not concept.zones.exists():
        raise ValidationError("Mindestens eine Zone muss definiert sein")

    concept.is_validated = True
    concept.validated_by_id = user_id
    concept.validated_at = timezone.now()
    concept.status = ExplosionConcept.Status.APPROVED
    concept.save(
        update_fields=[
            "is_validated",
            "validated_by_id",
            "validated_at",
            "status",
            "updated_at",
        ]
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.CONCEPT,
        action="validated",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={"version": concept.version},
        user_id=user_id,
    )

    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.concept.validated",
        payload={"concept_id": str(concept.id)},
    )

    return concept


@transaction.atomic
def create_zone_definition(
    cmd: CreateZoneDefinitionCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ZoneDefinition:
    """
    Erstellt eine Zonendefinition für ein Ex-Konzept.

    Audit: explosionsschutz.zone.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    concept = ExplosionConcept.objects.get(id=cmd.concept_id, tenant_id=tenant_id)

    if concept.status not in [
        ExplosionConcept.Status.DRAFT,
        ExplosionConcept.Status.IN_REVIEW,
    ]:
        raise ValidationError(
            "Zonen können nur zu Entwürfen oder Konzepten in Prüfung hinzugefügt werden"
        )

    reference_standard = None
    if cmd.reference_standard_id:
        reference_standard = ReferenceStandard.objects.for_tenant(tenant_id).get(
            id=cmd.reference_standard_id
        )

    zone = ZoneDefinition.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        zone_type=cmd.zone_type,
        name=cmd.name.strip(),
        extent=cmd.extent,
        reference_standard=reference_standard,
        justification=cmd.justification or "",
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="created",
        entity_type="explosionsschutz.ZoneDefinition",
        entity_id=zone.id,
        payload={
            "concept_id": str(concept.id),
            "zone_type": zone.zone_type,
            "name": zone.name,
        },
        user_id=user_id,
    )

    return zone


@transaction.atomic
def create_protection_measure(
    cmd: CreateProtectionMeasureCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ProtectionMeasure:
    """
    Erstellt eine Schutzmaßnahme für ein Ex-Konzept.

    Audit: explosionsschutz.measure.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    concept = ExplosionConcept.objects.get(id=cmd.concept_id, tenant_id=tenant_id)

    catalog_reference = None
    if cmd.catalog_reference_id:
        catalog_reference = MeasureCatalog.objects.for_tenant(tenant_id).get(
            id=cmd.catalog_reference_id
        )

    safety_function = None
    if cmd.safety_function_id:
        safety_function = SafetyFunction.objects.for_tenant(tenant_id).get(
            id=cmd.safety_function_id
        )

    measure = ProtectionMeasure.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        category=cmd.category,
        title=cmd.title.strip(),
        description=cmd.description or "",
        catalog_reference=catalog_reference,
        safety_function=safety_function,
        status=ProtectionMeasure.Status.OPEN,
        due_date=cmd.due_date,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.MEASURE,
        action="created",
        entity_type="explosionsschutz.ProtectionMeasure",
        entity_id=measure.id,
        payload={
            "concept_id": str(concept.id),
            "category": measure.category,
            "title": measure.title,
            "has_safety_function": measure.safety_function_id is not None,
        },
        user_id=user_id,
    )

    return measure


@transaction.atomic
def create_equipment(
    cmd: CreateEquipmentCmd, tenant_id: UUID, user_id: UUID | None = None
) -> Equipment:
    """
    Registriert ein Betriebsmittel.

    Audit: explosionsschutz.equipment.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    area = Area.objects.get(id=cmd.area_id, tenant_id=tenant_id)
    equipment_type = EquipmentType.objects.for_tenant(tenant_id).get(id=cmd.equipment_type_id)

    zone = None
    if cmd.zone_id:
        zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
        if zone.zone_type not in equipment_type.allowed_zones:
            raise ValidationError(
                f"Equipment Kategorie {equipment_type.atex_category} "
                f"nicht zulässig in Zone {zone.zone_type}. "
                f"Erlaubte Zonen: {', '.join(equipment_type.allowed_zones)}"
            )

    equipment = Equipment.objects.create(
        tenant_id=tenant_id,
        area=area,
        equipment_type=equipment_type,
        zone=zone,
        serial_number=cmd.serial_number or "",
        asset_number=cmd.asset_number or "",
        location_detail=cmd.location_detail or "",
        installation_date=cmd.installation_date,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.EQUIPMENT,
        action="created",
        entity_type="explosionsschutz.Equipment",
        entity_id=equipment.id,
        payload={
            "area_id": str(area.id),
            "zone_id": str(zone.id) if zone else None,
            "atex_marking": equipment_type.full_atex_marking,
        },
        user_id=user_id,
    )

    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.equipment.created",
        payload={
            "equipment_id": str(equipment.id),
            "zone_type": zone.zone_type if zone else None,
        },
    )

    return equipment


@transaction.atomic
def create_inspection(
    cmd: CreateInspectionCmd, tenant_id: UUID, user_id: UUID | None = None
) -> Inspection:
    """
    Erfasst eine Prüfung nach BetrSichV.

    Audit: explosionsschutz.inspection.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    equipment = Equipment.objects.get(id=cmd.equipment_id, tenant_id=tenant_id)

    valid_types = {t[0] for t in Inspection.InspectionType.choices}
    if cmd.inspection_type not in valid_types:
        raise ValidationError(f"Ungültiger Prüfungstyp: {cmd.inspection_type}")

    valid_results = {r[0] for r in Inspection.Result.choices}
    if cmd.result not in valid_results:
        raise ValidationError(f"Ungültiges Prüfergebnis: {cmd.result}")

    require_permission("ex_inspection.create")

    inspection = Inspection.objects.create(
        tenant_id=tenant_id,
        equipment=equipment,
        inspection_type=cmd.inspection_type,
        inspection_date=cmd.inspection_date,
        inspector_name=cmd.inspector_name.strip(),
        result=cmd.result,
        findings=cmd.findings or "",
        recommendations=cmd.recommendations or "",
        certificate_number=cmd.certificate_number or "",
        created_by_id=user_id,
    )

    if inspection.result in (
        Inspection.Result.PASSED,
        Inspection.Result.PASSED_WITH_NOTES,
    ):
        from dateutil.relativedelta import relativedelta

        interval = (
            equipment.inspection_interval_months
            or equipment.equipment_type.default_inspection_interval_months
        )
        equipment.last_inspection_date = inspection.inspection_date
        equipment.next_inspection_date = inspection.inspection_date + relativedelta(months=interval)
        equipment.save(
            update_fields=[
                "last_inspection_date",
                "next_inspection_date",
                "updated_at",
            ]
        )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.INSPECTION,
        action="created",
        entity_type="explosionsschutz.Inspection",
        entity_id=inspection.id,
        payload={
            "equipment_id": str(equipment.id),
            "inspection_type": inspection.inspection_type,
            "result": inspection.result,
        },
        user_id=user_id,
    )

    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.inspection.created",
        payload={
            "inspection_id": str(inspection.id),
            "equipment_id": str(equipment.id),
            "result": inspection.result,
        },
    )

    return inspection


@transaction.atomic
def assess_ignition_source(
    cmd: AssessIgnitionSourceCmd, tenant_id: UUID, user_id: UUID | None = None
) -> ZoneIgnitionSourceAssessment:
    """
    Bewertet eine Zündquelle für eine Zone nach EN 1127-1.

    Audit: explosionsschutz.ignition.assessed
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)

    valid_sources = {s[0] for s in IgnitionSource.choices}
    if cmd.ignition_source not in valid_sources:
        raise ValidationError(f"Ungültige Zündquelle: {cmd.ignition_source}")

    assessment, created = ZoneIgnitionSourceAssessment.objects.update_or_create(
        tenant_id=tenant_id,
        zone=zone,
        ignition_source=cmd.ignition_source,
        defaults={
            "is_present": cmd.is_present,
            "is_effective": cmd.is_effective,
            "mitigation": cmd.mitigation or "",
            "assessed_by_id": user_id,
            "assessed_at": timezone.now(),
        },
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.IGNITION,
        action="assessed" if created else "updated",
        entity_type="explosionsschutz.ZoneIgnitionSourceAssessment",
        entity_id=assessment.id,
        payload={
            "zone_id": str(zone.id),
            "ignition_source": cmd.ignition_source,
            "is_present": cmd.is_present,
            "is_effective": cmd.is_effective,
            "has_mitigation": bool(cmd.mitigation),
        },
        user_id=user_id,
    )

    return assessment


@transaction.atomic
def archive_explosion_concept(
    concept_id: UUID, tenant_id: UUID, user_id: UUID | None = None
) -> ExplosionConcept:
    """
    Archiviert ein Ex-Konzept (Soft Delete).

    Audit: explosionsschutz.concept.archived
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    concept = ExplosionConcept.objects.select_for_update().get(id=concept_id, tenant_id=tenant_id)

    if concept.status not in [ExplosionConcept.Status.APPROVED, ExplosionConcept.Status.ARCHIVED]:
        raise ValidationError("Nur freigegebene Konzepte können archiviert werden")

    previous_status = concept.status
    concept.status = ExplosionConcept.Status.ARCHIVED
    concept.save(update_fields=["status", "updated_at"])

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.CONCEPT,
        action="archived",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "version": concept.version,
            "previous_status": previous_status,
        },
        user_id=user_id,
    )

    return concept


# =============================================================================
# RISKFW-INTEGRATION: Zonenberechnung, DXF-Import, ATEX-Check
# =============================================================================

DXF_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

_ZONE_VALUE_MAP: dict[str, str] = {
    "Zone 0": "0",
    "Zone 1": "1",
    "Zone 2": "2",
    "EX_ZONE_0": "0",
    "EX_ZONE_1": "1",
    "EX_ZONE_2": "2",
}


def _parse_ex_zone_type(raw_value: str) -> str:
    result = _ZONE_VALUE_MAP.get(raw_value)
    if result is None:
        raise ValueError(
            f"Unbekannter Ex-Zonen-Wert: {raw_value!r}. Erlaubt: {list(_ZONE_VALUE_MAP)}"
        )
    return result


@dataclass(frozen=True)
class CalculateZoneCmd:
    zone_id: UUID
    release_rate_kg_s: float
    ventilation_rate_m3_s: float
    release_type: str
    notes: str = ""


@transaction.atomic
def calculate_and_store_zone(
    cmd: CalculateZoneCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> "ZoneCalculationResult":
    """
    Delegiert TRGS 721 Berechnung an riskfw, archiviert Ergebnis.
    Audit: explosionsschutz.zone.calculated
    """
    import dataclasses as _dc

    import riskfw
    from riskfw.exceptions import SubstanceNotFoundError
    from riskfw.zones import calculate_zone_extent

    try:
        zone = ZoneDefinition.objects.select_related("concept").get(
            id=cmd.zone_id, tenant_id=tenant_id
        )
    except ZoneDefinition.DoesNotExist:
        raise ValidationError(f"ZoneDefinition {cmd.zone_id} nicht gefunden")

    if zone.concept is None:
        raise ValidationError(f"ZoneDefinition {cmd.zone_id} hat kein ExplosionConcept")

    substance_name = zone.concept.substance_name
    if not substance_name:
        raise ValidationError(f"Concept {zone.concept_id} hat keinen Stoff zugewiesen")

    try:
        result = calculate_zone_extent(
            release_rate_kg_s=cmd.release_rate_kg_s,
            ventilation_rate_m3_s=cmd.ventilation_rate_m3_s,
            substance_name=substance_name,
            release_type=cmd.release_type,
        )
    except SubstanceNotFoundError as exc:
        raise ValidationError(f"Stoff '{substance_name}' nicht in riskfw-DB: {exc}") from exc

    calc = ZoneCalculationResult.objects.create(
        tenant_id=tenant_id,
        zone=zone,
        substance_name=substance_name,
        release_rate_kg_s=cmd.release_rate_kg_s,
        ventilation_rate_m3_s=cmd.ventilation_rate_m3_s,
        release_type=cmd.release_type,
        calculated_zone_type=str(result.zone_type),
        calculated_radius_m=result.radius_m,
        calculated_volume_m3=result.volume_m3,
        basis_norm=result.basis_norm,
        riskfw_version=riskfw.__version__,
        raw_result=_dc.asdict(result),
        calculated_by_id=user_id,
        notes=cmd.notes,
    )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="calculated",
        entity_type="explosionsschutz.ZoneCalculationResult",
        entity_id=calc.id,
        payload={
            "zone_type": str(result.zone_type),
            "radius_m": result.radius_m,
            "substance": substance_name,
        },
        user_id=user_id,
    )
    return calc


@transaction.atomic
def import_zones_from_dxf(
    concept_id: UUID,
    dxf_bytes: bytes,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> int:
    """
    DXF -> nl2cad-brandschutz -> ExBereich-Liste -> ZoneDefinition-Records.
    Audit: explosionsschutz.zone.imported
    """
    import io

    import ezdxf
    from ezdxf.lldxf.const import DXFError

    from brandschutz.analyzer import BrandschutzAnalyzer

    if len(dxf_bytes) > DXF_MAX_BYTES:
        raise ValidationError(f"DXF zu gross: {len(dxf_bytes):,} Bytes (max {DXF_MAX_BYTES:,})")

    try:
        doc = ezdxf.read(io.BytesIO(dxf_bytes))
    except DXFError as exc:
        raise ValidationError(f"Ungueltige DXF-Datei: {exc}") from exc

    concept = ExplosionConcept.objects.get(id=concept_id, tenant_id=tenant_id)
    analyse = BrandschutzAnalyzer().analyze_dxf(doc)

    created_ids: list[UUID] = []
    for ex_bereich in analyse.ex_bereiche:
        zone = ZoneDefinition.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            zone_type=_parse_ex_zone_type(ex_bereich.zone.value),
            name=(ex_bereich.name or f"Import: {ex_bereich.zone.value}"),
            justification=(f"DXF-Import via nl2cad-brandschutz, Layer: {ex_bereich.layer}"),
        )
        created_ids.append(zone.id)

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.ZONE,
        action="imported",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept_id,
        payload={
            "count": len(created_ids),
            "zone_ids": [str(i) for i in created_ids],
            "source": "dxf",
        },
        user_id=user_id,
    )
    return len(created_ids)


@dataclass(frozen=True)
class CreateEquipmentWithATEXCmd:
    area_id: UUID
    equipment_type_id: UUID
    zone_id: UUID | None = None
    serial_number: str | None = None
    asset_number: str | None = None
    location_detail: str | None = None
    installation_date: str | None = None


@transaction.atomic
def create_equipment_with_atex_check(
    cmd: CreateEquipmentWithATEXCmd,
    tenant_id: UUID,
    user_id: UUID | None = None,
) -> Equipment:
    """
    Erstellt Betriebsmittel + ATEX-Check explizit im Service.
    Kein post_save-Signal: deterministisch, kein Seiteneffekt bei loaddata.
    Audit: explosionsschutz.equipment.created
    """
    import dataclasses as _dc

    import riskfw
    from riskfw.equipment import check_equipment_suitability
    from riskfw.exceptions import ATEXCheckError

    equipment_type = EquipmentType.objects.get(id=cmd.equipment_type_id)
    equipment = Equipment.objects.create(
        tenant_id=tenant_id,
        area_id=cmd.area_id,
        equipment_type=equipment_type,
        zone_id=cmd.zone_id,
        serial_number=cmd.serial_number or "",
        asset_number=cmd.asset_number or "",
        location_detail=cmd.location_detail or "",
    )

    atex_marking = equipment_type.full_atex_marking
    zone_str = "2"
    if cmd.zone_id:
        try:
            zone_obj = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
            zone_str = zone_obj.zone_type
        except ZoneDefinition.DoesNotExist:
            pass

    atex_result = None
    try:
        atex_result = check_equipment_suitability(
            ex_marking=atex_marking,
            zone=zone_str,
        )
    except ATEXCheckError:
        pass

    if atex_result is not None:
        EquipmentATEXCheck.objects.create(
            tenant_id=tenant_id,
            equipment=equipment,
            is_suitable=atex_result.is_suitable,
            result=_dc.asdict(atex_result),
            riskfw_version=riskfw.__version__,
        )

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.EQUIPMENT,
        action="created",
        entity_type="explosionsschutz.Equipment",
        entity_id=equipment.id,
        payload={
            "atex_suitable": (atex_result.is_suitable if atex_result else None),
            "marking": atex_marking,
        },
        user_id=user_id,
    )
    return equipment
