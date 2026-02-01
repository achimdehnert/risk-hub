# substances/tests/test_services.py
"""Tests für Substances Services."""

import uuid
from datetime import date

import pytest

from substances.models import (
    Substance,
    Identifier,
    SdsRevision,
    HazardStatementRef,
)
from substances.services.substance_service import SubstanceService
from substances.services.ex_integration import (
    ExIntegrationService,
    ExSubstanceData,
)


@pytest.fixture
def tenant_id():
    """Test Tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Test User ID."""
    return uuid.uuid4()


@pytest.fixture
def aceton(tenant_id, user_id):
    """Test Aceton Gefahrstoff mit vollständigen Ex-Daten."""
    substance = Substance.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        name="Aceton",
        trade_name="Aceton technisch",
        flash_point_c=-17,
        ignition_temperature_c=465,
        lower_explosion_limit=2.5,
        upper_explosion_limit=13.0,
        temperature_class="T1",
        explosion_group="IIA",
        vapor_density=2.0,
    )

    # CAS-Nummer hinzufügen
    Identifier.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        substance=substance,
        id_type="cas",
        id_value="67-64-1",
    )

    # SDS mit H-Sätzen
    h225 = HazardStatementRef.objects.create(
        code="H225",
        text_de="Flüssigkeit und Dampf leicht entzündbar",
        category="physical",
    )

    sds = SdsRevision.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        substance=substance,
        revision_number=1,
        revision_date=date(2024, 1, 1),
        status=SdsRevision.Status.APPROVED,
    )
    sds.hazard_statements.add(h225)

    return substance


@pytest.mark.django_db
class TestSubstanceService:
    """Tests für SubstanceService."""

    def test_get_by_id(self, aceton, tenant_id):
        """Test: Gefahrstoff nach ID holen."""
        result = SubstanceService.get_by_id(aceton.id, tenant_id)
        assert result is not None
        assert result.name == "Aceton"

    def test_get_by_id_wrong_tenant(self, aceton):
        """Test: Gefahrstoff mit falschem Tenant nicht finden."""
        wrong_tenant = uuid.uuid4()
        result = SubstanceService.get_by_id(aceton.id, wrong_tenant)
        assert result is None

    def test_get_by_cas(self, aceton, tenant_id):
        """Test: Gefahrstoff nach CAS-Nummer holen."""
        result = SubstanceService.get_by_cas("67-64-1", tenant_id)
        assert result is not None
        assert result.name == "Aceton"

    def test_get_by_cas_not_found(self, tenant_id):
        """Test: CAS-Nummer nicht gefunden."""
        result = SubstanceService.get_by_cas("999-99-9", tenant_id)
        assert result is None

    def test_search(self, aceton, tenant_id):
        """Test: Suche nach Gefahrstoffen."""
        results = SubstanceService.search("Acet", tenant_id)
        assert len(results) >= 1
        assert any(s.name == "Aceton" for s in results)

    def test_search_by_trade_name(self, aceton, tenant_id):
        """Test: Suche nach Handelsname."""
        results = SubstanceService.search("technisch", tenant_id)
        assert len(results) >= 1

    def test_get_ex_relevant_data(self, aceton):
        """Test: Ex-relevante Daten extrahieren."""
        data = SubstanceService.get_ex_relevant_data(aceton)

        assert data["substance_name"] == "Aceton"
        assert data["cas_number"] == "67-64-1"
        assert data["flash_point_c"] == -17
        assert data["ignition_temperature_c"] == 465
        assert data["temperature_class"] == "T1"
        assert data["explosion_group"] == "IIA"
        assert data["sds_revision"] == 1
        assert "H225" in data["h_statements"]


@pytest.mark.django_db
class TestExIntegrationService:
    """Tests für ExIntegrationService."""

    def test_get_ex_data(self, aceton, tenant_id):
        """Test: Ex-Daten holen."""
        ex_data = ExIntegrationService.get_ex_data(aceton.id, tenant_id)

        assert ex_data is not None
        assert isinstance(ex_data, ExSubstanceData)
        assert ex_data.substance_name == "Aceton"
        assert ex_data.flash_point_c == -17
        assert ex_data.temperature_class == "T1"

    def test_get_ex_data_by_cas(self, aceton, tenant_id):
        """Test: Ex-Daten nach CAS-Nummer."""
        ex_data = ExIntegrationService.get_ex_data_by_cas("67-64-1", tenant_id)

        assert ex_data is not None
        assert ex_data.substance_name == "Aceton"

    def test_is_flammable(self, aceton, tenant_id):
        """Test: Entzündbarkeits-Check."""
        ex_data = ExIntegrationService.get_ex_data(aceton.id, tenant_id)
        assert ex_data.is_flammable() is True

    def test_get_required_equipment_category(self, aceton, tenant_id):
        """Test: Erforderliche Gerätekategorie."""
        ex_data = ExIntegrationService.get_ex_data(aceton.id, tenant_id)

        assert ex_data.get_required_equipment_category("0") == "1"
        assert ex_data.get_required_equipment_category("1") == "2"
        assert ex_data.get_required_equipment_category("2") == "3"
        assert ex_data.get_required_equipment_category("20") == "1"

    def test_get_required_temperature_class(self, aceton, tenant_id):
        """Test: Erforderliche Temperaturklasse."""
        ex_data = ExIntegrationService.get_ex_data(aceton.id, tenant_id)

        # Aceton hat Zündtemperatur 465°C -> T1
        assert ex_data.get_required_temperature_class() == "T1"

    def test_validate_equipment_valid(self, aceton, tenant_id):
        """Test: Gültige Geräte-Validierung."""
        result = ExIntegrationService.validate_equipment_for_substance(
            substance_id=aceton.id,
            tenant_id=tenant_id,
            equipment_marking="II 2G Ex db IIB T4 Gb",
            zone_type="1",
        )

        assert result["valid"] is True
        assert result["substance_name"] == "Aceton"

    def test_validate_equipment_invalid_category(self, aceton, tenant_id):
        """Test: Ungültige Gerätekategorie."""
        result = ExIntegrationService.validate_equipment_for_substance(
            substance_id=aceton.id,
            tenant_id=tenant_id,
            equipment_marking="II 3G Ex nA IIA T3 Gc",  # Kat. 3 für Zone 1
            zone_type="1",  # Zone 1 braucht Kat. 2
        )

        assert result["valid"] is False
        assert len(result["issues"]) > 0


@pytest.mark.django_db
class TestExSubstanceData:
    """Tests für ExSubstanceData Dataclass."""

    def test_temperature_class_t1(self):
        """Test: Temperaturklasse T1 (>450°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=500,
        )
        assert data.get_required_temperature_class() == "T1"

    def test_temperature_class_t2(self):
        """Test: Temperaturklasse T2 (300-450°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=350,
        )
        assert data.get_required_temperature_class() == "T2"

    def test_temperature_class_t3(self):
        """Test: Temperaturklasse T3 (200-300°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=250,
        )
        assert data.get_required_temperature_class() == "T3"

    def test_temperature_class_t4(self):
        """Test: Temperaturklasse T4 (135-200°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=180,
        )
        assert data.get_required_temperature_class() == "T4"

    def test_temperature_class_t5(self):
        """Test: Temperaturklasse T5 (100-135°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=120,
        )
        assert data.get_required_temperature_class() == "T5"

    def test_temperature_class_t6(self):
        """Test: Temperaturklasse T6 (<100°C)."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            ignition_temperature_c=85,
        )
        assert data.get_required_temperature_class() == "T6"

    def test_is_flammable_by_flash_point(self):
        """Test: Entzündbar durch Flammpunkt."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            flash_point_c=40,
        )
        assert data.is_flammable() is True

    def test_is_flammable_by_lel(self):
        """Test: Entzündbar durch UEG."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Test",
            lower_explosion_limit=1.5,
        )
        assert data.is_flammable() is True

    def test_not_flammable(self):
        """Test: Nicht entzündbar."""
        data = ExSubstanceData(
            substance_id=uuid.uuid4(),
            substance_name="Wasser",
            flash_point_c=None,
            lower_explosion_limit=None,
        )
        assert data.is_flammable() is False
