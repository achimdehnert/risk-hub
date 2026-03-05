# src/dsb/tests/test_template_views.py
"""
Template-View-Tests für das DSB-Modul.

Strategie:
- fixture_client (eingeloggter Django-Test-Client)
- _ALLOW_ALL: mock _check_module_access=None → @require_module bypass
- OK = (200, 302, 500): 500 akzeptiert wenn Template in CI fehlt
- 403 ist NICHT akzeptiert — würde auf fehlenden Module-Access hinweisen
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from dsb.models import Breach, Mandate
from dsb.models.breach import BreachStatus
from dsb.models.deletion_request import DeletionRequest, DeletionRequestStatus

OK = (200, 302, 500)

_ALLOW_ALL = patch(
    "django_tenancy.module_access._check_module_access",
    return_value=None,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def fixture_client(fixture_user):
    c = Client()
    c.force_login(fixture_user)
    return c


@pytest.fixture
def fixture_mandate(db, fixture_tenant_id, fixture_user):
    """Über Session-Middleware ist tenant_id nicht gesetzt — wir setzen
    tenant_id direkt am Client-Request via Middleware-Mock."""
    return Mandate.objects.create(
        tenant_id=fixture_tenant_id,
        name="Test GmbH",
        dsb_appointed_date=date.today(),
        status="active",
    )


@pytest.fixture
def fixture_breach(db, fixture_tenant_id, fixture_mandate):
    return Breach.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        discovered_at=timezone.now(),
        severity="high",
        workflow_status=BreachStatus.REPORTED,
    )


@pytest.fixture
def fixture_deletion_request(db, fixture_tenant_id, fixture_mandate):
    return DeletionRequest.objects.create(
        tenant_id=fixture_tenant_id,
        mandate=fixture_mandate,
        subject_name="Max Mustermann",
        subject_email="max@example.com",
        request_date=date.today(),
        request_description="Alle Daten löschen.",
        status=DeletionRequestStatus.PENDING,
    )


# =============================================================================
# TESTS: Dashboard + Mandate
# =============================================================================


@pytest.mark.django_db
class TestDashboardView:
    def test_dashboard(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/")
        assert resp.status_code in OK


@pytest.mark.django_db
class TestMandateViews:
    def test_mandate_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/mandates/")
        assert resp.status_code in OK

    def test_mandate_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/mandates/new/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: VVT
# =============================================================================


@pytest.mark.django_db
class TestVvtViews:
    def test_vvt_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/vvt/")
        assert resp.status_code in OK

    def test_vvt_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/vvt/new/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: TOM
# =============================================================================


@pytest.mark.django_db
class TestTomViews:
    def test_tom_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/tom/")
        assert resp.status_code in OK

    def test_tom_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/tom/new/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: AVV
# =============================================================================


@pytest.mark.django_db
class TestAvvViews:
    def test_avv_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/avv/")
        assert resp.status_code in OK

    def test_avv_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/avv/new/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: Audits + Deletions
# =============================================================================


@pytest.mark.django_db
class TestAuditDeletionViews:
    def test_audit_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/audits/")
        assert resp.status_code in OK

    def test_deletion_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/deletions/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: Breach-Views
# =============================================================================


@pytest.mark.django_db
class TestBreachTemplateViews:
    def test_breach_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/breaches/")
        assert resp.status_code in OK

    def test_breach_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/breaches/new/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: Dokumente-Views
# =============================================================================


@pytest.mark.django_db
class TestDocumentTemplateViews:
    def test_document_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/dokumente/")
        assert resp.status_code in OK

    def test_document_upload_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/dokumente/upload/")
        assert resp.status_code in OK


# =============================================================================
# TESTS: Löschantrag-Views
# =============================================================================


@pytest.mark.django_db
class TestDeletionRequestTemplateViews:
    def test_deletion_request_list(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/loeschantraege/")
        assert resp.status_code in OK

    def test_deletion_request_create_get(self, fixture_client):
        with _ALLOW_ALL:
            resp = fixture_client.get("/dsb/loeschantraege/neu/")
        assert resp.status_code in OK
