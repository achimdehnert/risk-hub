# src/explosionsschutz/tests/test_views.py
"""
API Tests für Explosionsschutz Views

Tests nach ADR v5:
- Tenant-Isolierung bei API-Zugriffen
- CRUD-Operationen für alle Entities
- Berechtigungsprüfungen
"""

import uuid
from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from explosionsschutz.models import (
    ReferenceStandard,
    MeasureCatalog,
    EquipmentType,
    Area,
    ExplosionConcept,
    ZoneDefinition,
    Equipment,
)

User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fixture_tenant_id():
    """Tenant UUID für Tests"""
    return uuid.uuid4()


@pytest.fixture
def fixture_other_tenant_id():
    """Anderer Tenant für Isolationstests"""
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
def fixture_api_client(fixture_tenant_id, fixture_test_user):
    """API Client mit Tenant-Header und Authentifizierung"""
    client = APIClient()
    client.defaults["HTTP_X_TENANT_ID"] = str(fixture_tenant_id)
    client.force_authenticate(user=fixture_test_user)
    return client


@pytest.fixture
def fixture_system_standard():
    """Globaler System-Standard"""
    return ReferenceStandard.objects.create(
        tenant_id=None,
        code="ATEX 2014/34/EU",
        title="ATEX-Produktrichtlinie",
        category="directive",
        is_system=True,
    )


@pytest.fixture
def fixture_tenant_standard(fixture_tenant_id):
    """Tenant-spezifischer Standard"""
    return ReferenceStandard.objects.create(
        tenant_id=fixture_tenant_id,
        code="CUSTOM-001",
        title="Betriebsspezifische Anweisung",
        category="other",
        is_system=False,
    )


@pytest.fixture
def fixture_other_tenant_standard(fixture_other_tenant_id):
    """Standard eines anderen Tenants"""
    return ReferenceStandard.objects.create(
        tenant_id=fixture_other_tenant_id,
        code="OTHER-001",
        title="Fremder Standard",
        category="other",
        is_system=False,
    )


@pytest.fixture
def fixture_measure_catalog(fixture_tenant_id):
    """Maßnahmenkatalog-Eintrag"""
    return MeasureCatalog.objects.create(
        tenant_id=fixture_tenant_id,
        code="M-001",
        title="Erdung aller leitfähigen Teile",
        description_template="Potentialausgleich durchführen",
        default_type="secondary",
        is_system=False,
    )


@pytest.fixture
def fixture_equipment_type(fixture_tenant_id):
    """Betriebsmitteltyp"""
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="Pepperl+Fuchs",
        model="KFD2-SR2-Ex1.W",
        atex_group="II",
        atex_category="1",
        protection_type="ia",
        explosion_group="IIC",
        temperature_class="T6",
        epl="Ga",
        is_system=False,
    )


@pytest.fixture
def fixture_area(fixture_tenant_id):
    """Betriebsbereich"""
    return Area.objects.create(
        tenant_id=fixture_tenant_id,
        site_id=uuid.uuid4(),
        code="PROD-01",
        name="Produktionsbereich 1",
    )


@pytest.fixture
def fixture_explosion_concept(fixture_tenant_id, fixture_area):
    """Explosionsschutzkonzept"""
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=uuid.uuid4(),
        title="Ex-Konzept Test",
        version=1,
        status="draft",
    )


@pytest.fixture
def fixture_zone(fixture_tenant_id, fixture_explosion_concept):
    """Zonendefinition"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_explosion_concept,
        zone_type="1",
        name="Tankumgebung",
    )


# =============================================================================
# TESTS: REFERENCE STANDARDS API
# =============================================================================

@pytest.mark.django_db
class TestReferenceStandardsAPI:
    """Tests für /api/ex/reference-standards/"""

    def test_should_list_global_and_tenant_standards(
        self,
        fixture_api_client,
        fixture_system_standard,
        fixture_tenant_standard,
    ):
        """GET listet globale + tenant-spezifische Standards"""
        url = reverse("explosionsschutz:standard-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        codes = [s["code"] for s in response.data["results"]]
        assert fixture_system_standard.code in codes
        assert fixture_tenant_standard.code in codes

    def test_should_not_list_other_tenant_standards(
        self,
        fixture_api_client,
        fixture_other_tenant_standard,
    ):
        """GET zeigt NICHT Standards anderer Tenants"""
        url = reverse("explosionsschutz:standard-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        codes = [s["code"] for s in response.data["results"]]
        assert fixture_other_tenant_standard.code not in codes

    def test_should_retrieve_single_standard(
        self,
        fixture_api_client,
        fixture_tenant_standard,
    ):
        """GET /{id} gibt einzelnen Standard zurück"""
        url = reverse(
            "explosionsschutz:standard-detail",
            kwargs={"pk": fixture_tenant_standard.id}
        )
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == fixture_tenant_standard.code


# =============================================================================
# TESTS: EQUIPMENT TYPES API
# =============================================================================

@pytest.mark.django_db
class TestEquipmentTypesAPI:
    """Tests für /api/ex/equipment-types/"""

    def test_should_list_equipment_types(
        self,
        fixture_api_client,
        fixture_equipment_type,
    ):
        """GET listet Betriebsmitteltypen"""
        url = reverse("explosionsschutz:equipment-type-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_should_include_atex_marking(
        self,
        fixture_api_client,
        fixture_equipment_type,
    ):
        """Response enthält berechnete ATEX-Kennzeichnung"""
        url = reverse(
            "explosionsschutz:equipment-type-detail",
            kwargs={"pk": fixture_equipment_type.id}
        )
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "full_atex_marking" in response.data
        assert "allowed_zones" in response.data
        assert "0" in response.data["allowed_zones"]  # Cat 1 erlaubt Zone 0


# =============================================================================
# TESTS: AREAS API
# =============================================================================

@pytest.mark.django_db
class TestAreasAPI:
    """Tests für /api/ex/areas/"""

    def test_should_list_areas(
        self,
        fixture_api_client,
        fixture_area,
    ):
        """GET listet Bereiche"""
        url = reverse("explosionsschutz:area-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_should_create_area(self, fixture_api_client, fixture_tenant_id):
        """POST erstellt neuen Bereich"""
        url = reverse("explosionsschutz:area-list")
        data = {
            "site_id": str(uuid.uuid4()),
            "code": "NEW-01",
            "name": "Neuer Bereich",
            "has_explosion_hazard": True,
        }
        response = fixture_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["code"] == "NEW-01"


# =============================================================================
# TESTS: EXPLOSION CONCEPTS API
# =============================================================================

@pytest.mark.django_db
class TestExplosionConceptsAPI:
    """Tests für /api/ex/concepts/"""

    def test_should_list_concepts(
        self,
        fixture_api_client,
        fixture_explosion_concept,
    ):
        """GET listet Ex-Konzepte"""
        url = reverse("explosionsschutz:concept-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_should_retrieve_concept_with_zones(
        self,
        fixture_api_client,
        fixture_explosion_concept,
        fixture_zone,
    ):
        """GET /{id} gibt Konzept mit Zonen zurück"""
        url = reverse(
            "explosionsschutz:concept-detail",
            kwargs={"pk": fixture_explosion_concept.id}
        )
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "zones" in response.data
        assert len(response.data["zones"]) == 1

    def test_should_filter_by_status(
        self,
        fixture_api_client,
        fixture_explosion_concept,
    ):
        """GET ?status=draft filtert nach Status"""
        url = reverse("explosionsschutz:concept-list")
        response = fixture_api_client.get(url, {"status": "draft"})

        assert response.status_code == status.HTTP_200_OK
        for concept in response.data["results"]:
            assert concept["status"] == "draft"


# =============================================================================
# TESTS: ZONES API
# =============================================================================

@pytest.mark.django_db
class TestZonesAPI:
    """Tests für /api/ex/zones/"""

    def test_should_list_zones(
        self,
        fixture_api_client,
        fixture_zone,
    ):
        """GET listet Zonen"""
        url = reverse("explosionsschutz:zone-list")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_should_include_required_category(
        self,
        fixture_api_client,
        fixture_zone,
    ):
        """Response enthält erforderliche Equipment-Kategorie"""
        url = reverse(
            "explosionsschutz:zone-detail",
            kwargs={"pk": fixture_zone.id}
        )
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["required_equipment_category"] == "2"  # Zone 1 = Cat 2


# =============================================================================
# TESTS: EQUIPMENT API
# =============================================================================

@pytest.mark.django_db
class TestEquipmentAPI:
    """Tests für /api/ex/equipment/"""

    def test_should_create_equipment(
        self,
        fixture_api_client,
        fixture_area,
        fixture_zone,
        fixture_equipment_type,
    ):
        """POST erstellt neues Equipment"""
        url = reverse("explosionsschutz:equipment-list")
        data = {
            "area_id": str(fixture_area.id),
            "equipment_type_id": str(fixture_equipment_type.id),
            "zone_id": str(fixture_zone.id),
            "serial_number": "EQ-API-001",
        }
        response = fixture_api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["serial_number"] == "EQ-API-001"


# =============================================================================
# TESTS: DASHBOARD API
# =============================================================================

@pytest.mark.django_db
class TestDashboardAPI:
    """Tests für /api/ex/dashboard/"""

    def test_should_return_dashboard_stats(
        self,
        fixture_api_client,
        fixture_explosion_concept,
        fixture_zone,
    ):
        """GET /dashboard gibt Statistiken zurück"""
        url = reverse("explosionsschutz:dashboard")
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "concepts" in response.data
        assert "zones" in response.data
        assert "equipment" in response.data


# =============================================================================
# TESTS: TENANT ISOLATION
# =============================================================================

@pytest.mark.django_db
class TestTenantIsolation:
    """Tests für Tenant-Isolation bei API-Zugriffen"""

    def test_should_not_access_other_tenant_area(
        self,
        fixture_api_client,
        fixture_other_tenant_id,
    ):
        """Fremder Bereich ist nicht erreichbar"""
        other_area = Area.objects.create(
            tenant_id=fixture_other_tenant_id,
            site_id=uuid.uuid4(),
            code="OTHER-01",
            name="Fremder Bereich",
        )

        url = reverse("explosionsschutz:area-detail", kwargs={"pk": other_area.id})
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_should_not_access_other_tenant_concept(
        self,
        fixture_api_client,
        fixture_other_tenant_id,
    ):
        """Fremdes Konzept ist nicht erreichbar"""
        other_area = Area.objects.create(
            tenant_id=fixture_other_tenant_id,
            site_id=uuid.uuid4(),
            code="OTHER-02",
            name="Fremder Bereich 2",
        )
        other_concept = ExplosionConcept.objects.create(
            tenant_id=fixture_other_tenant_id,
            area=other_area,
            substance_id=uuid.uuid4(),
            title="Fremdes Konzept",
        )

        url = reverse(
            "explosionsschutz:concept-detail",
            kwargs={"pk": other_concept.id}
        )
        response = fixture_api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
