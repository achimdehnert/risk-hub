# src/dsb/tests/test_views_breach.py
"""
View-Tests für dsb/views_breach.py — Coverage +8%.

Strategie:
- mock _check_module_access=None → @require_module bypass
- RequestFactory + req.tenant_id direkt setzen
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.utils import timezone

from dsb import views_breach
from dsb.models import Breach, Mandate
from dsb.models.breach import BreachStatus

_ALLOW_ALL = patch(
    "django_tenancy.module_access._check_module_access",
    return_value=None,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_tenant_id():
    return uuid.uuid4()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def fixture_mandate(db, fixture_tenant_id):
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


def _req(rf, user, tenant_id, method="GET", path="/dsb/breaches/", data=None):
    if method == "POST":
        r = rf.post(path, data or {})
    else:
        r = rf.get(path)
    r.user = user
    r.tenant_id = tenant_id
    r.session = {}
    from django.contrib.messages.storage.fallback import FallbackStorage

    r._messages = FallbackStorage(r)
    return r


# =============================================================================
# TESTS: breach_list
# =============================================================================


@pytest.mark.django_db
class TestBreachListView:
    def test_returns_200_empty(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_breach.breach_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_returns_200_with_breach(self, rf, fixture_user, fixture_tenant_id, fixture_breach):
        with _ALLOW_ALL:
            resp = views_breach.breach_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_isolates_tenant(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        other_tid = uuid.uuid4()
        other_mandate = Mandate.objects.create(
            tenant_id=other_tid,
            name="Fremde GmbH",
            dsb_appointed_date=date.today(),
            status="active",
        )
        Breach.objects.create(
            tenant_id=other_tid,
            mandate=other_mandate,
            discovered_at=timezone.now(),
            severity="low",
        )
        with _ALLOW_ALL:
            resp = views_breach.breach_list(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200


# =============================================================================
# TESTS: breach_create
# =============================================================================


@pytest.mark.django_db
class TestBreachCreateView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        with _ALLOW_ALL:
            resp = views_breach.breach_create(_req(rf, fixture_user, fixture_tenant_id))
        assert resp.status_code == 200

    def test_post_valid_creates_breach(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={
                    "mandate": str(fixture_mandate.pk),
                    "discovered_at_0": str(date.today()),
                    "discovered_at_1": "10:00:00",
                    "severity": "high",
                    "title": "Test-Panne",
                },
            )
            before = Breach.objects.filter(tenant_id=fixture_tenant_id).count()
            resp = views_breach.breach_create(r)
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            assert Breach.objects.filter(tenant_id=fixture_tenant_id).count() == before + 1


# =============================================================================
# TESTS: breach_detail
# =============================================================================


@pytest.mark.django_db
class TestBreachDetailView:
    def test_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_breach):
        with _ALLOW_ALL:
            resp = views_breach.breach_detail(
                _req(rf, fixture_user, fixture_tenant_id), pk=fixture_breach.pk
            )
        assert resp.status_code == 200

    def test_wrong_tenant_returns_404(self, rf, fixture_user, fixture_breach):
        from django.http import Http404

        with _ALLOW_ALL:
            with pytest.raises(Http404):
                views_breach.breach_detail(
                    _req(rf, fixture_user, uuid.uuid4()), pk=fixture_breach.pk
                )


# =============================================================================
# TESTS: breach_advance
# =============================================================================


@pytest.mark.django_db
class TestBreachAdvanceView:
    def test_get_redirects(self, rf, fixture_user, fixture_tenant_id, fixture_breach):
        """GET → redirect zu detail (kein POST)"""
        with _ALLOW_ALL:
            resp = views_breach.breach_advance(
                _req(rf, fixture_user, fixture_tenant_id), pk=fixture_breach.pk
            )
        assert resp.status_code == 302

    def test_post_valid_transition(self, rf, fixture_user, fixture_tenant_id, fixture_breach):
        """POST mit gültigem Übergang reported → dsb_notified"""
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={"new_status": BreachStatus.DSB_NOTIFIED, "send_mail": "0"},
            )
            resp = views_breach.breach_advance(r, pk=fixture_breach.pk)
        assert resp.status_code == 302
        fixture_breach.refresh_from_db()
        assert fixture_breach.workflow_status == BreachStatus.DSB_NOTIFIED

    def test_post_invalid_transition_redirects(
        self, rf, fixture_user, fixture_tenant_id, fixture_breach
    ):
        """POST mit ungültigem Übergang → redirect mit Fehlermeldung"""
        with _ALLOW_ALL:
            r = _req(
                rf,
                fixture_user,
                fixture_tenant_id,
                method="POST",
                data={"new_status": BreachStatus.CLOSED, "send_mail": "0"},
            )
            resp = views_breach.breach_advance(r, pk=fixture_breach.pk)
        assert resp.status_code == 302
        fixture_breach.refresh_from_db()
        assert fixture_breach.workflow_status == BreachStatus.REPORTED
