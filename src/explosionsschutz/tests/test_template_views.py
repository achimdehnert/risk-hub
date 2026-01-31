# src/explosionsschutz/tests/test_template_views.py
"""
Tests für HTML-Template Views

Tests nach ADR v5:
- Template-Rendering
- Tenant-Isolierung bei HTML-Views
- Korrekte Kontextdaten
"""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from explosionsschutz.models import (
    Area,
    ExplosionConcept,
    ZoneDefinition,
    Equipment,
    EquipmentType,
)

User = get_user_model()


@pytest.fixture
def fixture_tenant_id():
    """Tenant UUID für Tests"""
    return uuid.uuid4()


@pytest.fixture
def fixture_test_user():
    """Test-User für Authentifizierung"""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def fixture_client(fixture_tenant_id, fixture_test_user):
    """Test Client mit Tenant-Header und Login"""
    client = Client()
    client.defaults["HTTP_X_TENANT_ID"] = str(fixture_tenant_id)
    client.force_login(fixture_test_user)
    return client


@pytest.fixture
def fixture_area(fixture_tenant_id):
    """Testbereich"""
    return Area.objects.create(
        tenant_id=fixture_tenant_id,
        site_id=uuid.uuid4(),
        code="TEST-01",
        name="Testbereich",
    )


@pytest.fixture
def fixture_equipment_type(fixture_tenant_id):
    """Test-Betriebsmitteltyp"""
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="Test GmbH",
        model="Test-Sensor",
        atex_group="II",
        atex_category="2",
        protection_type="d",
        explosion_group="IIB",
        temperature_class="T4",
        is_system=False,
    )


@pytest.fixture
def fixture_concept(fixture_tenant_id, fixture_area):
    """Test Ex-Konzept"""
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
    """Test-Zone"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_concept,
        zone_type="1",
        name="Test-Zone",
    )


@pytest.fixture
def fixture_equipment(fixture_tenant_id, fixture_area, fixture_equipment_type):
    """Test-Equipment"""
    return Equipment.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        equipment_type=fixture_equipment_type,
        serial_number="EQ-TEST-001",
        status="active",
    )


@pytest.mark.django_db
class TestHomeView:
    """Tests für Homepage"""

    def test_should_render_homepage(self, fixture_client):
        """GET /ex/ rendert Homepage"""
        response = fixture_client.get("/ex/")
        assert response.status_code == 200
        assert b"Explosionsschutz" in response.content

    def test_should_show_stats(self, fixture_client, fixture_area):
        """Homepage zeigt Statistiken"""
        response = fixture_client.get("/ex/")
        assert response.status_code == 200


@pytest.mark.django_db
class TestAreaViews:
    """Tests für Bereich-Views"""

    def test_should_list_areas(self, fixture_client, fixture_area):
        """GET /ex/areas/ listet Bereiche"""
        response = fixture_client.get("/ex/areas/")
        assert response.status_code == 200
        assert b"Testbereich" in response.content

    def test_should_show_area_detail(self, fixture_client, fixture_area):
        """GET /ex/areas/{id}/ zeigt Bereichdetails"""
        response = fixture_client.get(f"/ex/areas/{fixture_area.id}/")
        assert response.status_code == 200
        assert b"TEST-01" in response.content

    def test_should_filter_by_search(self, fixture_client, fixture_area):
        """GET /ex/areas/?search=test filtert"""
        response = fixture_client.get("/ex/areas/?search=test")
        assert response.status_code == 200
        assert b"Testbereich" in response.content

    def test_should_filter_by_hazard(self, fixture_client, fixture_area):
        """GET /ex/areas/?hazard=1 filtert nach Ex-Gefährdung"""
        response = fixture_client.get("/ex/areas/?hazard=1")
        assert response.status_code == 200
        assert b"Testbereich" in response.content


@pytest.mark.django_db
class TestConceptViews:
    """Tests für Konzept-Views"""

    def test_should_list_concepts(self, fixture_client, fixture_concept):
        """GET /ex/concepts/ listet Konzepte"""
        response = fixture_client.get("/ex/concepts/")
        assert response.status_code == 200
        assert b"Test-Konzept" in response.content

    def test_should_show_concept_detail(
        self, fixture_client, fixture_concept, fixture_zone
    ):
        """GET /ex/concepts/{id}/ zeigt Konzeptdetails mit Zonen"""
        response = fixture_client.get(f"/ex/concepts/{fixture_concept.id}/")
        assert response.status_code == 200
        assert b"Test-Konzept" in response.content
        assert b"Test-Zone" in response.content

    def test_should_filter_by_status(self, fixture_client, fixture_concept):
        """GET /ex/concepts/?status=draft filtert nach Status"""
        response = fixture_client.get("/ex/concepts/?status=draft")
        assert response.status_code == 200
        assert b"Test-Konzept" in response.content


@pytest.mark.django_db
class TestEquipmentViews:
    """Tests für Equipment-Views"""

    def test_should_list_equipment(self, fixture_client, fixture_equipment):
        """GET /ex/equipment/ listet Betriebsmittel"""
        response = fixture_client.get("/ex/equipment/")
        assert response.status_code == 200
        assert b"EQ-TEST-001" in response.content

    def test_should_show_equipment_detail(self, fixture_client, fixture_equipment):
        """GET /ex/equipment/{id}/ zeigt Equipment-Details"""
        response = fixture_client.get(f"/ex/equipment/{fixture_equipment.id}/")
        assert response.status_code == 200
        assert b"Test GmbH" in response.content
        assert b"Test-Sensor" in response.content


@pytest.mark.django_db
class TestTenantIsolation:
    """Tests für Tenant-Isolierung bei HTML-Views"""

    def test_should_not_show_other_tenant_area(
        self, fixture_client, fixture_tenant_id
    ):
        """Fremder Bereich wird nicht angezeigt"""
        other_tenant = uuid.uuid4()
        other_area = Area.objects.create(
            tenant_id=other_tenant,
            site_id=uuid.uuid4(),
            code="OTHER-01",
            name="Fremder Bereich",
        )

        response = fixture_client.get("/ex/areas/")
        assert response.status_code == 200
        assert b"Fremder Bereich" not in response.content

    def test_should_return_404_for_other_tenant_detail(
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
