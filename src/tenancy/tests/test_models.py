"""Tests for tenancy models — Organization, Membership, Site."""

import pytest

from tenancy.models import Membership, Organization, Site


@pytest.mark.django_db
class TestOrganization:
    """Organization model tests."""

    def test_should_create_with_defaults(self):
        org = Organization.objects.create(slug="acme", name="Acme Corp")
        assert org.status == Organization.Status.TRIAL
        assert org.plan_code == "free"
        assert org.tenant_id is not None
        assert org.is_readonly is False

    def test_should_have_unique_slug(self, fixture_tenant):
        with pytest.raises(Exception):
            Organization.objects.create(slug=fixture_tenant.slug, name="Dup")

    def test_should_have_unique_tenant_id(self, fixture_tenant):
        with pytest.raises(Exception):
            Organization.objects.create(
                slug="unique-slug",
                name="Dup Tenant",
                tenant_id=fixture_tenant.tenant_id,
            )

    def test_is_active_for_trial(self):
        org = Organization(status=Organization.Status.TRIAL)
        assert org.is_active is True

    def test_is_active_for_active(self):
        org = Organization(status=Organization.Status.ACTIVE)
        assert org.is_active is True

    def test_is_active_false_for_suspended(self):
        org = Organization(status=Organization.Status.SUSPENDED)
        assert org.is_active is False

    def test_is_active_false_for_deleted(self):
        org = Organization(status=Organization.Status.DELETED)
        assert org.is_active is False

    def test_str_returns_name(self):
        org = Organization(name="Foo GmbH")
        assert str(org) == "Foo GmbH"


@pytest.mark.django_db
class TestMembership:
    """Membership model tests."""

    def test_should_create_membership(self, fixture_tenant, fixture_user):
        ms = Membership.objects.filter(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        ).first()
        assert ms is not None
        assert ms.role == Membership.Role.MEMBER

    def test_should_enforce_unique_user_per_tenant(self, fixture_tenant, fixture_user):
        with pytest.raises(Exception):
            Membership.objects.create(
                tenant_id=fixture_tenant.tenant_id,
                organization=fixture_tenant,
                user=fixture_user,
                role=Membership.Role.ADMIN,
            )

    def test_str_includes_user_and_org(self, fixture_tenant, fixture_user):
        ms = Membership.objects.get(tenant_id=fixture_tenant.tenant_id, user=fixture_user)
        s = str(ms)
        assert fixture_user.username in s
        assert fixture_tenant.name in s

    def test_tenant_manager_filters_by_tenant(self, fixture_tenant, fixture_tenant_b):
        from tests.factories import UserFactory

        user_b = UserFactory()
        Membership.objects.create(
            tenant_id=fixture_tenant_b.tenant_id,
            organization=fixture_tenant_b,
            user=user_b,
            role=Membership.Role.MEMBER,
        )
        qs = Membership.objects.filter(tenant_id=fixture_tenant.tenant_id)
        assert all(m.tenant_id == fixture_tenant.tenant_id for m in qs)


@pytest.mark.django_db
class TestSite:
    """Site model tests."""

    def test_should_create_site(self, fixture_site):
        assert fixture_site.name == "Hauptwerk"
        assert fixture_site.tenant_id is not None

    def test_should_enforce_unique_name_per_tenant(self, fixture_tenant, fixture_site):
        with pytest.raises(Exception):
            Site.objects.create(
                tenant_id=fixture_tenant.tenant_id,
                organization=fixture_tenant,
                name="Hauptwerk",
            )

    def test_same_name_allowed_in_different_tenant(self, fixture_tenant_b):
        site = Site.objects.create(
            tenant_id=fixture_tenant_b.tenant_id,
            organization=fixture_tenant_b,
            name="Hauptwerk",
        )
        assert site.pk is not None

    def test_str_returns_name(self, fixture_site):
        assert str(fixture_site) == "Hauptwerk"
