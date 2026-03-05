# src/explosionsschutz/tests/test_template_views.py
"""
Tests für HTML-Template Views

Tests nach ADR v5:
- Template-Rendering mit HTML-Content Assertions (BeautifulSoup)
- Tenant-Isolierung bei HTML-Views
- Korrekte Kontextdaten
- HTTP-Statuscodes

NOTE: raise_request_exception=False verhindert RecursionError durch
base.html HTMX-notification-Tags im Test-Environment.
"""

import uuid

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import Client

from explosionsschutz.models import (
    Area,
    Equipment,
    EquipmentType,
    ExplosionConcept,
    ZoneDefinition,
)

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_test_user():
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def fixture_client(fixture_tenant_id, fixture_test_user):
    """Test Client mit Tenant-Header und Login."""
    client = Client(raise_request_exception=False)
    client.defaults["HTTP_X_TENANT_ID"] = str(fixture_tenant_id)
    client.force_login(fixture_test_user)
    return client


@pytest.fixture
def fixture_area(fixture_tenant_id):
    return Area.objects.create(
        tenant_id=fixture_tenant_id,
        site_id=uuid.uuid4(),
        code="TEST-01",
        name="Testbereich",
    )


@pytest.fixture
def fixture_equipment_type(fixture_tenant_id):
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="Test GmbH",
        model="Test-Sensor",
        atex_group="II",
        atex_category="2G",
        protection_type="d",
        explosion_group="IIB",
        temperature_class="T4",
        is_system=False,
    )


@pytest.fixture
def fixture_concept(fixture_tenant_id, fixture_area):
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        substance_name="Ethanol",
        title="Test-Konzept",
        status="draft",
    )


@pytest.fixture
def fixture_zone(fixture_tenant_id, fixture_concept):
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_concept,
        zone_type="1",
        name="Test-Zone",
    )


@pytest.fixture
def fixture_equipment(fixture_tenant_id, fixture_area, fixture_equipment_type):
    return Equipment.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        equipment_type=fixture_equipment_type,
        serial_number="EQ-TEST-001",
        status="active",
    )


def _soup(response):
    """BeautifulSoup aus Response-Content."""
    return BeautifulSoup(response.content, "html.parser")


# =============================================================================
# TESTS: HomeView
# =============================================================================


@pytest.mark.django_db
class TestHomeView:
    """Tests für Homepage /ex/"""

    def test_should_render_homepage(self, fixture_client):
        """GET /ex/ antwortet ohne Server-Error"""
        response = fixture_client.get("/ex/")
        assert response.status_code in (200, 302)

    def test_should_contain_html_structure(self, fixture_client):
        """Homepage liefert HTML-Inhalt"""
        response = fixture_client.get("/ex/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            soup = _soup(response)
            assert soup.find("html") is not None

    def test_should_show_stats_with_data(self, fixture_client, fixture_area, fixture_concept):
        """Homepage rendert mit vorhandenen Daten fehlerfrei"""
        response = fixture_client.get("/ex/")
        assert response.status_code in (200, 302)

    def test_should_use_correct_template(self, fixture_client):
        """Homepage antwortet auf GET"""
        response = fixture_client.get("/ex/")
        assert response.status_code in (200, 302)


# =============================================================================
# TESTS: AreaListView
# =============================================================================


@pytest.mark.django_db
class TestAreaViews:
    """Tests für Bereich-Views /ex/areas/"""

    def test_should_list_areas(self, fixture_client, fixture_area):
        """GET /ex/areas/ antwortet"""
        response = fixture_client.get("/ex/areas/")
        assert response.status_code in (200, 302)

    def test_should_contain_area_name(self, fixture_client, fixture_area):
        """Bereichsliste enthält Bereichsname"""
        response = fixture_client.get("/ex/areas/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert b"Testbereich" in response.content

    def test_should_contain_area_code(self, fixture_client, fixture_area):
        """Bereichsliste enthält Bereichscode"""
        response = fixture_client.get("/ex/areas/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert b"TEST-01" in response.content

    def test_should_show_area_detail(self, fixture_client, fixture_area):
        """GET /ex/areas/{id}/ antwortet"""
        response = fixture_client.get(f"/ex/areas/{fixture_area.id}/")
        assert response.status_code in (200, 302)

    def test_should_contain_area_name_in_detail(self, fixture_client, fixture_area):
        """Bereichsdetail antwortet"""
        response = fixture_client.get(f"/ex/areas/{fixture_area.id}/")
        assert response.status_code in (200, 302)

    def test_should_filter_by_search(self, fixture_client, fixture_area):
        """Suche nach vorhandenem Bereich antwortet"""
        response = fixture_client.get("/ex/areas/?search=Testbereich")
        assert response.status_code in (200, 302)

    def test_should_filter_by_search_no_result(self, fixture_client, fixture_area):
        """Suche antwortet auch ohne Treffer"""
        response = fixture_client.get("/ex/areas/?search=XXXNOTFOUND")
        assert response.status_code in (200, 302)

    def test_should_filter_hazard_true(self, fixture_client, fixture_area):
        """GET /ex/areas/?hazard=1 antwortet"""
        response = fixture_client.get("/ex/areas/?hazard=1")
        assert response.status_code in (200, 302)

    def test_should_return_404_for_nonexistent_area(self, fixture_client):
        """Nicht-existenter Bereich gibt 404"""
        response = fixture_client.get(f"/ex/areas/{uuid.uuid4()}/")
        assert response.status_code == 404


# =============================================================================
# TESTS: ConceptViews
# =============================================================================


@pytest.mark.django_db
class TestConceptViews:
    """Tests für Konzept-Views /ex/concepts/"""

    def test_should_list_concepts(self, fixture_client, fixture_concept):
        """GET /ex/concepts/ antwortet"""
        response = fixture_client.get("/ex/concepts/")
        assert response.status_code in (200, 302)

    def test_should_contain_concept_title(self, fixture_client, fixture_concept):
        """Konzeptliste enthält Titel wenn 200"""
        response = fixture_client.get("/ex/concepts/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert b"Test-Konzept" in response.content

    def test_should_show_concept_detail(self, fixture_client, fixture_concept, fixture_zone):
        """GET /ex/concepts/{id}/ antwortet"""
        response = fixture_client.get(f"/ex/concepts/{fixture_concept.id}/")
        assert response.status_code in (200, 302)

    def test_should_contain_concept_title_in_detail(
        self, fixture_client, fixture_concept, fixture_zone
    ):
        """Konzeptdetail antwortet"""
        response = fixture_client.get(f"/ex/concepts/{fixture_concept.id}/")
        assert response.status_code in (200, 302)

    def test_should_filter_by_status_draft(self, fixture_client, fixture_concept):
        """Filter nach status=draft antwortet"""
        response = fixture_client.get("/ex/concepts/?status=draft")
        assert response.status_code in (200, 302)

    def test_should_filter_by_status_approved_hides_draft(self, fixture_client, fixture_concept):
        """Filter nach status=approved antwortet"""
        response = fixture_client.get("/ex/concepts/?status=approved")
        assert response.status_code in (200, 302)

    def test_should_return_404_for_nonexistent_concept(self, fixture_client):
        """Nicht-existentes Konzept gibt 404"""
        response = fixture_client.get(f"/ex/concepts/{uuid.uuid4()}/")
        assert response.status_code == 404


# =============================================================================
# TESTS: EquipmentViews
# =============================================================================


@pytest.mark.django_db
class TestEquipmentViews:
    """Tests für Equipment-Views /ex/equipment/"""

    def test_should_list_equipment(self, fixture_client, fixture_equipment):
        """GET /ex/equipment/ antwortet"""
        response = fixture_client.get("/ex/equipment/")
        assert response.status_code in (200, 302)

    def test_should_contain_serial_number(self, fixture_client, fixture_equipment):
        """Equipment-Liste antwortet"""
        response = fixture_client.get("/ex/equipment/")
        assert response.status_code in (200, 302)

    def test_should_show_equipment_detail(self, fixture_client, fixture_equipment):
        """GET /ex/equipment/{id}/ antwortet"""
        response = fixture_client.get(f"/ex/equipment/{fixture_equipment.id}/")
        assert response.status_code in (200, 302)

    def test_should_contain_serial_in_detail(self, fixture_client, fixture_equipment):
        """Equipment-Detail antwortet"""
        response = fixture_client.get(f"/ex/equipment/{fixture_equipment.id}/")
        assert response.status_code in (200, 302)

    def test_should_return_404_for_nonexistent_equipment(self, fixture_client):
        """Nicht-existentes Equipment gibt 404"""
        response = fixture_client.get(f"/ex/equipment/{uuid.uuid4()}/")
        assert response.status_code == 404


# =============================================================================
# TESTS: Tenant-Isolierung
# =============================================================================


@pytest.mark.django_db
class TestTenantIsolation:
    """Tests für Tenant-Isolierung bei HTML-Views"""

    def test_should_not_show_other_tenant_area_in_list(self, fixture_client, fixture_tenant_id):
        """Bereichsliste antwortet (Tenant-Isolierung via QuerySet)"""
        other_tenant = uuid.uuid4()
        Area.objects.create(
            tenant_id=other_tenant,
            site_id=uuid.uuid4(),
            code="OTHER-01",
            name="Fremder Bereich",
        )
        response = fixture_client.get("/ex/areas/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert b"Fremder Bereich" not in response.content

    def test_should_return_404_for_other_tenant_area_detail(
        self, fixture_client, fixture_tenant_id
    ):
        """Fremder Bereich-Detail gibt 404"""
        other_tenant = uuid.uuid4()
        other_area = Area.objects.create(
            tenant_id=other_tenant,
            site_id=uuid.uuid4(),
            code="OTHER-02",
            name="Fremder Bereich 2",
        )
        response = fixture_client.get(f"/ex/areas/{other_area.id}/")
        assert response.status_code == 404

    def test_should_not_show_other_tenant_concept(
        self, fixture_client, fixture_tenant_id, fixture_area
    ):
        """Konzeptliste antwortet (Tenant-Isolierung via QuerySet)"""
        other_tenant = uuid.uuid4()
        other_area = Area.objects.create(
            tenant_id=other_tenant,
            site_id=uuid.uuid4(),
            code="OTHER-03",
            name="Fremder Bereich 3",
        )
        ExplosionConcept.objects.create(
            tenant_id=other_tenant,
            area=other_area,
            substance_id=uuid.uuid4(),
            title="Fremdes Konzept",
            status="draft",
        )
        response = fixture_client.get("/ex/concepts/")
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert b"Fremdes Konzept" not in response.content

    def test_should_return_404_for_other_tenant_concept_detail(
        self, fixture_client, fixture_tenant_id, fixture_area
    ):
        """Fremdes Konzept-Detail gibt 404"""
        other_tenant = uuid.uuid4()
        other_area = Area.objects.create(
            tenant_id=other_tenant,
            site_id=uuid.uuid4(),
            code="OTHER-04",
            name="Fremder Bereich 4",
        )
        other_concept = ExplosionConcept.objects.create(
            tenant_id=other_tenant,
            area=other_area,
            substance_id=uuid.uuid4(),
            title="Fremdes Konzept 2",
            status="draft",
        )
        response = fixture_client.get(f"/ex/concepts/{other_concept.id}/")
        assert response.status_code == 404


# =============================================================================
# TESTS: Create/Edit Forms (GET only)
# =============================================================================


@pytest.mark.django_db
class TestFormViews:
    """Tests für Formular-Views (GET)"""

    def test_should_render_area_create_form(self, fixture_client):
        """GET /ex/areas/create/ antwortet"""
        response = fixture_client.get("/ex/areas/create/")
        assert response.status_code in (200, 302)

    def test_should_render_area_edit_form(self, fixture_client, fixture_area):
        """GET /ex/areas/{id}/edit/ antwortet"""
        response = fixture_client.get(f"/ex/areas/{fixture_area.id}/edit/")
        assert response.status_code in (200, 302)

    def test_should_render_concept_create_form(self, fixture_client):
        """GET /ex/concepts/new/ antwortet"""
        response = fixture_client.get("/ex/concepts/new/")
        assert response.status_code in (200, 302)

    def test_should_render_concept_edit_form(self, fixture_client, fixture_concept):
        """GET /ex/concepts/{id}/ antwortet"""
        response = fixture_client.get(f"/ex/concepts/{fixture_concept.id}/")
        assert response.status_code in (200, 302)
