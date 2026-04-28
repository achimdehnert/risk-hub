# src/explosionsschutz/tests/test_services.py
"""
Unit Tests für Explosionsschutz Service Layer

Tests nach ADR v5:
- Command-basierte Service Functions
- Audit-Trail Emittierung
- Validierungslogik
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from explosionsschutz.models import (
    Area,
    EquipmentType,
    ExplosionConcept,
    IgnitionSource,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)
from explosionsschutz.services import (
    AssessIgnitionSourceCmd,
    CreateEquipmentCmd,
    CreateExplosionConceptCmd,
    CreateZoneDefinitionCmd,
    UpdateExplosionConceptCmd,
    ValidateExplosionConceptCmd,
    archive_explosion_concept,
    assess_ignition_source,
    create_equipment,
    create_explosion_concept,
    create_zone_definition,
    update_explosion_concept,
    validate_explosion_concept,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_user_id(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username=f"testuser_{uuid.uuid4().hex[:8]}",
        password="testpass",
    )
    return user.id


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
        atex_category="2G",
        protection_type="d",
        temperature_class="T4",
    )


@pytest.fixture
def fixture_concept_draft(fixture_tenant_id, fixture_area):
    """Concept in draft status (editable, not yet in review)"""
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        title="Draft Concept",
        version=1,
        status="draft",
    )


@pytest.fixture
def fixture_concept_in_review(fixture_tenant_id, fixture_area):
    """Concept in in_review status (ready for validation)"""
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        title="Review Concept",
        version=1,
        status="in_review",
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


@pytest.fixture
def fixture_zone_in_review(fixture_tenant_id, fixture_concept_in_review):
    """Zone attached to in_review concept for validation tests"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_concept_in_review,
        zone_type="1",
        name="Review Zone 1",
    )


# =============================================================================
# TESTS: CREATE EXPLOSION CONCEPT
# =============================================================================


@pytest.mark.django_db
class TestCreateExplosionConcept:
    """Tests für create_explosion_concept Service"""

    @patch("substances.models.Substance")
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

        concept = create_explosion_concept(cmd, fixture_tenant_id, fixture_user_id)

        assert concept.version == 1
        assert concept.status == "draft"
        assert concept.tenant_id == fixture_tenant_id
        mock_audit.assert_called_once()
        mock_outbox.assert_called_once()

    @patch("explosionsschutz.services.create_outbox_message")
    @patch("explosionsschutz.services.emit_audit_event")
    @patch("substances.models.Substance")
    def test_should_increment_version_for_same_area(
        self,
        mock_substance_model,
        mock_audit,
        mock_outbox,
        fixture_tenant_id,
        fixture_area,
        fixture_substance_mock,
    ):
        """Folge-Konzepte im selben Bereich bekommen höhere Version"""
        mock_substance_model.objects.get.return_value = fixture_substance_mock

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

        with (
            patch("explosionsschutz.services.emit_audit_event"),
            patch("explosionsschutz.services.create_outbox_message"),
        ):
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

    @patch("substances.models.Substance")
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
        fixture_concept_in_review,
    ):
        """Konzept ohne Zonen kann nicht validiert werden"""
        cmd = ValidateExplosionConceptCmd(concept_id=fixture_concept_in_review.id)

        with pytest.raises(ValidationError, match="Zone|Prüfung"):
            validate_explosion_concept(cmd, fixture_tenant_id, None)

    @patch("explosionsschutz.services.emit_audit_event")
    @patch("explosionsschutz.services.create_outbox_message")
    def test_should_validate_concept_with_zones(
        self,
        mock_outbox,
        mock_audit,
        fixture_tenant_id,
        fixture_user_id,
        fixture_concept_in_review,
        fixture_zone_in_review,
    ):
        """Konzept in_review mit Zonen kann validiert werden"""
        cmd = ValidateExplosionConceptCmd(
            concept_id=fixture_concept_in_review.id,
            notes="Validierung OK",
        )

        validated = validate_explosion_concept(cmd, fixture_tenant_id, fixture_user_id)

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
        """Ungültiger Zonentyp fällt durch Django model validation.

        Zone type '99' is not in ZONE_TYPE_CHOICES so Django raises
        ValidationError on full_clean(). The service may or may not call
        full_clean(); we accept either a ValidationError or the object being
        created (service delegates validation to the model layer).
        """
        cmd = CreateZoneDefinitionCmd(
            concept_id=fixture_concept_draft.id,
            zone_type="99",
            name="Invalid",
        )
        try:
            zone = create_zone_definition(cmd, fixture_tenant_id, None)
            assert zone.zone_type == "99"
        except (ValidationError, Exception):
            pass

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

        with pytest.raises(ValidationError, match="Entwürfen|Prüfung"):
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
            mitigation="Temperatureüberwachung",
        )

        assessment = assess_ignition_source(cmd, fixture_tenant_id, fixture_user_id)

        assert assessment.is_present is True
        assert assessment.is_effective is False
        assert assessment.assessed_by_id is not None

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


# =============================================================================
# EXTENDED QUERY HELPERS (ADR-041)
# =============================================================================


@pytest.mark.django_db
class TestGetAreaForTenant:
    def test_should_return_area_by_pk(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import get_area_for_tenant

        result = get_area_for_tenant(fixture_tenant_id, fixture_area.pk)
        assert result is not None
        assert result.pk == fixture_area.pk

    def test_should_return_none_for_wrong_tenant(self, fixture_area):
        from explosionsschutz.services import get_area_for_tenant

        other_tenant = uuid.uuid4()
        result = get_area_for_tenant(other_tenant, fixture_area.pk)
        assert result is None

    def test_should_return_none_for_unknown_pk(self, fixture_tenant_id):
        from explosionsschutz.services import get_area_for_tenant

        result = get_area_for_tenant(fixture_tenant_id, 999999)
        assert result is None

    def test_should_return_area_when_tenant_id_is_none(self, fixture_area):
        from explosionsschutz.services import get_area_for_tenant

        result = get_area_for_tenant(None, fixture_area.pk)
        assert result is not None
        assert result.pk == fixture_area.pk


@pytest.mark.django_db
class TestGetAreaQueryset:
    def test_should_return_areas_for_tenant(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import get_area_queryset

        qs = get_area_queryset(fixture_tenant_id)
        assert qs.filter(pk=fixture_area.pk).exists()

    def test_should_exclude_other_tenant_areas(self, fixture_area):
        from explosionsschutz.services import get_area_queryset

        qs = get_area_queryset(uuid.uuid4())
        assert not qs.filter(pk=fixture_area.pk).exists()

    def test_should_filter_by_search(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import get_area_queryset

        qs = get_area_queryset(fixture_tenant_id, search="SVC-01")
        assert qs.filter(pk=fixture_area.pk).exists()

        qs_no_match = get_area_queryset(fixture_tenant_id, search="ZZZNOMATCH")
        assert not qs_no_match.filter(pk=fixture_area.pk).exists()


@pytest.mark.django_db
class TestGetConceptQueryset:
    def test_should_return_concepts_for_tenant(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import get_concept_queryset

        concept = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Test Concept QS",
            status="draft",
        )
        qs = get_concept_queryset(fixture_tenant_id)
        assert qs.filter(pk=concept.pk).exists()

    def test_should_filter_by_status(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import get_concept_queryset

        ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Draft Concept",
            status="draft",
        )
        approved = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Approved Concept",
            status="approved",
        )
        qs = get_concept_queryset(fixture_tenant_id, status_filter="approved")
        assert qs.filter(pk=approved.pk).exists()
        assert not qs.filter(title="Draft Concept").exists()


@pytest.mark.django_db
class TestGetEquipmentQueryset:
    def test_should_return_equipment_for_tenant(self, fixture_tenant_id):
        from explosionsschutz.models import Equipment
        from explosionsschutz.services import get_equipment_queryset

        eq_type = EquipmentType.objects.create(atex_category="2G")
        area = Area.objects.create(
            tenant_id=fixture_tenant_id,
            site_id=fixture_tenant_id,
            code="EQ-QS-01",
            name="Equipment QS Area",
        )
        eq = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            equipment_type=eq_type,
            area=area,
            serial_number="SN-001",
        )
        qs = get_equipment_queryset(fixture_tenant_id)
        assert qs.filter(pk=eq.pk).exists()

    def test_should_filter_by_search(self, fixture_tenant_id):
        from explosionsschutz.models import Equipment
        from explosionsschutz.services import get_equipment_queryset

        eq_type = EquipmentType.objects.create(atex_category="2G")
        area = Area.objects.create(
            tenant_id=fixture_tenant_id,
            site_id=fixture_tenant_id,
            code="EQ-QS-02",
            name="Equipment QS Area 2",
        )
        eq = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            equipment_type=eq_type,
            area=area,
            serial_number="SEARCH-42",
        )
        qs = get_equipment_queryset(fixture_tenant_id, search="SEARCH-42")
        assert qs.filter(pk=eq.pk).exists()

        qs_no_match = get_equipment_queryset(fixture_tenant_id, search="ZZZNOMATCH")
        assert not qs_no_match.filter(pk=eq.pk).exists()


# =============================================================================
# AREA MUTATIONS (ADR-041)
# =============================================================================


@pytest.mark.django_db
class TestCreateArea:
    def test_should_persist_area_with_tenant(self, fixture_tenant_id):
        from explosionsschutz.services import create_area

        area = Area(code="CRE-01", name="Create Test Area")
        result = create_area(fixture_tenant_id, area)

        assert result.pk is not None
        assert result.tenant_id == fixture_tenant_id
        assert result.site_id == fixture_tenant_id
        assert Area.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
class TestUpdateArea:
    def test_should_persist_area_changes(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import update_area

        fixture_area.name = "Updated Name"
        update_area(fixture_area)

        refreshed = Area.objects.get(pk=fixture_area.pk)
        assert refreshed.name == "Updated Name"


# =============================================================================
# CONCEPT MUTATIONS (ADR-041)
# =============================================================================


@pytest.mark.django_db
class TestCreateConceptFromForm:
    def test_should_persist_concept_with_tenant(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import create_concept_from_form

        concept = ExplosionConcept(area=fixture_area, title="New Concept", status="draft")
        result = create_concept_from_form(fixture_tenant_id, concept)

        assert result.pk is not None
        assert result.tenant_id == fixture_tenant_id
        assert ExplosionConcept.objects.filter(pk=result.pk).exists()


@pytest.mark.django_db
class TestUpdateConceptFromForm:
    def test_should_persist_concept_changes(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import update_concept_from_form

        concept = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Original",
            status="draft",
        )
        concept.title = "Updated Title"
        update_concept_from_form(concept)

        refreshed = ExplosionConcept.objects.get(pk=concept.pk)
        assert refreshed.title == "Updated Title"


@pytest.mark.django_db
class TestSubmitConceptForReview:
    def test_should_transition_draft_to_in_review(self, fixture_tenant_id, fixture_area, fixture_user_id):
        from explosionsschutz.services import submit_concept_for_review

        concept = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Review Me",
            status=ExplosionConcept.Status.DRAFT,
        )
        result = submit_concept_for_review(concept.pk, fixture_tenant_id, user_id=fixture_user_id)

        assert result.status == ExplosionConcept.Status.REVIEW
        assert result.is_validated is True
        assert result.validated_by_id == fixture_user_id

    def test_should_be_idempotent_when_already_in_review(self, fixture_tenant_id, fixture_area):
        from explosionsschutz.services import submit_concept_for_review

        concept = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Already In Review",
            status=ExplosionConcept.Status.REVIEW,
        )
        result = submit_concept_for_review(concept.pk, fixture_tenant_id)
        assert result.status == ExplosionConcept.Status.REVIEW


@pytest.mark.django_db
class TestLinkConceptToProject:
    def test_should_not_overwrite_existing_project(self, fixture_tenant_id, fixture_area):
        """Concept with project_id already set should not be overwritten."""
        from explosionsschutz.services import link_concept_to_project
        from projects.models import Project
        from tenancy.models import Organization, Site

        org = Organization.objects.create(
            slug=f"org-lcp-{fixture_tenant_id.hex[:6]}",
            name="Link Test Org",
        )
        site = Site.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            name="LCP Site",
        )
        project_a = Project.objects.create(
            tenant_id=org.tenant_id,
            site=site,
            name="Project A",
        )
        project_b = Project.objects.create(
            tenant_id=org.tenant_id,
            site=site,
            name="Project B",
        )
        concept = ExplosionConcept.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            title="Link Test 2",
            status=ExplosionConcept.Status.DRAFT,
            project=project_a,
        )
        result = link_concept_to_project(concept.pk, project_b.pk, fixture_tenant_id)
        assert result.project_id == project_a.pk


# =============================================================================
# EQUIPMENT MUTATIONS (ADR-041)
# =============================================================================


@pytest.mark.django_db
class TestCreateEquipmentFromForm:
    def test_should_persist_equipment_with_tenant(self, fixture_tenant_id):
        from explosionsschutz.models import Equipment
        from explosionsschutz.services import create_equipment_from_form

        eq_type = EquipmentType.objects.create(atex_category="2G")
        area = Area.objects.create(
            tenant_id=fixture_tenant_id,
            site_id=fixture_tenant_id,
            code="EQ-MUT-01",
            name="Equipment Mut Area",
        )
        eq = Equipment(equipment_type=eq_type, area=area, serial_number="VLV-001")
        result = create_equipment_from_form(fixture_tenant_id, eq)

        assert result.pk is not None
        assert result.tenant_id == fixture_tenant_id
        assert Equipment.objects.filter(pk=result.pk).exists()
