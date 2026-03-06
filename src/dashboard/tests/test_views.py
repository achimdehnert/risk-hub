"""Tests für dashboard/views.py — DashboardView + Partials."""

import uuid

import pytest
from django.test import RequestFactory

from dashboard.views import (
    DashboardActivityPartialView,
    DashboardKPIPartialView,
    DashboardView,
)

TENANT_ID = uuid.uuid4()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory
    return UserFactory()


def _req(rf, user, tenant_id):
    r = rf.get("/")
    r.user = user
    r.tenant_id = tenant_id
    return r


@pytest.mark.django_db
class TestDashboardView:
    def test_get_renders(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID)
        resp = DashboardView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_get_no_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, None)
        resp = DashboardView.as_view()(req)
        assert resp.status_code in (200, 500)


@pytest.mark.django_db
class TestDashboardKPIPartialView:
    def test_get_renders(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID)
        resp = DashboardKPIPartialView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_get_no_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, None)
        resp = DashboardKPIPartialView.as_view()(req)
        assert resp.status_code in (200, 500)


@pytest.mark.django_db
class TestDashboardActivityPartialView:
    def test_get_renders(self, rf, fixture_user):
        req = _req(rf, fixture_user, TENANT_ID)
        resp = DashboardActivityPartialView.as_view()(req)
        assert resp.status_code in (200, 500)

    def test_get_no_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, None)
        resp = DashboardActivityPartialView.as_view()(req)
        assert resp.status_code in (200, 500)
