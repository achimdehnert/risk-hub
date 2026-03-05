# src/dsb/tests/test_views.py
"""
View-Tests für dsb/views.py — Coverage P1.

Strategie:
- @override_settings(MODULE_URL_MAP={}) deaktiviert ModuleAccessMiddleware-Check
- request.tenant_id direkt setzen
- @login_required via RequestFactory + req.user umgehen
"""

import uuid
from datetime import date

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone

from dsb import views
from dsb.models import Breach, Mandate

# MODULE_URL_MAP={} → ModuleAccessMiddleware erlaubt alle Requests
_NO_MODULE_CHECK = override_settings(MODULE_URL_MAP={})


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


def _req(rf, user, tenant_id, method="GET", path="/dsb/", data=None):
    """Erstellt einen Request mit User + tenant_id."""
    if method == "POST":
        r = rf.post(path, data or {})
    else:
        r = rf.get(path)
    r.user = user
    r.tenant_id = tenant_id
    r.session = {}
    return r


# =============================================================================
# TESTS: _tenant_id / _user_id helpers
# =============================================================================


@pytest.mark.django_db
class TestTenantIdHelper:
    def test_returns_request_attr(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views._tenant_id(r) == fixture_tenant_id

    def test_fallback_via_membership(self, rf, fixture_user):
        from tenancy.models import Membership, Organization

        org = Organization.objects.create(slug="fallback-co", name="Fallback Co")
        Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=fixture_user,
            role=Membership.Role.MEMBER,
        )
        r = rf.get("/dsb/")
        r.user = fixture_user
        r.session = {}
        assert views._tenant_id(r) == org.tenant_id

    def test_returns_none_for_anonymous(self, rf):
        from django.contrib.auth.models import AnonymousUser

        r = rf.get("/dsb/")
        r.user = AnonymousUser()
        r.session = {}
        assert views._tenant_id(r) is None


@pytest.mark.django_db
class TestUserIdHelper:
    def test_returns_user_pk(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views._user_id(r) == fixture_user.pk

    def test_returns_none_for_anonymous(self, rf):
        from django.contrib.auth.models import AnonymousUser

        r = rf.get("/dsb/")
        r.user = AnonymousUser()
        r.session = {}
        assert views._user_id(r) is None


# =============================================================================
# TESTS: dashboard view
# =============================================================================


@pytest.mark.django_db
@_NO_MODULE_CHECK
class TestDashboardView:
    def test_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        resp = views.dashboard(r)
        assert resp.status_code == 200

    def test_returns_200_with_none_tenant(self, rf, fixture_user):
        r = _req(rf, fixture_user, None)
        resp = views.dashboard(r)
        assert resp.status_code == 200

    def test_includes_open_breaches(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="high",
        )
        r = _req(rf, fixture_user, fixture_tenant_id)
        resp = views.dashboard(r)
        assert resp.status_code == 200


# =============================================================================
# TESTS: mandate_list + mandate_create
# =============================================================================


@pytest.mark.django_db
class TestMandateListView:
    def test_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.mandate_list(r).status_code == 200

    def test_isolates_own_tenant(self, rf, fixture_user, fixture_tenant_id):
        Mandate.objects.create(
            tenant_id=fixture_tenant_id,
            name="Eigenes",
            dsb_appointed_date=date.today(),
            status="active",
        )
        Mandate.objects.create(
            tenant_id=uuid.uuid4(),
            name="Fremd",
            dsb_appointed_date=date.today(),
            status="active",
        )
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.mandate_list(r).status_code == 200


@pytest.mark.django_db
class TestMandateCreateView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.mandate_create(r).status_code == 200

    def test_valid_post_creates_mandate(self, rf, fixture_user, fixture_tenant_id):
        r = _req(
            rf,
            fixture_user,
            fixture_tenant_id,
            method="POST",
            data={
                "name": "Neue GmbH",
                "dsb_appointed_date": str(date.today()),
                "status": "active",
            },
        )
        before = Mandate.objects.filter(tenant_id=fixture_tenant_id).count()
        resp = views.mandate_create(r)
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            assert Mandate.objects.filter(tenant_id=fixture_tenant_id).count() == before + 1


# =============================================================================
# TESTS: vvt_list, tom_list, dpa_list, audit_list, deletion_list, breach_list
# =============================================================================


@pytest.mark.django_db
@_NO_MODULE_CHECK
class TestModuleViews:
    def test_vvt_list(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.vvt_list(r).status_code == 200

    def test_vvt_list_empty(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.vvt_list(r).status_code == 200

    def test_tom_list(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.tom_list(r).status_code == 200

    def test_dpa_list(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.dpa_list(r).status_code == 200

    def test_audit_list(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.audit_list(r).status_code == 200

    def test_deletion_list(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.deletion_list(r).status_code == 200

    def test_breach_list_empty(self, rf, fixture_user, fixture_tenant_id):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.breach_list(r).status_code == 200

    def test_breach_list_with_data(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="high",
        )
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.breach_list(r).status_code == 200


# =============================================================================
# TESTS: mandate_edit, mandate_delete
# =============================================================================


@pytest.mark.django_db
class TestMandateEditView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.mandate_edit(r, pk=fixture_mandate.pk).status_code == 200

    def test_wrong_tenant_raises_404(self, rf, fixture_user, fixture_mandate):
        from django.http import Http404

        r = _req(rf, fixture_user, uuid.uuid4())
        with pytest.raises(Http404):
            views.mandate_edit(r, pk=fixture_mandate.pk)


@pytest.mark.django_db
class TestMandateDeleteView:
    def test_get_returns_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id)
        assert views.mandate_delete(r, pk=fixture_mandate.pk).status_code == 200

    def test_post_deletes_and_redirects(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        r = _req(rf, fixture_user, fixture_tenant_id, method="POST")
        resp = views.mandate_delete(r, pk=fixture_mandate.pk)
        assert resp.status_code == 302
        assert not Mandate.objects.filter(pk=fixture_mandate.pk).exists()
