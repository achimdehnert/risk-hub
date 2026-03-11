# src/dsb/tests/test_services.py
"""
Unit-Tests für DSB Service Layer (get_dsb_kpis).

Tests nach ADR v5:
- KPI-Aggregation für leeren Tenant
- KPI-Aggregation mit Daten (Mandate, VVT, TOM, AVV, Breaches)
- Tenant-Isolierung: fremde Daten fließen nicht in KPIs ein
"""

import uuid
from datetime import date, timedelta

import pytest
from django.utils import timezone

from dsb.models import (
    Breach,
    DataProcessingAgreement,
    Mandate,
    MeasureStatus,
    OrganizationalMeasure,
    ProcessingActivity,
    TechnicalMeasure,
)
from dsb.services import DsbKPI, get_dsb_kpis

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_mandate(fixture_tenant_id):
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Test GmbH",
        dsb_appointed_date=date.today(),
        status="active",
    )


@pytest.fixture
def fixture_mandate_inactive(fixture_tenant_id):
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Inactive GmbH",
        dsb_appointed_date=date.today(),
        status="terminated",
    )


@pytest.fixture
def fixture_processing_activity(fixture_tenant_id, fixture_mandate):
    return ProcessingActivity.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        number=1,
        name="Kundenverwaltung",
        legal_basis="contract",
        risk_level="low",
    )


@pytest.fixture
def fixture_processing_activity_high_risk(fixture_tenant_id, fixture_mandate):
    return ProcessingActivity.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        number=2,
        name="Video-Überwachung",
        legal_basis="legitimate_interest",
        risk_level="high",
        dsfa_required=True,
    )


@pytest.fixture
def fixture_technical_measure_implemented(fixture_tenant_id, fixture_mandate):
    return TechnicalMeasure.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        title="Verschlüsselung",
        status=MeasureStatus.IMPLEMENTED,
    )


@pytest.fixture
def fixture_technical_measure_planned(fixture_tenant_id, fixture_mandate):
    return TechnicalMeasure.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        title="MFA",
        status=MeasureStatus.PLANNED,
    )


@pytest.fixture
def fixture_org_measure(fixture_tenant_id, fixture_mandate):
    return OrganizationalMeasure.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        title="Datenschutz-Schulung",
        status=MeasureStatus.IMPLEMENTED,
    )


@pytest.fixture
def fixture_dpa_active(fixture_tenant_id, fixture_mandate):
    return DataProcessingAgreement.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        partner_name="Cloud-Provider AG",
        subject_matter="Hosting-Dienste",
        status="active",
    )


@pytest.fixture
def fixture_dpa_expired(fixture_tenant_id, fixture_mandate):
    return DataProcessingAgreement.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        partner_name="Alter Dienstleister GmbH",
        subject_matter="Alte Dienste",
        status="expired",
    )


@pytest.fixture
def fixture_breach_open(fixture_tenant_id, fixture_mandate):
    return Breach.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        discovered_at=timezone.now() - timedelta(hours=10),
        severity="high",
        reported_to_authority_at=None,
    )


@pytest.fixture
def fixture_breach_reported(fixture_tenant_id, fixture_mandate):
    return Breach.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        discovered_at=timezone.now() - timedelta(days=5),
        severity="low",
        reported_to_authority_at=timezone.now() - timedelta(days=4),
    )


# =============================================================================
# TESTS: leerer Tenant
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisEmpty:
    """KPIs für Tenant ohne Daten — alles 0"""

    def test_should_return_zero_kpis_for_empty_tenant(self):
        kpi = get_dsb_kpis(uuid.uuid4())

        assert isinstance(kpi, DsbKPI)
        assert kpi.mandates_total == 0
        assert kpi.mandates_active == 0
        assert kpi.vvt_total == 0
        assert kpi.dpa_total == 0
        assert kpi.breaches_total == 0
        assert kpi.tom_tech_total == 0
        assert kpi.tom_org_total == 0

    def test_should_return_dsb_kpi_dataclass(self):
        kpi = get_dsb_kpis(uuid.uuid4())
        assert isinstance(kpi, DsbKPI)


# =============================================================================
# TESTS: Mandate KPIs
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisMandates:
    """Mandate-Zählung"""

    def test_should_count_active_mandates(
        self, fixture_tenant_id, fixture_mandate, fixture_mandate_inactive
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.mandates_total == 2
        assert kpi.mandates_active == 1

    def test_should_count_only_own_tenant_mandates(self, fixture_tenant_id, fixture_mandate):
        other_tenant = uuid.uuid4()
        Mandate.objects.create(
            tenant_id=other_tenant,
            name="Fremdes Unternehmen",
            dsb_appointed_date=date.today(),
            status="active",
        )
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.mandates_total == 1


# =============================================================================
# TESTS: VVT KPIs
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisVvt:
    """Verarbeitungsverzeichnis-KPIs"""

    def test_should_count_vvt_entries(
        self,
        fixture_tenant_id,
        fixture_processing_activity,
        fixture_processing_activity_high_risk,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.vvt_total == 2

    def test_should_count_high_risk_vvt(
        self,
        fixture_tenant_id,
        fixture_processing_activity,
        fixture_processing_activity_high_risk,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.vvt_high_risk == 1

    def test_should_count_dsfa_required(
        self,
        fixture_tenant_id,
        fixture_processing_activity,
        fixture_processing_activity_high_risk,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.vvt_dsfa_required == 1


# =============================================================================
# TESTS: TOM KPIs
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisTom:
    """TOM-KPIs (technische + organisatorische Maßnahmen)"""

    def test_should_count_technical_measures(
        self,
        fixture_tenant_id,
        fixture_technical_measure_implemented,
        fixture_technical_measure_planned,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.tom_tech_total == 2
        assert kpi.tom_tech_implemented == 1
        assert kpi.tom_tech_planned == 1

    def test_should_count_org_measures(
        self,
        fixture_tenant_id,
        fixture_org_measure,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.tom_org_total == 1
        assert kpi.tom_org_implemented == 1
        assert kpi.tom_org_planned == 0


# =============================================================================
# TESTS: AVV KPIs
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisDpa:
    """AVV-KPIs"""

    def test_should_count_dpa_by_status(
        self,
        fixture_tenant_id,
        fixture_dpa_active,
        fixture_dpa_expired,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.dpa_total == 2
        assert kpi.dpa_active == 1
        assert kpi.dpa_expired == 1


# =============================================================================
# TESTS: Breach KPIs
# =============================================================================


@pytest.mark.django_db
class TestDsbKpisBreaches:
    """Datenpannen-KPIs"""

    def test_should_count_breaches_total(
        self,
        fixture_tenant_id,
        fixture_breach_open,
        fixture_breach_reported,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.breaches_total == 2

    def test_should_count_open_breaches(
        self,
        fixture_tenant_id,
        fixture_breach_open,
        fixture_breach_reported,
    ):
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.breaches_open == 1

    def test_should_count_overdue_breaches(
        self,
        fixture_tenant_id,
        fixture_breach_open,
    ):
        """Breach < 72h alt ist noch nicht overdue"""
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.breaches_overdue == 0

    def test_should_detect_overdue_breach(self, fixture_tenant_id, fixture_mandate):
        """Breach > 72h ohne Meldung ist overdue"""
        Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now() - timedelta(hours=80),
            severity="critical",
            reported_to_authority_at=None,
        )
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.breaches_overdue == 1

    def test_should_not_count_other_tenant_breaches(self, fixture_tenant_id, fixture_breach_open):
        """Fremde Datenpannen fließen nicht in KPIs ein"""
        other_tenant = uuid.uuid4()
        other_mandate = Mandate.objects.create(
            tenant_id=other_tenant,
            name="Fremdes Unternehmen",
            dsb_appointed_date=date.today(),
            status="active",
        )
        Breach.objects.create(
            tenant_id=other_tenant,
            mandate=other_mandate,
            discovered_at=timezone.now(),
            severity="low",
        )
        kpi = get_dsb_kpis(fixture_tenant_id)
        assert kpi.breaches_total == 1
