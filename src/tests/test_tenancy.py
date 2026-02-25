"""Tests for tenancy models (Organization, Site, Membership)."""

from __future__ import annotations

import pytest

from tenancy.models import Membership, Organization, Site


@pytest.mark.django_db
class TestOrganization:
    """Test Organization model and lifecycle."""

    def test_should_create_with_trial_status(self):
        org = Organization.objects.create(
            slug="new-corp", name="New Corp",
        )
        assert org.status == Organization.Status.TRIAL
        assert org.plan_code == "free"
        assert org.is_active is True

    def test_should_be_active_when_trial(self, fixture_tenant):
        fixture_tenant.status = Organization.Status.TRIAL
        assert fixture_tenant.is_active is True

    def test_should_be_active_when_active(self, fixture_tenant):
        assert fixture_tenant.is_active is True

    def test_should_not_be_active_when_suspended(self, fixture_tenant):
        fixture_tenant.status = Organization.Status.SUSPENDED
        assert fixture_tenant.is_active is False

    def test_should_not_be_active_when_deleted(self, fixture_tenant):
        fixture_tenant.status = Organization.Status.DELETED
        assert fixture_tenant.is_active is False

    def test_should_have_unique_slug(self, fixture_tenant):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Organization.objects.create(
                slug=fixture_tenant.slug, name="Dup",
            )

    def test_should_have_unique_tenant_id(self, fixture_tenant):
        assert fixture_tenant.tenant_id is not None


@pytest.mark.django_db
class TestSite:
    """Test Site model."""

    def test_should_create_site(self, fixture_site):
        assert fixture_site.name == "Hauptwerk"
        assert fixture_site.tenant_id is not None

    def test_should_enforce_unique_name_per_tenant(
        self, fixture_tenant, fixture_site,
    ):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Site.objects.create(
                tenant_id=fixture_tenant.tenant_id,
                organization=fixture_tenant,
                name="Hauptwerk",
            )

    def test_should_allow_same_name_different_tenant(
        self, fixture_tenant_b, fixture_site,
    ):
        site_b = Site.objects.create(
            tenant_id=fixture_tenant_b.tenant_id,
            organization=fixture_tenant_b,
            name="Hauptwerk",
        )
        assert site_b.id != fixture_site.id


@pytest.mark.django_db
class TestMembership:
    """Test Membership model."""

    def test_should_create_membership(self, fixture_user, fixture_tenant):
        m = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id,
            user=fixture_user,
        )
        assert m.role == Membership.Role.MEMBER

    def test_should_enforce_unique_user_per_tenant(
        self, fixture_user, fixture_tenant,
    ):
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Membership.objects.create(
                tenant_id=fixture_tenant.tenant_id,
                organization=fixture_tenant,
                user=fixture_user,
                role=Membership.Role.VIEWER,
            )

    def test_should_allow_user_in_multiple_tenants(
        self, fixture_user, fixture_tenant_b,
    ):
        m = Membership.objects.create(
            tenant_id=fixture_tenant_b.tenant_id,
            organization=fixture_tenant_b,
            user=fixture_user,
            role=Membership.Role.EXTERNAL,
        )
        assert m.role == Membership.Role.EXTERNAL
