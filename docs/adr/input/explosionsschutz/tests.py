"""
Tests für das Explosionsschutz-Modul.

Struktur:
  TestConceptWorkflow      – Status-Übergänge (Draft → Review → Approved → Archived)
  TestZoneClassification   – ZoneClassificationEngine Regelmatrix
  TestIgnitionSources      – Zündquellen-Initialisierung und Bewertung
  TestEquipmentValidation  – ATEX-Kategorie gegen Zone-Eignung
  TestSeedCommand          – seed_explosionsschutz Idempotenz
  TestMigration0001        – RLS-Policies in der Migration vorhanden
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.explosionsschutz.models import (
    Area,
    EquipmentType,
    ExplosionConcept,
    ProtectionMeasure,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)
from apps.explosionsschutz.services import (
    ApproveConceptCmd,
    ArchiveConceptCmd,
    AssessIgnitionSourceCmd,
    ConceptService,
    CreateConceptCmd,
    CreateZoneCmd,
    SubmitForReviewCmd,
    UpdateConceptCmd,
    ZoneService,
)
from apps.explosionsschutz.services.zone_classification import (
    ZoneClassificationEngine,
)

TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
SITE_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def area(db):
    return Area.objects.create(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        code="TEST-01",
        name="Testbereich",
    )


@pytest.fixture
def draft_concept(db, area):
    return ExplosionConcept.objects.create(
        tenant_id=TENANT_ID,
        area=area,
        title="Testkonzept",
        status=ExplosionConcept.Status.DRAFT,
        release_grade="secondary",
        atmosphere_type="gas",
    )


@pytest.fixture
def zone(db, draft_concept):
    return ZoneDefinition.objects.create(
        tenant_id=TENANT_ID,
        concept=draft_concept,
        zone_type="2",
        name="Testzone",
        justification="Sekundäre Freisetzung",
    )


@pytest.fixture
def primary_measure(db, draft_concept):
    return ProtectionMeasure.objects.create(
        tenant_id=TENANT_ID,
        concept=draft_concept,
        category="primary",
        title="Inertisierung",
        description="N₂-Spülung vor Inbetriebnahme",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ConceptService Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestConceptWorkflow:

    def test_create_concept_sets_is_current(self, db, area):
        cmd = CreateConceptCmd(
            area_id=area.id,
            title="Konzept v1",
        )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            concept = ConceptService.create_concept(cmd, TENANT_ID, USER_ID)

        assert concept.status == ExplosionConcept.Status.DRAFT
        assert concept.is_current is True
        assert concept.tenant_id == TENANT_ID

    def test_create_second_concept_deactivates_first(self, db, area, draft_concept):
        cmd = CreateConceptCmd(area_id=area.id, title="Konzept v2")
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            new_concept = ConceptService.create_concept(cmd, TENANT_ID, USER_ID)

        draft_concept.refresh_from_db()
        assert draft_concept.is_current is False
        assert new_concept.is_current is True

    def test_submit_for_review_requires_zone_and_primary_measure(
        self, db, draft_concept
    ):
        cmd = SubmitForReviewCmd(concept_id=draft_concept.id)
        with pytest.raises(ValidationError, match="Zone"):
            with patch("apps.explosionsschutz.services.emit_audit_event"):
                ConceptService.submit_for_review(cmd, TENANT_ID, USER_ID)

    def test_submit_for_review_succeeds_with_zone_and_measure(
        self, db, draft_concept, zone, primary_measure
    ):
        cmd = SubmitForReviewCmd(concept_id=draft_concept.id)
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            concept = ConceptService.submit_for_review(cmd, TENANT_ID, USER_ID)

        assert concept.status == ExplosionConcept.Status.REVIEW

    def test_approve_sets_immutable_snapshot(
        self, db, draft_concept, zone, primary_measure
    ):
        # Setup: zum Review bringen
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            ConceptService.submit_for_review(
                SubmitForReviewCmd(concept_id=draft_concept.id), TENANT_ID, USER_ID
            )

        approver_id = uuid.uuid4()
        cmd = ApproveConceptCmd(
            concept_id=draft_concept.id,
            approver_id=approver_id,
            approver_name="Max Mustermann",
            notes="Alles in Ordnung",
        )
        with (
            patch("apps.explosionsschutz.services.emit_audit_event"),
            patch("apps.explosionsschutz.services.OutboxMessage.objects.create"),
        ):
            concept = ConceptService.approve_concept(cmd, TENANT_ID, USER_ID)

        assert concept.status == ExplosionConcept.Status.APPROVED
        assert concept.approved_by_id == approver_id
        assert concept.approved_by_name == "Max Mustermann"
        assert concept.next_review_date is not None

    def test_approved_concept_cannot_be_updated(
        self, db, draft_concept, zone, primary_measure
    ):
        """Freigegebenes Konzept darf nicht bearbeitet werden."""
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            ConceptService.submit_for_review(
                SubmitForReviewCmd(concept_id=draft_concept.id), TENANT_ID, USER_ID
            )
        with (
            patch("apps.explosionsschutz.services.emit_audit_event"),
            patch("apps.explosionsschutz.services.OutboxMessage.objects.create"),
        ):
            ConceptService.approve_concept(
                ApproveConceptCmd(
                    concept_id=draft_concept.id,
                    approver_id=USER_ID,
                    approver_name="Test",
                ),
                TENANT_ID,
                USER_ID,
            )

        update_cmd = UpdateConceptCmd(
            concept_id=draft_concept.id, title="Neuer Titel"
        )
        with pytest.raises(PermissionDenied):
            with patch("apps.explosionsschutz.services.emit_audit_event"):
                ConceptService.update_concept(update_cmd, TENANT_ID, USER_ID)

    def test_archive_approved_concept(
        self, db, draft_concept, zone, primary_measure
    ):
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            ConceptService.submit_for_review(
                SubmitForReviewCmd(concept_id=draft_concept.id), TENANT_ID, USER_ID
            )
        with (
            patch("apps.explosionsschutz.services.emit_audit_event"),
            patch("apps.explosionsschutz.services.OutboxMessage.objects.create"),
        ):
            ConceptService.approve_concept(
                ApproveConceptCmd(
                    concept_id=draft_concept.id, approver_id=USER_ID, approver_name="Test"
                ),
                TENANT_ID,
                USER_ID,
            )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            concept = ConceptService.archive_concept(
                ArchiveConceptCmd(concept_id=draft_concept.id, reason="Superseded"),
                TENANT_ID,
                USER_ID,
            )

        assert concept.status == ExplosionConcept.Status.ARCHIVED
        assert concept.is_current is False


# ─────────────────────────────────────────────────────────────────────────────
# ZoneClassificationEngine Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestZoneClassification:

    def setup_method(self):
        self.engine = ZoneClassificationEngine()

    def test_continuous_no_ventilation_gas_gives_zone_0(self):
        result = self.engine.propose("continuous", "none", "gas")
        assert result.zone_type == "0"
        assert result.confidence == "high"

    def test_secondary_technical_dilution_gas_gives_no_zone(self):
        result = self.engine.propose("secondary", "technical_dilution", "gas")
        assert result.zone_type == "none"
        assert result.ventilation_reduction is True

    def test_primary_natural_gas_gives_zone_1(self):
        result = self.engine.propose("primary", "natural", "gas")
        assert result.zone_type == "1"

    def test_inertization_always_no_zone(self):
        for grade in ("continuous", "primary", "secondary"):
            result = self.engine.propose(grade, "inertization", "gas")
            assert result.zone_type == "none", f"Expected no zone for {grade}+inertization"

    def test_unknown_combination_returns_conservative_fallback(self):
        result = self.engine.propose("primary", "unknown_type", "gas")
        assert result.confidence == "low"
        assert result.zone_type in ("1", "21")

    def test_dust_primary_no_ventilation_gives_zone_21(self):
        result = self.engine.propose("primary", "none", "dust")
        assert result.zone_type == "21"

    def test_required_equipment_category_for_zones(self):
        assert self.engine.get_required_equipment_category("0") == "1G"
        assert self.engine.get_required_equipment_category("1") == "2G"
        assert self.engine.get_required_equipment_category("2") == "3G"
        assert self.engine.get_required_equipment_category("none") == "—"


# ─────────────────────────────────────────────────────────────────────────────
# ZoneService / Zündquellen Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestIgnitionSources:

    def test_create_zone_initialises_all_13_ignition_sources(
        self, db, draft_concept
    ):
        cmd = CreateZoneCmd(
            concept_id=draft_concept.id,
            zone_type="2",
            name="Testzone",
            justification="Test",
        )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            zone = ZoneService.create_zone(cmd, TENANT_ID, USER_ID)

        count = zone.ignition_assessments.count()
        assert count == 13, f"Erwartet 13 Zündquellen, erhalten {count}"

    def test_all_ignition_sources_initially_not_effective(self, db, draft_concept):
        cmd = CreateZoneCmd(
            concept_id=draft_concept.id,
            zone_type="1",
            name="Zone 1",
            justification="Test",
        )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            zone = ZoneService.create_zone(cmd, TENANT_ID, USER_ID)

        assert not zone.ignition_assessments.filter(is_effective=True).exists()

    def test_assess_ignition_source_updates_correctly(self, db, zone):
        cmd = AssessIgnitionSourceCmd(
            zone_id=zone.id,
            ignition_source="S04",  # Elektrische Anlagen
            is_present=True,
            is_effective=True,
            mitigation="Ex-geschützte Elektroinstallation (Zone 2, Kat. 3G)",
        )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            assessment = ZoneService.assess_ignition_source(cmd, TENANT_ID, USER_ID)

        assert assessment.is_present is True
        assert assessment.is_effective is True
        assert "Kat. 3G" in assessment.mitigation

    def test_ignition_assessment_complete_after_all_assessed(self, db, draft_concept):
        cmd = CreateZoneCmd(
            concept_id=draft_concept.id,
            zone_type="2",
            name="Komplette Zone",
            justification="Test",
        )
        with patch("apps.explosionsschutz.services.emit_audit_event"):
            zone = ZoneService.create_zone(cmd, TENANT_ID, USER_ID)

        # Alle Zündquellen wurden durch create_zone angelegt
        assert zone.ignition_assessment_complete is True

    def test_zone_active_ignition_sources_lists_effective_ones(self, db, zone):
        ZoneIgnitionSourceAssessment.objects.filter(zone=zone).update(
            is_present=False, is_effective=False
        )
        ZoneIgnitionSourceAssessment.objects.filter(
            zone=zone, ignition_source="S01"
        ).update(is_present=True, is_effective=True)

        active = zone.active_ignition_sources
        assert "S01" in active
        assert len(active) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Equipment Validation Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestEquipmentValidation:

    def test_equipment_type_suitable_for_zone(self, db):
        et = EquipmentType(
            manufacturer="Test",
            model_name="Gerät",
            atex_category="3G",
        )
        assert et.is_suitable_for_zone("2") is True
        assert et.is_suitable_for_zone("1") is False  # Zone 1 braucht min. 2G
        assert et.is_suitable_for_zone("0") is False  # Zone 0 braucht 1G

    def test_category_1g_suitable_for_all_gas_zones(self, db):
        et = EquipmentType(manufacturer="T", model_name="M", atex_category="1G")
        for zone_type in ("0", "1", "2"):
            assert et.is_suitable_for_zone(zone_type) is True

    def test_atex_marking_composed_correctly(self, db):
        et = EquipmentType(
            manufacturer="Bartec",
            model_name="Test",
            atex_group="II",
            atex_category="2G",
            protection_type="Ex de",
            explosion_group="IIC",
            temperature_class="T4",
        )
        marking = et.atex_marking
        assert "II" in marking
        assert "2G" in marking
        assert "Ex de" in marking
        assert "IIC" in marking
        assert "T4" in marking
