# substances/tests/test_models.py
"""Tests für Substances Models."""

import uuid
from datetime import date

import pytest
from django.core.exceptions import ValidationError

from substances.models import (
    Party,
    Substance,
    Identifier,
    SdsRevision,
    SiteInventoryItem,
    HazardStatementRef,
    PrecautionaryStatementRef,
    PictogramRef,
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
def manufacturer(tenant_id, user_id):
    """Test Hersteller."""
    return Party.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        name="BASF SE",
        party_type=Party.PartyType.MANUFACTURER,
        email="info@basf.com",
    )


@pytest.fixture
def substance(tenant_id, user_id, manufacturer):
    """Test Gefahrstoff."""
    return Substance.objects.create(
        tenant_id=tenant_id,
        created_by=user_id,
        name="Aceton",
        trade_name="Aceton technisch",
        manufacturer=manufacturer,
        storage_class=Substance.StorageClass.SC_3,
        flash_point_c=-17,
        ignition_temperature_c=465,
        lower_explosion_limit=2.5,
        upper_explosion_limit=13.0,
        temperature_class="T1",
        explosion_group="IIA",
    )


@pytest.fixture
def h_statement():
    """Test H-Satz."""
    return HazardStatementRef.objects.create(
        code="H225",
        text_de="Flüssigkeit und Dampf leicht entzündbar",
        category="physical",
    )


@pytest.fixture
def p_statement():
    """Test P-Satz."""
    return PrecautionaryStatementRef.objects.create(
        code="P210",
        text_de="Von Hitze, heißen Oberflächen, Funken, offenen Flammen "
                "sowie anderen Zündquellen fernhalten. Nicht rauchen",
        category="prevention",
    )


@pytest.fixture
def pictogram():
    """Test Piktogramm."""
    return PictogramRef.objects.create(
        code="GHS02",
        name_de="Flamme",
        name_en="Flame",
        description="Entzündbare Stoffe",
    )


@pytest.mark.django_db
class TestParty:
    """Tests für Party Model."""

    def test_create_manufacturer(self, tenant_id, user_id):
        """Test: Hersteller erstellen."""
        party = Party.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name="Test GmbH",
            party_type=Party.PartyType.MANUFACTURER,
        )
        assert party.id is not None
        assert party.name == "Test GmbH"
        assert party.party_type == Party.PartyType.MANUFACTURER

    def test_create_supplier(self, tenant_id, user_id):
        """Test: Lieferant erstellen."""
        party = Party.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name="Supplier AG",
            party_type=Party.PartyType.SUPPLIER,
        )
        assert party.party_type == Party.PartyType.SUPPLIER

    def test_str_representation(self, manufacturer):
        """Test: String-Darstellung."""
        assert "BASF SE" in str(manufacturer)
        assert "Hersteller" in str(manufacturer)


@pytest.mark.django_db
class TestSubstance:
    """Tests für Substance Model."""

    def test_create_substance(self, substance):
        """Test: Gefahrstoff erstellen."""
        assert substance.id is not None
        assert substance.name == "Aceton"
        assert substance.flash_point_c == -17
        assert substance.temperature_class == "T1"

    def test_cas_number_property(self, substance, tenant_id, user_id):
        """Test: CAS-Nummer Property."""
        Identifier.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            id_type=Identifier.IdType.CAS,
            id_value="67-64-1",
        )
        assert substance.cas_number == "67-64-1"

    def test_cas_number_none_when_missing(self, substance):
        """Test: CAS-Nummer None wenn nicht vorhanden."""
        assert substance.cas_number is None

    def test_current_sds_property(
        self, substance, tenant_id, user_id, h_statement
    ):
        """Test: Aktuelle SDS-Revision Property."""
        # Erste Revision (Draft)
        SdsRevision.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            revision_number=1,
            revision_date=date(2024, 1, 1),
            status=SdsRevision.Status.DRAFT,
        )

        # Zweite Revision (Approved)
        sds2 = SdsRevision.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            revision_number=2,
            revision_date=date(2024, 6, 1),
            status=SdsRevision.Status.APPROVED,
        )
        sds2.hazard_statements.add(h_statement)

        current = substance.current_sds
        assert current is not None
        assert current.revision_number == 2
        assert current.status == SdsRevision.Status.APPROVED

    def test_storage_class_choices(self, tenant_id, user_id, manufacturer):
        """Test: Lagerklassen-Auswahl."""
        substance = Substance.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name="Wasserstoffperoxid",
            manufacturer=manufacturer,
            storage_class=Substance.StorageClass.SC_5_1B,
        )
        assert substance.storage_class == "5.1B"


@pytest.mark.django_db
class TestIdentifier:
    """Tests für Identifier Model."""

    def test_create_cas_identifier(self, substance, tenant_id, user_id):
        """Test: CAS-Kennung erstellen."""
        identifier = Identifier.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            id_type=Identifier.IdType.CAS,
            id_value="67-64-1",
        )
        assert identifier.id_type == "cas"
        assert "CAS" in str(identifier)

    def test_create_ufi_identifier(self, substance, tenant_id, user_id):
        """Test: UFI-Code erstellen."""
        identifier = Identifier.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            id_type=Identifier.IdType.UFI,
            id_value="N2N0-S0FT-M00K-E9DQ",
        )
        assert identifier.id_type == "ufi"


@pytest.mark.django_db
class TestSdsRevision:
    """Tests für SdsRevision Model."""

    def test_create_sds_revision(
        self, substance, tenant_id, user_id, h_statement, pictogram
    ):
        """Test: SDS-Revision erstellen."""
        sds = SdsRevision.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            revision_number=1,
            revision_date=date(2024, 1, 15),
            status=SdsRevision.Status.DRAFT,
            signal_word=SdsRevision.SignalWord.DANGER,
        )
        sds.hazard_statements.add(h_statement)
        sds.pictograms.add(pictogram)

        assert sds.revision_number == 1
        assert sds.signal_word == SdsRevision.SignalWord.DANGER
        assert h_statement in sds.hazard_statements.all()
        assert pictogram in sds.pictograms.all()

    def test_str_representation(self, substance, tenant_id, user_id):
        """Test: String-Darstellung."""
        sds = SdsRevision.objects.create(
            tenant_id=tenant_id,
            created_by=user_id,
            substance=substance,
            revision_number=3,
            revision_date=date(2024, 1, 1),
        )
        assert "Aceton" in str(sds)
        assert "Rev. 3" in str(sds)


@pytest.mark.django_db
class TestReferenceData:
    """Tests für Referenzdaten."""

    def test_h_statement_str(self, h_statement):
        """Test: H-Satz String-Darstellung."""
        assert "H225" in str(h_statement)

    def test_p_statement_str(self, p_statement):
        """Test: P-Satz String-Darstellung."""
        assert "P210" in str(p_statement)

    def test_pictogram_str(self, pictogram):
        """Test: Piktogramm String-Darstellung."""
        assert "GHS02" in str(pictogram)
        assert "Flamme" in str(pictogram)
