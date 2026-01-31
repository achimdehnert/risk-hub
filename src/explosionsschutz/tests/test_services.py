# src/explosionsschutz/tests/test_services.py
"""
Unit Tests für Explosionsschutz Service Layer

Tests nach ADR v5:
- Command-basierte Service Functions
- Audit-Trail Emittierung
- Validierungslogik
"""

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from django.core.exceptions import ValidationError, PermissionDenied

from explosionsschutz.models import (
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    EquipmentType,
    ZoneIgnitionSourceAssessment,
    IgnitionSource,
)
from explosionsschutz.services import (
    create_explosion_concept,
    update_explosion_concept,
    validate_explosion_concept,
    create_zone_definition,
    create_protection_measure,
    create_equipment,
    assess_ignition_source,
    archive_explosion_concept,
    CreateExplosionConceptCmd,
    UpdateExplosionConceptCmd,
    ValidateExplosionConceptCmd,
    CreateZoneDefinitionCmd,
    CreateProtectionMeasureCmd,
    CreateEquipmentCmd,
    AssessIgnitionSourceCmd,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_user_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_area(fixture_tenant_id):
    return Area.objects.create(
        tenant_id=fixture_tenant_id,
        site_id=uuid.uuid4(),
        code="SVC-01",
        name="Service Test Area",
    )


@pytest.fixture
def fixture_substance_mock():
    """Mock für externes Substance-Model"""
    substance = MagicMock()
    substance.id = uuid.uuid4()
    substance.name = "Ethanol"
    return substance


@pytest.fixture
def fixture_equipment_type(fixture_tenant_id):
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="Test",
        model="Model-1",
        atex_group="II",
        atex_category="2",
        protection_type="d",
        temperature_class="T4",
    )


@pytest.fixture
def fixture_concept_draft(fixture_tenant_id, fixture_area):
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        title="Draft Concept",
        version=1,
        status="draft",
    )


@pytest.fixture
def fixture_concept_approved(fixture_tenant_id, fixture_area):
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        title="Approved Concept",
        version=1,
        status="approved",
        is_validated=True,
    )


@pytest.fixture
def fixture_zone_1(fixture_tenant_id, fixture_concept_draft):
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_concept_draft,
        zone_type="1",
        name="Test Zone 1",
    )


# =============================================================================
# TESTS: CREATE EXPLOSION CONCEPT
# =============================================================================

@pytest.mark.django_db
class TestCreateExplosionConcept:
    """Tests für create_explosion_concept Service"""

    @patch("explosionsschutz.services.Substance")
    @patch("explosionsschutz.services.emit_audit_event")
    @patch("explosionsschutz.services.create_outbox_message")
    def test_should_create_concept_with_version_1(
        self,
        mock_outbox,
        mock_audit,
        mock_substance_model,
        fixture_tenant_id,
        fixture_user_id,
        fixture_area,
        fixture_substance_mock,
    ):
        """Erstes Konzept bekommt Version 1"""
        mock_substance_model.objects.get.return_value = fixture_substance_mock

        cmd = CreateExplosionConceptCmd(
            area_id=fixture_area.id,
            substance_id=fixture_substance_mock.id,
            title="Test Konzept",
        )

        concept = create_explosion_concept(
            cmd, fixture_tenant_id, fixture_user_id
        )

        assert concept.version == 1
        assert concept.status == "draft"
        assert concept.tenant_id == fixture_tenant_id
        mock_audit.assert_called_once()
        mock_outbox.assert_called_once()

    @patch("explosionsschutz.services.Substance")
    def test_should_increment_version_for_same_area(
        self,
        mock_substance_model,
        fixture_tenant_id,
        fixture_area,
        fixture_substance_mock,
    ):
        """Folge-Konzepte im selben Bereich bekommen höhere Version"""
        mock_substance_model.objects.get.return_value = fixture_substance_mock

        # Erstes Konzept existiert bereits
        ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            substance_id=uuid.uuid4(),
            title="Existing",
            version=1,
        )

        cmd = CreateExplosionConceptCmd(
            area_id=fixture_area.id,
            substance_id=fixture_substance_mock.id,
            title="Zweites Konzept",
        )

        concept = create_explosion_concept(cmd, fixture_tenant_id, None)
        assert concept.version == 2

    def test_should_reject_without_tenant(self, fixture_area):
        """Ohne tenant_id wird PermissionDenied geworfen"""
        cmd = CreateExplosionConceptCmd(
            area_id=fixture_area.id,
            substance_id=uuid.uuid4(),
            title="Test",
        )

        with pytest.raises(PermissionDenied):
            create_explosion_concept(cmd, None, None)

    @patch("explosionsschutz.services.Substance")
    def test_should_reject_area_from_other_tenant(
        self,
        mock_substance_model,
        fixture_area,
        fixture_substance_mock,
    ):
        """Area eines anderen Tenants wird abgelehnt"""
        mock_substance_model.objects.get.return_value = fixture_substance_mock
        other_tenant = uuid.uuid4()

        cmd = CreateExplosionConceptCmd(
            area_id=fixture_area.id,
            substance_id=fixture_substance_mock.id,
            title="Test",
        )

        with pytest.raises(PermissionDenied):
            create_explosion_concept(cmd, other_tenant, None)


# =============================================================================
# TESTS: UPDATE EXPLOSION CONCEPT
# =============================================================================

@pytest.mark.django_db
class TestUpdateExplosionConcept:
    """Tests für update_explosion_concept Service"""

    @patch("explosionsschutz.services.emit_audit_event")
    def test_should_update_title(
        self,
        mock_audit,
        fixture_tenant_id,
        fixture_concept_draft,
    ):
        """Titel kann bei Draft geändert werden"""
        cmd = UpdateExplosionConceptCmd(
            concept_id=fixture_concept_draft.id,
            title="Neuer Titel",
        )

        updated = update_explosion_concept(cmd, fixture_tenant_id, None)
        assert updated.title == "Neuer Titel"
        mock_audit.assert_called_once()

    def test_should_reject_update_on_approved(
        self,
        fixture_tenant_id,
        fixture_concept_approved,
    ):
        """Freigegebene Konzepte können nicht geändert werden"""
        cmd = UpdateExplosionConceptCmd(
            concept_id=fixture_concept_approved.id,
            title="Versuch",
        )

        with pytest.raises(ValidationError):
            update_explosion_concept(cmd, fixture_tenant_id, None)


# =============================================================================
# TESTS: VALIDATE EXPLOSION CONCEPT
# =============================================================================

@pytest.mark.django_db
class TestValidateExplosionConcept:
    """Tests für validate_explosion_concept Service"""

    def test_should_reject_concept_without_zones(
        self,
        fixture_tenant_id,
        fixture_concept_draft,
    ):
        """Konzept ohne Zonen kann nicht validiert werden"""
        cmd = ValidateExplosionConceptCmd(concept_id=fixture_concept_draft.id)

        with pytest.raises(ValidationError, match="Zone"):
            validate_explosion_concept(cmd, fixture_tenant_id, None)

    @patch("explosionsschutz.services.emit_audit_event")
    @patch("explosionsschutz.services.create_outbox_message")
    def test_should_validate_concept_with_zones(
        self,
        mock_outbox,
        mock_audit,
        fixture_tenant_id,
        fixture_user_id,
        fixture_concept_draft,
        fixture_zone_1,
    ):
        """Konzept mit Zonen kann validiert werden"""
        cmd = ValidateExplosionConceptCmd(
            concept_id=fixture_concept_draft.id,
            notes="Validierung OK",
        )

        validated = validate_explosion_concept(
            cmd, fixture_tenant_id, fixture_user_id
        )

        assert validated.status == "approved"
        assert validated.is_validated is True
        assert validated.validated_by_id == fixture_user_id


# =============================================================================
# TESTS: CREATE ZONE DEFINITION
# =============================================================================

@pytest.mark.django_db
class TestCreateZoneDefinition:
    """Tests für create_zone_definition Service"""

    @patch("explosionsschutz.services.emit_audit_event")
    def test_should_create_zone(
        self,
        mock_audit,
        fixture_tenant_id,
        fixture_concept_draft,
    ):
        """Zone kann erstellt werden"""
        cmd = CreateZoneDefinitionCmd(
            concept_id=fixture_concept_draft.id,
            zone_type="2",
            name="Neue Zone 2",
            justification="Gelegentlich explosionsfähig",
        )

        zone = create_zone_definition(cmd, fixture_tenant_id, None)

        assert zone.zone_type == "2"
        assert zone.name == "Neue Zone 2"
        mock_audit.assert_called_once()

    def test_should_reject_invalid_zone_type(
        self,
        fixture_tenant_id,
        fixture_concept_draft,
    ):
        """Ungültiger Zonentyp wird abgelehnt"""
        cmd = CreateZoneDefinitionCmd(
            concept_id=fixture_concept_draft.id,
            zone_type="99",
            name="Invalid",
        )

        with pytest.raises(ValidationError, match="Zonentyp"):
            create_zone_definition(cmd, fixture_tenant_id, None)

    def test_should_reject_zone_on_approved_concept(
        self,
        fixture_tenant_id,
        fixture_concept_approved,
    ):
        """Zonen können nicht zu freigegebenen Konzepten hinzugefügt werden"""
        cmd = CreateZoneDefinitionCmd(
            concept_id=fixture_concept_approved.id,
            zone_type="1",
            name="Test",
        )

        with pytest.raises(ValidationError, match="Entwürfen"):
            create_zone_definition(cmd, fixture_tenant_id, None)


# =============================================================================
# TESTS: CREATE EQUIPMENT
# =============================================================================

@pytest.mark.django_db
class TestCreateEquipment:
    """Tests für create_equipment Service"""

    @patch("explosionsschutz.services.emit_audit_event")
    @patch("explosionsschutz.services.create_outbox_message")
    def test_should_create_equipment_in_compatible_zone(
        self,
        mock_outbox,
        mock_audit,
        fixture_tenant_id,
        fixture_area,
        fixture_zone_1,
        fixture_equipment_type,
    ):
        """Equipment mit passender Kategorie wird erstellt"""
        cmd = CreateEquipmentCmd(
            area_id=fixture_area.id,
            equipment_type_id=fixture_equipment_type.id,
            zone_id=fixture_zone_1.id,
            serial_number="EQ-001",
        )

        equipment = create_equipment(cmd, fixture_tenant_id, None)

        assert equipment.serial_number == "EQ-001"
        assert equipment.zone_id == fixture_zone_1.id

    def test_should_reject_incompatible_equipment(
        self,
        fixture_tenant_id,
        fixture_area,
        fixture_concept_draft,
    ):
        """Kategorie 3 Equipment wird in Zone 0 abgelehnt"""
        zone_0 = ZoneDefinition.objects.create(
            tenant_id=fixture_tenant_id,
            concept=fixture_concept_draft,
            zone_type="0",
            name="Zone 0",
        )

        cat3_type = EquipmentType.objects.create(
            tenant_id=fixture_tenant_id,
            manufacturer="Test",
            model="Cat3",
            atex_group="II",
            atex_category="3",
        )

        cmd = CreateEquipmentCmd(
            area_id=fixture_area.id,
            equipment_type_id=cat3_type.id,
            zone_id=zone_0.id,
            serial_number="FAIL",
        )

        with pytest.raises(ValidationError, match="nicht zulässig"):
            create_equipment(cmd, fixture_tenant_id, None)


# =============================================================================
# TESTS: ASSESS IGNITION SOURCE
# =============================================================================

@pytest.mark.django_db
class TestAssessIgnitionSource:
    """Tests für assess_ignition_source Service"""

    @patch("explosionsschutz.services.emit_audit_event")
    def test_should_create_assessment(
        self,
        mock_audit,
        fixture_tenant_id,
        fixture_user_id,
        fixture_zone_1,
    ):
        """Zündquellenbewertung wird erstellt"""
        cmd = AssessIgnitionSourceCmd(
            zone_id=fixture_zone_1.id,
            ignition_source=IgnitionSource.S1_HOT_SURFACES,
            is_present=True,
            is_effective=False,
            mitigation="Temperaturüberwachung",
        )

        assessment = assess_ignition_source(
            cmd, fixture_tenant_id, fixture_user_id
        )

        assert assessment.is_present is True
        assert assessment.is_effective is False
        assert assessment.assessed_by_id == fixture_user_id

    @patch("explosionsschutz.services.emit_audit_event")
    def test_should_update_existing_assessment(
        self,
        mock_audit,
        fixture_tenant_id,
        fixture_zone_1,
    ):
        """Bestehende Bewertung wird aktualisiert"""
        ZoneIgnitionSourceAssessment.objects.create(
            tenant_id=fixture_tenant_id,
            zone=fixture_zone_1,
            ignition_source=IgnitionSource.S4_ELECTRICAL,
            is_present=True,
            is_effective=True,
        )

        cmd = AssessIgnitionSourceCmd(
            zone_id=fixture_zone_1.id,
            ignition_source=IgnitionSource.S4_ELECTRICAL,
            is_present=True,
            is_effective=False,
            mitigation="Ex-Schutz installiert",
        )

        assessment = assess_ignition_source(cmd, fixture_tenant_id, None)
        assert assessment.is_effective is False
        assert assessment.mitigation == "Ex-Schutz installiert"


# =============================================================================
# TESTS: ARCHIVE EXPLOSION CONCEPT
# =============================================================================

@pytest.mark.django_db
class TestArchiveExplosionConcept:
    """Tests für archive_explosion_concept Service"""

    @patch("explosionsschutz.services.emit_audit_event")
    def test_should_archive_approved_concept(
        self,
        mock_audit,
        fixture_tenant_id,
        fixture_concept_approved,
    ):
        """Freigegebenes Konzept kann archiviert werden"""
        archived = archive_explosion_concept(
            fixture_concept_approved.id,
            fixture_tenant_id,
            None,
        )

        assert archived.status == "archived"

    def test_should_reject_archive_draft(
        self,
        fixture_tenant_id,
        fixture_concept_draft,
    ):
        """Entwürfe können nicht archiviert werden"""
        with pytest.raises(ValidationError, match="freigegeben"):
            archive_explosion_concept(
                fixture_concept_draft.id,
                fixture_tenant_id,
                None,
            )
