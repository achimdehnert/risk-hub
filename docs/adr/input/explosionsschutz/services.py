"""
Service Layer für das Explosionsschutz-Modul.

Alle Mutations laufen über diese Services:
- Command DTOs (frozen dataclasses) für typsichere Eingaben
- @transaction.atomic für Datenkonsistenz
- emit_audit_event() für den Audit-Trail
- OutboxMessage für async Aktionen (Fristen-Benachrichtigungen)
- Keine business logic in Views oder Signals
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import emit_audit_event
from apps.outbox.models import OutboxMessage

from .models import (
    Area,
    Equipment,
    ExplosionConcept,
    IgnitionSource,
    Inspection,
    MeasureCategory,
    ProtectionMeasure,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)

# ============================================================================
# Command DTOs
# ============================================================================


@dataclass(frozen=True)
class CreateAreaCmd:
    site_id: UUID
    code: str
    name: str
    description: str = ""
    location_description: str = ""


@dataclass(frozen=True)
class CreateConceptCmd:
    area_id: UUID
    title: str
    substance_id: UUID | None = None
    atmosphere_type: str = "gas"
    process_description: str = ""
    document_number: str = ""


@dataclass(frozen=True)
class UpdateConceptCmd:
    concept_id: UUID
    title: str | None = None
    substance_id: UUID | None = None
    process_description: str | None = None
    substitute_check_status: str | None = None
    substitute_check_notes: str | None = None
    release_source_type: str | None = None
    release_grade: str | None = None
    release_description: str | None = None
    explosion_impact_mitigation: str | None = None
    responsible_id: UUID | None = None
    responsible_name: str | None = None
    next_review_date: date | None = None


@dataclass(frozen=True)
class SubmitForReviewCmd:
    concept_id: UUID
    notes: str = ""


@dataclass(frozen=True)
class ApproveConceptCmd:
    concept_id: UUID
    approver_id: UUID
    approver_name: str
    notes: str = ""


@dataclass(frozen=True)
class ArchiveConceptCmd:
    concept_id: UUID
    reason: str = ""


@dataclass(frozen=True)
class CreateZoneCmd:
    concept_id: UUID
    zone_type: str
    name: str
    justification: str
    location_in_area: str = ""
    extent_shape: str = "custom"
    extent_radius_m: float | None = None
    extent_height_m: float | None = None
    extent_description: str = ""
    ventilation_type: str = "natural"
    ventilation_notes: str = ""
    trgs_reference_id: UUID | None = None


@dataclass(frozen=True)
class AssessIgnitionSourceCmd:
    zone_id: UUID
    ignition_source: str
    is_present: bool
    is_effective: bool
    mitigation: str = ""
    residual_risk_acceptable: bool = True


@dataclass(frozen=True)
class CreateMeasureCmd:
    concept_id: UUID
    category: str
    title: str
    description: str
    justification: str = ""
    catalog_reference_id: UUID | None = None
    safety_function_id: UUID | None = None
    responsible_id: UUID | None = None
    responsible_name: str = ""
    due_date: date | None = None
    status: str = "done"
    standard_reference_id: UUID | None = None


@dataclass(frozen=True)
class AddEquipmentCmd:
    area_id: UUID
    name: str
    equipment_type_id: UUID | None = None
    inventory_number: str = ""
    serial_number: str = ""
    atex_marking_override: str = ""
    manufacturer: str = ""
    inspection_interval_months: int | None = None
    first_inspection_date: date | None = None


@dataclass(frozen=True)
class RecordInspectionCmd:
    equipment_id: UUID
    inspection_type: str
    scheduled_date: date
    performed_date: date | None = None
    performed_by_id: UUID | None = None
    performed_by_name: str = ""
    external_inspector: str = ""
    result: str | None = None
    findings: str = ""
    corrective_actions: str = ""
    next_inspection_date: date | None = None


# ============================================================================
# Area Service
# ============================================================================


class AreaService:

    @staticmethod
    @transaction.atomic
    def create_area(
        cmd: CreateAreaCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Area:
        area = Area.objects.create(
            tenant_id=tenant_id,
            site_id=cmd.site_id,
            code=cmd.code,
            name=cmd.name,
            description=cmd.description,
            location_description=cmd.location_description,
        )
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="area.created",
            entity_type="explosionsschutz.Area",
            entity_id=area.id,
            user_id=user_id,
            payload={"code": cmd.code, "name": cmd.name},
        )
        return area


# ============================================================================
# Concept Service
# ============================================================================


class ConceptService:

    @staticmethod
    @transaction.atomic
    def create_concept(
        cmd: CreateConceptCmd,
        tenant_id: UUID,
        user_id: UUID,
        author_name: str = "",
    ) -> ExplosionConcept:
        area = Area.objects.get(pk=cmd.area_id, tenant_id=tenant_id)

        # Vorherige Konzepte als "nicht aktuell" markieren
        area.concepts.filter(is_current=True).update(is_current=False)

        concept = ExplosionConcept.objects.create(
            tenant_id=tenant_id,
            area=area,
            title=cmd.title,
            substance_id=cmd.substance_id,
            atmosphere_type=cmd.atmosphere_type,
            process_description=cmd.process_description,
            document_number=cmd.document_number,
            author_id=user_id,
            author_name=author_name,
            status=ExplosionConcept.Status.DRAFT,
            is_current=True,
        )
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="concept.created",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            user_id=user_id,
            payload={"title": cmd.title, "area_id": str(cmd.area_id)},
        )
        return concept

    @staticmethod
    @transaction.atomic
    def update_concept(
        cmd: UpdateConceptCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ExplosionConcept:
        concept = ExplosionConcept.objects.select_for_update().get(
            pk=cmd.concept_id, tenant_id=tenant_id
        )
        if concept.status not in (
            ExplosionConcept.Status.DRAFT, ExplosionConcept.Status.REVIEW
        ):
            raise PermissionDenied(
                f"Konzept im Status '{concept.status}' kann nicht bearbeitet werden."
            )

        changed: dict = {}
        for field in (
            "title", "substance_id", "process_description",
            "substitute_check_status", "substitute_check_notes",
            "release_source_type", "release_grade", "release_description",
            "explosion_impact_mitigation", "responsible_id", "responsible_name",
            "next_review_date",
        ):
            val = getattr(cmd, field, None)
            if val is not None:
                setattr(concept, field, val)
                changed[field] = str(val)

        concept.save()
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="concept.updated",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            user_id=user_id,
            payload={"changed_fields": list(changed.keys())},
        )
        return concept

    @staticmethod
    @transaction.atomic
    def submit_for_review(
        cmd: SubmitForReviewCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ExplosionConcept:
        concept = ExplosionConcept.objects.select_for_update().get(
            pk=cmd.concept_id, tenant_id=tenant_id
        )
        if concept.status != ExplosionConcept.Status.DRAFT:
            raise ValidationError("Nur Entwürfe können zur Prüfung eingereicht werden.")
        if not concept.zones.exists():
            raise ValidationError("Mindestens eine Zone muss definiert sein.")
        if not concept.measures.filter(category=MeasureCategory.PRIMARY).exists():
            raise ValidationError(
                "Mindestens eine primäre Schutzmaßnahme muss dokumentiert sein."
            )

        concept.status = ExplosionConcept.Status.REVIEW
        concept.save(update_fields=["status", "updated_at"])
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="concept.submitted_for_review",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            user_id=user_id,
            payload={"notes": cmd.notes},
        )
        return concept

    @staticmethod
    @transaction.atomic
    def approve_concept(
        cmd: ApproveConceptCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ExplosionConcept:
        concept = ExplosionConcept.objects.select_for_update().get(
            pk=cmd.concept_id, tenant_id=tenant_id
        )
        if concept.status != ExplosionConcept.Status.REVIEW:
            raise ValidationError("Nur Konzepte in Prüfung können freigegeben werden.")

        now = timezone.now()
        concept.status = ExplosionConcept.Status.APPROVED
        # Immutable Snapshot nach ADR-008 Empfehlung H4
        concept.approved_by_id = cmd.approver_id
        concept.approved_by_name = cmd.approver_name
        concept.approved_at = now
        concept.approval_notes = cmd.notes
        # Nächste Überprüfung in 3 Jahren (§6(9) GefStoffV)
        if not concept.next_review_date:
            concept.next_review_date = (now + timedelta(days=3 * 365)).date()
        concept.save()

        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="concept.approved",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            user_id=user_id,
            payload={
                "approved_by": cmd.approver_name,
                "approved_at": now.isoformat(),
                "next_review_date": concept.next_review_date.isoformat(),
            },
        )
        # Outbox: Erinnerung für nächste Überprüfung planen
        OutboxMessage.objects.create(
            tenant_id=tenant_id,
            event_type="explosionsschutz.review_due",
            payload={
                "concept_id": str(concept.id),
                "concept_title": concept.title,
                "review_due": concept.next_review_date.isoformat(),
                "area_id": str(concept.area_id),
            },
            scheduled_at=timezone.make_aware(
                datetime.combine(concept.next_review_date - timedelta(days=60), datetime.min.time())
            ),
        )
        return concept

    @staticmethod
    @transaction.atomic
    def archive_concept(
        cmd: ArchiveConceptCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ExplosionConcept:
        concept = ExplosionConcept.objects.select_for_update().get(
            pk=cmd.concept_id, tenant_id=tenant_id
        )
        if concept.status not in (
            ExplosionConcept.Status.APPROVED, ExplosionConcept.Status.REVIEW
        ):
            raise ValidationError("Nur freigegebene Konzepte können archiviert werden.")

        concept.status = ExplosionConcept.Status.ARCHIVED
        concept.is_current = False
        concept.save(update_fields=["status", "is_current", "updated_at"])
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="concept.archived",
            entity_type="explosionsschutz.ExplosionConcept",
            entity_id=concept.id,
            user_id=user_id,
            payload={"reason": cmd.reason},
        )
        return concept


# ============================================================================
# Zone Service
# ============================================================================


class ZoneService:

    @staticmethod
    @transaction.atomic
    def create_zone(
        cmd: CreateZoneCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ZoneDefinition:
        concept = ExplosionConcept.objects.get(pk=cmd.concept_id, tenant_id=tenant_id)
        if concept.status == ExplosionConcept.Status.APPROVED:
            raise PermissionDenied("Freigegebene Konzepte können nicht geändert werden.")

        zone = ZoneDefinition.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            zone_type=cmd.zone_type,
            name=cmd.name,
            justification=cmd.justification,
            location_in_area=cmd.location_in_area,
            extent_shape=cmd.extent_shape,
            extent_radius_m=cmd.extent_radius_m,
            extent_height_m=cmd.extent_height_m,
            extent_description=cmd.extent_description,
            ventilation_type=cmd.ventilation_type,
            ventilation_notes=cmd.ventilation_notes,
            trgs_reference_id=cmd.trgs_reference_id,
        )
        # Automatisch alle 13 Zündquellen als "nicht bewertet" anlegen
        ZoneService._init_ignition_assessments(zone, tenant_id)

        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="zone.created",
            entity_type="explosionsschutz.ZoneDefinition",
            entity_id=zone.id,
            user_id=user_id,
            payload={"zone_type": cmd.zone_type, "name": cmd.name},
        )
        return zone

    @staticmethod
    def _init_ignition_assessments(
        zone: ZoneDefinition, tenant_id: UUID
    ) -> None:
        """Legt alle 13 Zündquellen-Bewertungen als Platzhalter an."""
        assessments = [
            ZoneIgnitionSourceAssessment(
                tenant_id=tenant_id,
                zone=zone,
                ignition_source=source.value,
                is_present=False,
                is_effective=False,
            )
            for source in IgnitionSource
        ]
        ZoneIgnitionSourceAssessment.objects.bulk_create(
            assessments, ignore_conflicts=True
        )

    @staticmethod
    @transaction.atomic
    def assess_ignition_source(
        cmd: AssessIgnitionSourceCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ZoneIgnitionSourceAssessment:
        assessment, _ = ZoneIgnitionSourceAssessment.objects.update_or_create(
            zone_id=cmd.zone_id,
            ignition_source=cmd.ignition_source,
            defaults={
                "tenant_id": tenant_id,
                "is_present": cmd.is_present,
                "is_effective": cmd.is_effective,
                "mitigation": cmd.mitigation,
                "residual_risk_acceptable": cmd.residual_risk_acceptable,
                "assessed_by_id": user_id,
                "assessed_at": timezone.now(),
            },
        )
        return assessment


# ============================================================================
# Measure Service
# ============================================================================


class MeasureService:

    @staticmethod
    @transaction.atomic
    def create_measure(
        cmd: CreateMeasureCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> ProtectionMeasure:
        concept = ExplosionConcept.objects.get(pk=cmd.concept_id, tenant_id=tenant_id)
        if concept.status == ExplosionConcept.Status.APPROVED:
            raise PermissionDenied("Freigegebene Konzepte können nicht geändert werden.")

        measure = ProtectionMeasure.objects.create(
            tenant_id=tenant_id,
            concept=concept,
            category=cmd.category,
            title=cmd.title,
            description=cmd.description,
            justification=cmd.justification,
            catalog_reference_id=cmd.catalog_reference_id,
            safety_function_id=cmd.safety_function_id,
            responsible_id=cmd.responsible_id,
            responsible_name=cmd.responsible_name,
            due_date=cmd.due_date,
            status=cmd.status,
            standard_reference_id=cmd.standard_reference_id,
        )
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="measure.created",
            entity_type="explosionsschutz.ProtectionMeasure",
            entity_id=measure.id,
            user_id=user_id,
            payload={"category": cmd.category, "title": cmd.title},
        )
        return measure


# ============================================================================
# Equipment Service
# ============================================================================


class EquipmentService:

    @staticmethod
    @transaction.atomic
    def add_equipment(
        cmd: AddEquipmentCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Equipment:
        area = Area.objects.get(pk=cmd.area_id, tenant_id=tenant_id)

        # Prüfintervall bestimmen
        interval = cmd.inspection_interval_months
        if not interval and cmd.equipment_type_id:
            from .models.master_data import EquipmentType
            try:
                et = EquipmentType.objects.get(pk=cmd.equipment_type_id)
                interval = et.default_inspection_interval_months
            except EquipmentType.DoesNotExist:
                pass

        next_inspection = None
        if cmd.first_inspection_date and interval:
            from dateutil.relativedelta import relativedelta
            next_inspection = cmd.first_inspection_date + relativedelta(months=interval)

        equipment = Equipment.objects.create(
            tenant_id=tenant_id,
            area=area,
            name=cmd.name,
            equipment_type_id=cmd.equipment_type_id,
            inventory_number=cmd.inventory_number,
            serial_number=cmd.serial_number,
            atex_marking_override=cmd.atex_marking_override,
            manufacturer=cmd.manufacturer,
            inspection_interval_months=interval,
            first_inspection_date=cmd.first_inspection_date,
            next_inspection_date=next_inspection,
        )
        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="equipment.added",
            entity_type="explosionsschutz.Equipment",
            entity_id=equipment.id,
            user_id=user_id,
            payload={"name": cmd.name, "area_id": str(cmd.area_id)},
        )
        return equipment

    @staticmethod
    @transaction.atomic
    def record_inspection(
        cmd: RecordInspectionCmd,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Inspection:
        equipment = Equipment.objects.select_for_update().get(
            pk=cmd.equipment_id, tenant_id=tenant_id
        )
        inspection = Inspection.objects.create(
            tenant_id=tenant_id,
            equipment=equipment,
            inspection_type=cmd.inspection_type,
            scheduled_date=cmd.scheduled_date,
            performed_date=cmd.performed_date,
            performed_by_id=cmd.performed_by_id,
            performed_by_name=cmd.performed_by_name,
            external_inspector=cmd.external_inspector,
            result=cmd.result,
            findings=cmd.findings,
            corrective_actions=cmd.corrective_actions,
            next_inspection_date=cmd.next_inspection_date,
        )
        # Nächste Prüfung am Equipment aktualisieren
        if cmd.next_inspection_date:
            equipment.next_inspection_date = cmd.next_inspection_date
            equipment.save(update_fields=["next_inspection_date", "updated_at"])

        emit_audit_event(
            tenant_id=tenant_id,
            category="explosionsschutz",
            action="inspection.recorded",
            entity_type="explosionsschutz.Inspection",
            entity_id=inspection.id,
            user_id=user_id,
            payload={
                "equipment_id": str(equipment.id),
                "type": cmd.inspection_type,
                "result": cmd.result,
            },
        )
        # Wenn Prüfung fehlgeschlagen → Action via Outbox anlegen
        if cmd.result == Inspection.Result.FAILED:
            OutboxMessage.objects.create(
                tenant_id=tenant_id,
                event_type="explosionsschutz.inspection_failed",
                payload={
                    "inspection_id": str(inspection.id),
                    "equipment_id": str(equipment.id),
                    "equipment_name": equipment.name,
                    "findings": cmd.findings,
                },
                scheduled_at=timezone.now(),
            )
        return inspection
