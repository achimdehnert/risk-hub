"""Tests für Brandschutz views — RequestFactory pattern (ADR-058).

Bypasses full middleware stack (avoids RecursionError in template rendering).
"""
from __future__ import annotations

import uuid

import pytest
from django.test import RequestFactory

from brandschutz.views import (
    ConceptListView,
    EscapeRouteListView,
    ExtinguisherListView,
)

TENANT_ID = uuid.uuid4()


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def fixture_user(db):
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def fixture_org(db):
    from tenancy.models import Organization

    return Organization.objects.create(
        slug="brandschutz-test",
        name="Brandschutz Test GmbH",
        status=Organization.Status.ACTIVE,
    )


@pytest.fixture
def concept(db, fixture_org):
    from brandschutz.models import FireProtectionConcept
    from tenancy.models import Site

    site = Site.objects.create(
        tenant_id=fixture_org.tenant_id,
        organization=fixture_org,
        name="Hauptwerk",
    )
    return FireProtectionConcept.objects.create(
        tenant_id=fixture_org.tenant_id,
        site=site,
        title="Testkonzept",
        valid_from="2024-01-01",
    )


def _req(rf, user, tenant_id=None):
    r = rf.get("/")
    r.user = user
    r.tenant_id = tenant_id
    r.tenant = None
    return r


# ── ConceptListView ────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestConceptListView:
    def test_should_return_403_without_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, tenant_id=None)
        resp = ConceptListView.as_view()(req)
        assert resp.status_code == 403

    def test_should_return_200_with_tenant(self, rf, fixture_user, fixture_org):
        req = _req(rf, fixture_user, tenant_id=fixture_org.tenant_id)
        resp = ConceptListView.as_view()(req)
        assert resp.status_code == 200

    def test_should_show_concepts(self, rf, fixture_user, concept, fixture_org):
        req = _req(rf, fixture_user, tenant_id=fixture_org.tenant_id)
        resp = ConceptListView.as_view()(req)
        assert resp.status_code == 200
        assert b"Testkonzept" in resp.content

    def test_should_not_show_other_tenants_concepts(self, rf, fixture_user, concept):
        """Tenant isolation: concept from tenant A not visible in tenant B."""
        other_tenant = uuid.uuid4()
        req = _req(rf, fixture_user, tenant_id=other_tenant)
        resp = ConceptListView.as_view()(req)
        assert resp.status_code == 200
        assert b"Testkonzept" not in resp.content


# ── ExtinguisherListView ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestExtinguisherListView:
    def test_should_return_403_without_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, tenant_id=None)
        resp = ExtinguisherListView.as_view()(req)
        assert resp.status_code == 403

    def test_should_return_200_with_tenant(self, rf, fixture_user, fixture_org):
        req = _req(rf, fixture_user, tenant_id=fixture_org.tenant_id)
        resp = ExtinguisherListView.as_view()(req)
        assert resp.status_code == 200

    def test_should_support_status_filter(self, rf, fixture_user, fixture_org):
        r = rf.get("/?status=ok")
        r.user = fixture_user
        r.tenant_id = fixture_org.tenant_id
        r.tenant = None
        resp = ExtinguisherListView.as_view()(r)
        assert resp.status_code == 200


# ── EscapeRouteListView ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestEscapeRouteListView:
    def test_should_return_403_without_tenant(self, rf, fixture_user):
        req = _req(rf, fixture_user, tenant_id=None)
        resp = EscapeRouteListView.as_view()(req)
        assert resp.status_code == 403

    def test_should_return_200_with_tenant(self, rf, fixture_user, fixture_org):
        req = _req(rf, fixture_user, tenant_id=fixture_org.tenant_id)
        resp = EscapeRouteListView.as_view()(req)
        assert resp.status_code == 200

    def test_should_support_status_filter(self, rf, fixture_user, fixture_org):
        r = rf.get("/?status=ok")
        r.user = fixture_user
        r.tenant_id = fixture_org.tenant_id
        r.tenant = None
        resp = EscapeRouteListView.as_view()(r)
        assert resp.status_code == 200
