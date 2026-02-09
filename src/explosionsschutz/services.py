# src/explosionsschutz/services.py
"""
Explosionsschutz Service Layer (v5)

Alle Mutationen laufen über diesen Service Layer:
- Command DTOs für typsichere Eingaben
- @transaction.atomic für Konsistenz
- emit_audit_event() für Compliance
- OutboxMessage für async Verarbeitung
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

from permissions.authz import require_permission

from .models import (
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    EquipmentType,
    Inspection,
    VerificationDocument,
    MeasureCatalog,
    SafetyFunction,
    ReferenceStandard,
    ZoneIgnitionSourceAssessment,
    IgnitionSource,
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
    assessment_id: Optional[UUID] = None


@dataclass(frozen=True)
class UpdateExplosionConceptCmd:
    """Command für Aktualisierung eines Ex-Konzepts"""
    concept_id: UUID
    title: Optional[str] = None
    substance_id: Optional[UUID] = None


@dataclass(frozen=True)
class ValidateExplosionConceptCmd:
    """Command für Validierung/Freigabe eines Ex-Konzepts"""
    concept_id: UUID
    notes: Optional[str] = None


@dataclass(frozen=True)
class CreateZoneDefinitionCmd:
    """Command für Erstellung einer Zonendefinition"""
    concept_id: UUID
    zone_type: str
    name: str
    extent: Optional[dict] = None
    reference_standard_id: Optional[UUID] = None
    justification: Optional[str] = None


@dataclass(frozen=True)
class CreateProtectionMeasureCmd:
    """Command für Erstellung einer Schutzmaßnahme"""
    concept_id: UUID
    category: str
    title: str
    description: Optional[str] = None
    catalog_reference_id: Optional[UUID] = None
    safety_function_id: Optional[UUID] = None
    due_date: Optional[str] = None


@dataclass(frozen=True)
class CreateEquipmentCmd:
    """Command für Registrierung eines Betriebsmittels"""
    area_id: UUID
    equipment_type_id: UUID
    zone_id: Optional[UUID] = None
    serial_number: Optional[str] = None
    asset_number: Optional[str] = None
    location_detail: Optional[str] = None
    installation_date: Optional[str] = None


@dataclass(frozen=True)
class CreateInspectionCmd:
    """Command für Erfassung einer Prüfung"""
    equipment_id: UUID
    inspection_type: str
    inspection_date: str
    inspector_name: str
    result: str
    findings: Optional[str] = None
    recommendations: Optional[str] = None
    certificate_number: Optional[str] = None


@dataclass(frozen=True)
class AssessIgnitionSourceCmd:
    """Command für Zündquellenbewertung"""
    zone_id: UUID
    ignition_source: str
    is_present: bool
    is_effective: bool
    mitigation: Optional[str] = None


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
    
    Falls kein Kontext verfügbar, gibt None zurück.
    In Produktion würde dies über Thread-Local oder Middleware gesetzt.
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
    user_id: Optional[UUID] = None,
):
    """
    Emittiert ein Audit-Event via common.context.

    Raises ImportError if audit module is missing — this is
    intentional to catch misconfiguration early.
    """
    from common.context import (
        emit_audit_event as _emit,
    )
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
    tenant_id: UUID, topic: str, payload: dict,
):
    """
    Erstellt eine Outbox-Nachricht für async Verarbeitung.

    Raises ImportError if outbox module is missing.
    """
    from common.context import (
        emit_outbox_event as _emit_outbox,
    )
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
    cmd: CreateExplosionConceptCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ExplosionConcept:
    """
    Erstellt ein neues Explosionsschutzkonzept.
    
    Audit: explosionsschutz.concept.created
    Outbox: explosionsschutz.concept.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.create")

    # Validierung: Area muss zum Tenant gehören
    area = Area.objects.get(id=cmd.area_id)
    if area.tenant_id != tenant_id:
        raise PermissionDenied("Area gehört nicht zum Tenant")
    
    # Validierung: Substance muss existieren
    from substances.models import Substance
    substance = Substance.objects.get(id=cmd.substance_id)
    
    # Ermittle nächste Version für diesen Bereich
    existing_versions = ExplosionConcept.objects.filter(
        tenant_id=tenant_id,
        area_id=cmd.area_id
    ).count()
    next_version = existing_versions + 1
    
    # Erstelle Konzept
    concept = ExplosionConcept.objects.create(
        tenant_id=tenant_id,
        area=area,
        substance=substance,
        title=cmd.title.strip(),
        version=next_version,
        status=ExplosionConcept.Status.DRAFT,
        assessment_id=cmd.assessment_id,
        created_by_id=user_id,
    )
    
    # Audit Event
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
            "assessment_id": str(cmd.assessment_id) if cmd.assessment_id else None,
        },
        user_id=user_id,
    )
    
    # Outbox Message für async Verarbeitung
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
    cmd: UpdateExplosionConceptCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ExplosionConcept:
    """
    Aktualisiert ein bestehendes Ex-Konzept.
    
    Audit: explosionsschutz.concept.updated
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.create")

    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id,
        tenant_id=tenant_id
    )
    
    if concept.status != ExplosionConcept.Status.DRAFT:
        raise ValidationError("Nur Entwürfe können bearbeitet werden")
    
    # Sammle Änderungen für Audit
    changes = {}
    
    if cmd.title is not None and cmd.title != concept.title:
        changes["title"] = {"old": concept.title, "new": cmd.title}
        concept.title = cmd.title.strip()
    
    if cmd.substance_id is not None and cmd.substance_id != concept.substance_id:
        from substances.models import Substance
        new_substance = Substance.objects.get(id=cmd.substance_id)
        old_substance_name = concept.substance.name
        changes["substance"] = {
            "old": {"id": str(concept.substance_id), "name": old_substance_name},
            "new": {"id": str(cmd.substance_id), "name": new_substance.name},
        }
        concept.substance = new_substance
    
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
    cmd: ValidateExplosionConceptCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ExplosionConcept:
    """
    Validiert/gibt ein Ex-Konzept frei.
    
    Prüft:
    - Mindestens eine Zone definiert
    - Alle Zonen haben Maßnahmen
    - Equipment in Zonen hat gültige ATEX-Kategorie
    
    Audit: explosionsschutz.concept.validated
    Outbox: explosionsschutz.concept.validated
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")

    require_permission("ex_concept.approve")

    concept = ExplosionConcept.objects.select_for_update().get(
        id=cmd.concept_id,
        tenant_id=tenant_id
    )

    if concept.status != ExplosionConcept.Status.DRAFT:
        raise ValidationError("Nur Entwürfe können validiert werden")
    
    # Validierung: Mindestens eine Zone
    zones = concept.zones.all()
    if not zones.exists():
        raise ValidationError("Mindestens eine Zone muss definiert sein")
    
    # Validierung: Equipment-Zonenzuordnung
    validation_errors = []
    for zone in zones:
        for equipment in zone.equipment.all():
            allowed = equipment.equipment_type.allowed_zones
            if zone.zone_type not in allowed:
                validation_errors.append(
                    f"Equipment '{equipment.serial_number or equipment.asset_number}' "
                    f"(Kategorie {equipment.equipment_type.atex_category}) "
                    f"nicht zulässig in Zone {zone.zone_type}"
                )
    
    if validation_errors:
        raise ValidationError(validation_errors)
    
    # Status ändern
    concept.status = ExplosionConcept.Status.APPROVED
    concept.is_validated = True
    concept.validated_by_id = user_id
    concept.validated_at = timezone.now()
    concept.save()
    
    # Audit Event
    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.CONCEPT,
        action="validated",
        entity_type="explosionsschutz.ExplosionConcept",
        entity_id=concept.id,
        payload={
            "version": concept.version,
            "validated_by": str(user_id) if user_id else None,
            "notes": cmd.notes,
            "zone_count": zones.count(),
        },
        user_id=user_id,
    )
    
    # Outbox für Benachrichtigungen
    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.concept.validated",
        payload={
            "concept_id": str(concept.id),
            "validated_by": str(user_id) if user_id else None,
        },
    )
    
    return concept


@transaction.atomic
def create_zone_definition(
    cmd: CreateZoneDefinitionCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ZoneDefinition:
    """
    Erstellt eine Zonendefinition für ein Ex-Konzept.
    
    Audit: explosionsschutz.zone.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.get(
        id=cmd.concept_id,
        tenant_id=tenant_id
    )
    
    if concept.status != ExplosionConcept.Status.DRAFT:
        raise ValidationError("Zonen können nur in Entwürfen hinzugefügt werden")
    
    # Validierung: Zonentyp
    valid_zones = {"0", "1", "2", "20", "21", "22", "non_ex"}
    if cmd.zone_type not in valid_zones:
        raise ValidationError(f"Ungültiger Zonentyp: {cmd.zone_type}")
    
    zone = ZoneDefinition.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        zone_type=cmd.zone_type,
        name=cmd.name.strip(),
        extent=cmd.extent,
        reference_standard_id=cmd.reference_standard_id,
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
            "extent": zone.extent,
        },
        user_id=user_id,
    )
    
    return zone


@transaction.atomic
def create_protection_measure(
    cmd: CreateProtectionMeasureCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ProtectionMeasure:
    """
    Erstellt eine Schutzmaßnahme für ein Ex-Konzept.
    
    Audit: explosionsschutz.measure.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.get(
        id=cmd.concept_id,
        tenant_id=tenant_id
    )
    
    if concept.status != ExplosionConcept.Status.DRAFT:
        raise ValidationError("Maßnahmen können nur in Entwürfen hinzugefügt werden")
    
    # Validierung: Kategorie
    valid_categories = {c[0] for c in ProtectionMeasure.Category.choices}
    if cmd.category not in valid_categories:
        raise ValidationError(f"Ungültige Kategorie: {cmd.category}")
    
    measure = ProtectionMeasure.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        category=cmd.category,
        title=cmd.title.strip(),
        description=cmd.description or "",
        catalog_reference_id=cmd.catalog_reference_id,
        safety_function_id=cmd.safety_function_id,
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
    cmd: CreateEquipmentCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> Equipment:
    """
    Registriert ein Betriebsmittel in einem Bereich.
    
    Validiert automatisch die ATEX-Kategorie gegen den Zonentyp.
    
    Audit: explosionsschutz.equipment.created
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    area = Area.objects.get(id=cmd.area_id, tenant_id=tenant_id)
    
    equipment_type = EquipmentType.objects.for_tenant(tenant_id).get(
        id=cmd.equipment_type_id
    )
    
    # Validierung: ATEX-Kategorie passend zur Zone (falls Zone angegeben)
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
            "zone_type": zone.zone_type if zone else None,
            "equipment_type_id": str(equipment_type.id),
            "atex_marking": equipment_type.full_atex_marking,
            "serial_number": equipment.serial_number,
            "asset_number": equipment.asset_number,
        },
        user_id=user_id,
    )
    
    # Outbox für Prüffristen-Setup
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
    cmd: CreateInspectionCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> Inspection:
    """
    Erfasst eine Prüfung nach BetrSichV.
    
    Audit: explosionsschutz.inspection.created
    Outbox: explosionsschutz.inspection.created (für Fristenverwaltung)
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    equipment = Equipment.objects.get(
        id=cmd.equipment_id,
        tenant_id=tenant_id
    )
    
    # Validierung: Inspection Type
    valid_types = {t[0] for t in Inspection.InspectionType.choices}
    if cmd.inspection_type not in valid_types:
        raise ValidationError(f"Ungültiger Prüfungstyp: {cmd.inspection_type}")
    
    # Validierung: Result
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

    # Update equipment inspection schedule (moved from
    # Inspection.save() to keep model side-effect-free)
    if inspection.result in (
        Inspection.Result.PASSED,
        Inspection.Result.PASSED_WITH_NOTES,
    ):
        from dateutil.relativedelta import relativedelta

        interval = (
            equipment.inspection_interval_months
            or equipment.equipment_type
            .default_inspection_interval_months
        )
        equipment.last_inspection_date = (
            inspection.inspection_date
        )
        equipment.next_inspection_date = (
            inspection.inspection_date
            + relativedelta(months=interval)
        )
        equipment.save(update_fields=[
            "last_inspection_date",
            "next_inspection_date",
            "updated_at",
        ])

    emit_audit_event(
        tenant_id=tenant_id,
        category=AuditCategory.INSPECTION,
        action="created",
        entity_type="explosionsschutz.Inspection",
        entity_id=inspection.id,
        payload={
            "equipment_id": str(equipment.id),
            "equipment_serial": equipment.serial_number,
            "inspection_type": inspection.inspection_type,
            "result": inspection.result,
            "inspector": inspection.inspector_name,
        },
        user_id=user_id,
    )
    
    # Outbox für Fristenverwaltung
    create_outbox_message(
        tenant_id=tenant_id,
        topic="explosionsschutz.inspection.created",
        payload={
            "inspection_id": str(inspection.id),
            "equipment_id": str(equipment.id),
            "result": inspection.result,
            "next_inspection_date": str(equipment.next_inspection_date)
            if equipment.next_inspection_date else None,
        },
    )
    
    return inspection


@transaction.atomic
def assess_ignition_source(
    cmd: AssessIgnitionSourceCmd,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ZoneIgnitionSourceAssessment:
    """
    Bewertet eine Zündquelle für eine Zone nach EN 1127-1.
    
    Audit: explosionsschutz.ignition.assessed
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    zone = ZoneDefinition.objects.get(id=cmd.zone_id, tenant_id=tenant_id)
    
    # Validierung: Ignition Source
    valid_sources = {s[0] for s in IgnitionSource.choices}
    if cmd.ignition_source not in valid_sources:
        raise ValidationError(f"Ungültige Zündquelle: {cmd.ignition_source}")
    
    # Update or Create
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
        }
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
    concept_id: UUID,
    tenant_id: UUID,
    user_id: Optional[UUID] = None
) -> ExplosionConcept:
    """
    Archiviert ein Ex-Konzept (Soft Delete).
    
    Nur validierte Konzepte können archiviert werden.
    Archivierte Konzepte bleiben für Compliance-Zwecke erhalten.
    
    Audit: explosionsschutz.concept.archived
    """
    if tenant_id is None:
        raise PermissionDenied("Tenant erforderlich")
    
    concept = ExplosionConcept.objects.select_for_update().get(
        id=concept_id,
        tenant_id=tenant_id
    )
    
    if concept.status not in [
        ExplosionConcept.Status.APPROVED,
        ExplosionConcept.Status.ARCHIVED
    ]:
        raise ValidationError(
            "Nur freigegebene Konzepte können archiviert werden"
        )
    
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
