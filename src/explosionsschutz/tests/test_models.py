# src/explosionsschutz/tests/test_models.py
"""
Unit Tests für Explosionsschutz Models

Tests nach ADR v5:
- Hybrid-Isolation für Stammdaten
- ATEX-Kategorien und Zonenzuordnung
- Zündquellenbewertung
- Prüffristen-Berechnung
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from explosionsschutz.models import (
    ReferenceStandard,
    MeasureCatalog,
    SafetyFunction,
    EquipmentType,
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    Inspection,
    VerificationDocument,
    ZoneIgnitionSourceAssessment,
    IgnitionSource,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def fixture_tenant_id():
    """Tenant UUID für Tests"""
    return uuid.uuid4()


@pytest.fixture
def fixture_reference_standard(fixture_tenant_id):
    """Regelwerksreferenz für Tests"""
    return ReferenceStandard.objects.create(
        tenant_id=fixture_tenant_id,
        code="EN 60079-10-1",
        title="Klassifizierung von Bereichen - Gasexplosionsgefährdete Bereiche",
        category="norm",
        is_system=False,
    )


@pytest.fixture
def fixture_system_standard():
    """System-Regelwerk (global)"""
    return ReferenceStandard.objects.create(
        tenant_id=None,
        code="ATEX 2014/34/EU",
        title="ATEX-Produktrichtlinie",
        category="directive",
        is_system=True,
    )


@pytest.fixture
def fixture_equipment_type_cat1(fixture_tenant_id):
    """Kategorie 1 Betriebsmittel (Zone 0/20)"""
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
        ip_rating="IP20",
        is_system=False,
    )


@pytest.fixture
def fixture_equipment_type_cat2(fixture_tenant_id):
    """Kategorie 2 Betriebsmittel (Zone 1/21)"""
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="R. STAHL",
        model="IS1+",
        atex_group="II",
        atex_category="2",
        protection_type="d",
        explosion_group="IIB",
        temperature_class="T4",
        epl="Gb",
        ip_rating="IP66",
        default_inspection_interval_months=36,
        is_system=False,
    )


@pytest.fixture
def fixture_equipment_type_cat3(fixture_tenant_id):
    """Kategorie 3 Betriebsmittel (Zone 2/22)"""
    return EquipmentType.objects.create(
        tenant_id=fixture_tenant_id,
        manufacturer="Siemens",
        model="SIRIUS 3RT",
        atex_group="II",
        atex_category="3",
        protection_type="nA",
        explosion_group="IIA",
        temperature_class="T3",
        epl="Gc",
        ip_rating="IP54",
        default_inspection_interval_months=72,
        is_system=False,
    )


@pytest.fixture
def fixture_area(fixture_tenant_id):
    """Betriebsbereich für Tests"""
    return Area.objects.create(
        tenant_id=fixture_tenant_id,
        site_id=uuid.uuid4(),
        code="PROD-01",
        name="Produktionsbereich 1",
    )


@pytest.fixture
def fixture_substance_id():
    """Substanz UUID (externer FK)"""
    return uuid.uuid4()


@pytest.fixture
def fixture_explosion_concept(fixture_tenant_id, fixture_area, fixture_substance_id):
    """Ex-Konzept für Tests"""
    return ExplosionConcept.objects.create(
        tenant_id=fixture_tenant_id,
        area=fixture_area,
        substance_id=fixture_substance_id,
        title="Ex-Konzept Produktionsbereich 1",
        version=1,
        status="draft",
    )


@pytest.fixture
def fixture_zone_0(fixture_tenant_id, fixture_explosion_concept):
    """Zone 0 für Tests"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_explosion_concept,
        zone_type="0",
        name="Tankinneres",
        justification="Ständig explosionsfähige Atmosphäre im Tankinneren",
    )


@pytest.fixture
def fixture_zone_1(fixture_tenant_id, fixture_explosion_concept):
    """Zone 1 für Tests"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_explosion_concept,
        zone_type="1",
        name="Tankumgebung 1m",
        extent_horizontal_m=Decimal("1.0"),
        extent_vertical_m=Decimal("0.5"),
    )


@pytest.fixture
def fixture_zone_2(fixture_tenant_id, fixture_explosion_concept):
    """Zone 2 für Tests"""
    return ZoneDefinition.objects.create(
        tenant_id=fixture_tenant_id,
        concept=fixture_explosion_concept,
        zone_type="2",
        name="Hallenbereich",
        extent_horizontal_m=Decimal("5.0"),
    )


# =============================================================================
# TESTS: STAMMDATEN HYBRID-ISOLATION
# =============================================================================

@pytest.mark.django_db
class TestTenantScopedMasterData:
    """Tests für Hybrid-Isolation bei Stammdaten"""

    def test_should_create_tenant_specific_standard(self, fixture_tenant_id):
        """Tenant-spezifische Standards werden mit tenant_id erstellt"""
        standard = ReferenceStandard.objects.create(
            tenant_id=fixture_tenant_id,
            code="CUSTOM-001",
            title="Betriebsspezifische Anweisung",
            category="other",
            is_system=False,
        )
        assert standard.tenant_id == fixture_tenant_id
        assert standard.is_system is False

    def test_should_create_global_system_standard(self):
        """System-Standards haben tenant_id=None"""
        standard = ReferenceStandard.objects.create(
            tenant_id=None,
            code="IEC 60079-0",
            title="Explosive atmospheres - General requirements",
            category="norm",
            is_system=True,
        )
        assert standard.tenant_id is None
        assert standard.is_system is True

    def test_should_query_tenant_and_global_standards(
        self, fixture_tenant_id, fixture_reference_standard, fixture_system_standard
    ):
        """for_tenant() liefert globale + tenant-spezifische Daten"""
        qs = ReferenceStandard.objects.for_tenant(fixture_tenant_id)
        codes = list(qs.values_list("code", flat=True))

        assert fixture_reference_standard.code in codes
        assert fixture_system_standard.code in codes

    def test_should_not_query_other_tenant_standards(
        self, fixture_tenant_id, fixture_reference_standard
    ):
        """for_tenant() liefert NICHT Daten anderer Tenants"""
        other_tenant = uuid.uuid4()
        other_standard = ReferenceStandard.objects.create(
            tenant_id=other_tenant,
            code="OTHER-001",
            title="Anderer Tenant",
            category="other",
        )

        qs = ReferenceStandard.objects.for_tenant(fixture_tenant_id)
        codes = list(qs.values_list("code", flat=True))

        assert other_standard.code not in codes


# =============================================================================
# TESTS: ATEX-KENNZEICHNUNG UND ZONENZUORDNUNG
# =============================================================================

@pytest.mark.django_db
class TestEquipmentTypeAtexMarking:
    """Tests für ATEX-Kennzeichnung"""

    def test_should_generate_full_atex_marking(self, fixture_equipment_type_cat1):
        """full_atex_marking kombiniert alle ATEX-Felder"""
        marking = fixture_equipment_type_cat1.full_atex_marking
        assert "II" in marking
        assert "1" in marking
        assert "ia" in marking
        assert "IIC" in marking
        assert "T6" in marking

    def test_should_return_allowed_zones_for_cat1(self, fixture_equipment_type_cat1):
        """Kategorie 1 erlaubt Zonen 0, 1, 2"""
        allowed = fixture_equipment_type_cat1.allowed_zones
        assert "0" in allowed
        assert "1" in allowed
        assert "2" in allowed
        assert "non_ex" in allowed

    def test_should_return_allowed_zones_for_cat2(self, fixture_equipment_type_cat2):
        """Kategorie 2 erlaubt Zonen 1, 2 (nicht 0)"""
        allowed = fixture_equipment_type_cat2.allowed_zones
        assert "0" not in allowed
        assert "1" in allowed
        assert "2" in allowed

    def test_should_return_allowed_zones_for_cat3(self, fixture_equipment_type_cat3):
        """Kategorie 3 erlaubt nur Zone 2"""
        allowed = fixture_equipment_type_cat3.allowed_zones
        assert "0" not in allowed
        assert "1" not in allowed
        assert "2" in allowed


# =============================================================================
# TESTS: ZONENDEFINITION
# =============================================================================

@pytest.mark.django_db
class TestZoneDefinition:
    """Tests für Zonendefinitionen"""

    def test_should_return_required_category_for_zone_0(self, fixture_zone_0):
        """Zone 0 erfordert Kategorie 1"""
        assert fixture_zone_0.required_equipment_category == "1"

    def test_should_return_required_category_for_zone_1(self, fixture_zone_1):
        """Zone 1 erfordert Kategorie 2"""
        assert fixture_zone_1.required_equipment_category == "2"

    def test_should_return_required_category_for_zone_2(self, fixture_zone_2):
        """Zone 2 erfordert Kategorie 3"""
        assert fixture_zone_2.required_equipment_category == "3"


# =============================================================================
# TESTS: EQUIPMENT-ZONEN-KOMPATIBILITÄT
# =============================================================================

@pytest.mark.django_db
class TestEquipmentZoneCompatibility:
    """Tests für Equipment-Zonen-Zuordnung"""

    def test_should_allow_cat1_in_zone_0(
        self, fixture_tenant_id, fixture_area, fixture_zone_0, fixture_equipment_type_cat1
    ):
        """Kategorie 1 Equipment darf in Zone 0"""
        equipment = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            equipment_type=fixture_equipment_type_cat1,
            zone=fixture_zone_0,
            serial_number="CAT1-001",
        )
        assert equipment.zone.zone_type == "0"

    def test_should_allow_cat1_in_zone_2(
        self, fixture_tenant_id, fixture_area, fixture_zone_2, fixture_equipment_type_cat1
    ):
        """Kategorie 1 Equipment darf auch in Zone 2"""
        equipment = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            equipment_type=fixture_equipment_type_cat1,
            zone=fixture_zone_2,
            serial_number="CAT1-002",
        )
        assert equipment.zone.zone_type == "2"


# =============================================================================
# TESTS: PRÜFFRISTEN
# =============================================================================

@pytest.mark.django_db
class TestInspectionSchedule:
    """Tests für Prüffristen-Berechnung"""

    def test_should_calculate_next_inspection_date(
        self, fixture_tenant_id, fixture_area, fixture_zone_2, fixture_equipment_type_cat3
    ):
        """next_inspection_date wird basierend auf Intervall berechnet"""
        equipment = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            equipment_type=fixture_equipment_type_cat3,
            zone=fixture_zone_2,
            serial_number="INSP-001",
            installation_date=date.today() - timedelta(days=365),
            last_inspection_date=date.today() - timedelta(days=365),
            inspection_interval_months=12,
        )

        expected = date.today() - timedelta(days=365) + timedelta(days=365)
        assert equipment.next_inspection_date == expected

    def test_should_flag_overdue_inspection(
        self, fixture_tenant_id, fixture_area, fixture_zone_2, fixture_equipment_type_cat3
    ):
        """is_inspection_due ist True wenn überfällig"""
        equipment = Equipment.objects.create(
            tenant_id=fixture_tenant_id,
            area=fixture_area,
            equipment_type=fixture_equipment_type_cat3,
            zone=fixture_zone_2,
            serial_number="INSP-002",
            last_inspection_date=date.today() - timedelta(days=400),
            next_inspection_date=date.today() - timedelta(days=35),
        )

        assert equipment.is_inspection_due is True


# =============================================================================
# TESTS: ZÜNDQUELLENBEWERTUNG
# =============================================================================

@pytest.mark.django_db
class TestIgnitionSourceAssessment:
    """Tests für Zündquellenbewertung nach EN 1127-1"""

    def test_should_create_ignition_assessment(
        self, fixture_tenant_id, fixture_zone_1
    ):
        """Zündquellenbewertung kann erstellt werden"""
        assessment = ZoneIgnitionSourceAssessment.objects.create(
            tenant_id=fixture_tenant_id,
            zone=fixture_zone_1,
            ignition_source=IgnitionSource.S1_HOT_SURFACES,
            is_present=True,
            is_effective=False,
            mitigation="Oberflächentemperatur < Zündtemperatur",
        )

        assert assessment.is_present is True
        assert assessment.is_effective is False

    def test_should_enforce_unique_source_per_zone(
        self, fixture_tenant_id, fixture_zone_1
    ):
        """Eine Zündquelle kann nur einmal pro Zone bewertet werden"""
        ZoneIgnitionSourceAssessment.objects.create(
            tenant_id=fixture_tenant_id,
            zone=fixture_zone_1,
            ignition_source=IgnitionSource.S4_ELECTRICAL,
            is_present=True,
            is_effective=True,
        )

        with pytest.raises(IntegrityError):
            ZoneIgnitionSourceAssessment.objects.create(
                tenant_id=fixture_tenant_id,
                zone=fixture_zone_1,
                ignition_source=IgnitionSource.S4_ELECTRICAL,
                is_present=False,
                is_effective=False,
            )


# =============================================================================
# TESTS: KONZEPT-VOLLSTÄNDIGKEIT
# =============================================================================

@pytest.mark.django_db
class TestConceptCompletion:
    """Tests für Vollständigkeitsberechnung"""

    def test_should_calculate_completion_percentage(
        self, fixture_explosion_concept, fixture_zone_1
    ):
        """completion_percentage berechnet Fortschritt"""
        pct = fixture_explosion_concept.completion_percentage
        assert isinstance(pct, int)
        assert 0 <= pct <= 100
