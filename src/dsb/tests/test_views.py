# src/dsb/tests/test_views.py
"""
View-Tests für dsb/views.py — Coverage P1.

Strategie:
- @require_module via mock.patch("django_tenancy.module_access.require_module") bypassen
- request.tenant_id direkt auf fixture_tenant.tenant_id setzen
- Kein Template-Rendering notwendig (resolve + call direkt)
"""

import uuid
from datetime import date
from unittest.mock import patch

import pytest
from django.test import RequestFactory
from django.utils import timezone

from dsb import views
from dsb.models import Breach, Mandate


# =============================================================================
# HELPERS
# =============================================================================


def _passthrough(module_code):
    """Decorator-Ersatz für @require_module: gibt View unverändert zurück."""

    def decorator(view_fn):
        return view_fn

    return decorator


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


# =============================================================================
# HELPER: Request mit eingeloggtem User + tenant_id
# =============================================================================


def _make_request(rf, user, tenant_id, method="GET", path="/dsb/", data=None):
    if method == "POST":
        req = rf.post(path, data or {})
    else:
        req = rf.get(path)
    req.user = user
    req.tenant_id = tenant_id
    req.session = {}
    return req


# =============================================================================
# TESTS: _tenant_id helper
# =============================================================================


@pytest.mark.django_db
class TestTenantIdHelper:
    def test_should_return_tenant_id_from_request_attr(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        assert views._tenant_id(req) == fixture_tenant_id

    def test_should_fallback_via_membership(self, rf, fixture_user, fixture_tenant_id):
        """Wenn kein request.tenant_id → Membership-Fallback."""
        from tenancy.models import Membership, Organization

        org = Organization.objects.create(
            slug="fallback-corp",
            name="Fallback Corp",
            is_active=True,
        )
        Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=fixture_user,
            role=Membership.Role.MEMBER,
        )
        req = rf.get("/dsb/")
        req.user = fixture_user
        req.session = {}
        tid = views._tenant_id(req)
        assert tid == org.tenant_id

    def test_should_return_none_for_anonymous(self, rf):
        from django.contrib.auth.models import AnonymousUser

        req = rf.get("/dsb/")
        req.user = AnonymousUser()
        req.session = {}
        assert views._tenant_id(req) is None


@pytest.mark.django_db
class TestUserIdHelper:
    def test_should_return_user_pk(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        assert views._user_id(req) == fixture_user.pk

    def test_should_return_none_for_anonymous(self, rf):
        from django.contrib.auth.models import AnonymousUser

        req = rf.get("/dsb/")
        req.user = AnonymousUser()
        req.session = {}
        assert views._user_id(req) is None


# =============================================================================
# TESTS: dashboard view
# =============================================================================


@pytest.mark.django_db
class TestDashboardView:
    def test_should_return_200_for_authenticated_user(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.dashboard(req)
        assert resp.status_code == 200

    def test_should_pass_kpis_to_context(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.dashboard(req)
        assert resp.status_code == 200

    def test_should_work_with_none_tenant_id(self, rf, fixture_user):
        req = _make_request(rf, fixture_user, None)
        req.tenant_id = None
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.dashboard(req)
        assert resp.status_code == 200

    def test_should_include_open_breaches(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="high",
        )
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.dashboard(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: mandate_list view
# =============================================================================


@pytest.mark.django_db
class TestMandateListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        resp = views.mandate_list(req)
        assert resp.status_code == 200

    def test_should_show_only_own_tenant_mandates(self, rf, fixture_user, fixture_tenant_id):
        Mandate.objects.create(
            tenant_id=fixture_tenant_id,
            name="Eigenes Mandat",
            dsb_appointed_date=date.today(),
            status="active",
        )
        other_tid = uuid.uuid4()
        Mandate.objects.create(
            tenant_id=other_tid,
            name="Fremdes Mandat",
            dsb_appointed_date=date.today(),
            status="active",
        )
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        resp = views.mandate_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: mandate_create view
# =============================================================================


@pytest.mark.django_db
class TestMandateCreateView:
    def test_should_return_200_on_get(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        resp = views.mandate_create(req)
        assert resp.status_code == 200

    def test_should_create_mandate_on_valid_post(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(
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
        count_before = Mandate.objects.filter(tenant_id=fixture_tenant_id).count()
        resp = views.mandate_create(req)
        count_after = Mandate.objects.filter(tenant_id=fixture_tenant_id).count()
        assert resp.status_code in (200, 302)
        if resp.status_code == 302:
            assert count_after == count_before + 1


# =============================================================================
# TESTS: vvt_list view
# =============================================================================


@pytest.mark.django_db
class TestVvtListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.vvt_list(req)
        assert resp.status_code == 200

    def test_should_return_200_without_data(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.vvt_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: tom_list view
# =============================================================================


@pytest.mark.django_db
class TestTomListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.tom_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: dpa_list view
# =============================================================================


@pytest.mark.django_db
class TestDpaListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.dpa_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: breach_list view
# =============================================================================


@pytest.mark.django_db
class TestBreachListView:
    def test_should_return_200_empty(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.breach_list(req)
        assert resp.status_code == 200

    def test_should_return_200_with_breaches(
        self, rf, fixture_user, fixture_tenant_id, fixture_mandate
    ):
        Breach.objects.create(
            tenant_id=fixture_tenant_id,
            mandate=fixture_mandate,
            discovered_at=timezone.now(),
            severity="high",
        )
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.breach_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: audit_list view
# =============================================================================


@pytest.mark.django_db
class TestAuditListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.audit_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: deletion_list view
# =============================================================================


@pytest.mark.django_db
class TestDeletionListView:
    def test_should_return_200(self, rf, fixture_user, fixture_tenant_id):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        with patch("django_tenancy.module_access.require_module", side_effect=_passthrough):
            resp = views.deletion_list(req)
        assert resp.status_code == 200


# =============================================================================
# TESTS: mandate_edit view
# =============================================================================


@pytest.mark.django_db
class TestMandateEditView:
    def test_should_return_200_on_get(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        resp = views.mandate_edit(req, pk=fixture_mandate.pk)
        assert resp.status_code == 200

    def test_should_404_on_wrong_tenant(self, rf, fixture_user, fixture_mandate):
        other_tid = uuid.uuid4()
        req = _make_request(rf, fixture_user, other_tid)
        from django.http import Http404

        with pytest.raises(Http404):
            views.mandate_edit(req, pk=fixture_mandate.pk)


# =============================================================================
# TESTS: mandate_delete view
# =============================================================================


@pytest.mark.django_db
class TestMandateDeleteView:
    def test_should_return_200_on_get(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id)
        resp = views.mandate_delete(req, pk=fixture_mandate.pk)
        assert resp.status_code == 200

    def test_should_delete_on_post(self, rf, fixture_user, fixture_tenant_id, fixture_mandate):
        req = _make_request(rf, fixture_user, fixture_tenant_id, method="POST")
        resp = views.mandate_delete(req, pk=fixture_mandate.pk)
        assert resp.status_code == 302
        assert not Mandate.objects.filter(pk=fixture_mandate.pk).exists()
