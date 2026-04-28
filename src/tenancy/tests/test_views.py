"""Tests for tenancy.views — staff-only access, CRUD, member management."""

import pytest
from django.test import Client

from tenancy.models import Membership, Organization


@pytest.fixture
def staff_client(db):
    """Authenticated staff user client."""
    from tests.factories import UserFactory

    user = UserFactory(is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def regular_client(db):
    """Authenticated non-staff user client."""
    from tests.factories import UserFactory

    user = UserFactory(is_staff=False)
    client = Client()
    client.force_login(user)
    client._user = user
    return client


@pytest.fixture
def org(db):
    """A test organization."""
    return Organization.objects.create(
        slug="view-test-org",
        name="View Test Org",
        status=Organization.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestOrgListView:
    """org_list access control."""

    def test_should_allow_staff(self, staff_client):
        resp = staff_client.get("/tenants/")
        assert resp.status_code == 200

    def test_should_deny_non_staff(self, regular_client):
        resp = regular_client.get("/tenants/")
        assert resp.status_code == 403

    def test_should_redirect_anonymous(self):
        client = Client()
        resp = client.get("/tenants/")
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url


@pytest.mark.django_db
class TestOrgCreateView:
    """org_create tests."""

    def test_should_render_form_for_staff(self, staff_client):
        resp = staff_client.get("/tenants/new/")
        assert resp.status_code == 200

    def test_should_deny_non_staff(self, regular_client):
        resp = regular_client.get("/tenants/new/")
        assert resp.status_code == 403

    def test_should_create_org_on_post(self, staff_client):
        resp = staff_client.post(
            "/tenants/new/",
            {"slug": "new-org", "name": "New Org", "status": "active", "plan_code": "free"},
        )
        assert resp.status_code == 302
        assert Organization.objects.filter(slug="new-org").exists()


@pytest.mark.django_db
class TestOrgDetailView:
    """org_detail tests."""

    def test_should_show_detail_for_staff(self, staff_client, org):
        resp = staff_client.get(f"/tenants/{org.pk}/")
        assert resp.status_code == 200

    def test_should_deny_non_staff(self, regular_client, org):
        resp = regular_client.get(f"/tenants/{org.pk}/")
        assert resp.status_code == 403

    def test_should_404_for_missing_org(self, staff_client):
        import uuid

        resp = staff_client.get(f"/tenants/{uuid.uuid4()}/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestOrgEditView:
    """org_edit tests."""

    def test_should_render_form(self, staff_client, org):
        resp = staff_client.get(f"/tenants/{org.pk}/edit/")
        assert resp.status_code == 200

    def test_should_update_org(self, staff_client, org):
        resp = staff_client.post(
            f"/tenants/{org.pk}/edit/",
            {"slug": org.slug, "name": "Updated Name", "status": "active", "plan_code": "free"},
        )
        assert resp.status_code == 302
        org.refresh_from_db()
        assert org.name == "Updated Name"


@pytest.mark.django_db
class TestOrgDeleteView:
    """org_delete tests — soft delete."""

    def test_should_confirm_before_delete(self, staff_client, org):
        resp = staff_client.get(f"/tenants/{org.pk}/delete/")
        assert resp.status_code == 200

    def test_should_soft_delete_on_post(self, staff_client, org):
        resp = staff_client.post(f"/tenants/{org.pk}/delete/")
        assert resp.status_code == 302
        org.refresh_from_db()
        assert org.status == Organization.Status.DELETED
        assert org.deleted_at is not None


@pytest.mark.django_db
class TestMemberInviteView:
    """member_invite tests."""

    def test_should_deny_non_staff(self, regular_client, org):
        resp = regular_client.get(f"/tenants/{org.pk}/members/invite/")
        assert resp.status_code == 403

    def test_should_render_form(self, staff_client, org):
        resp = staff_client.get(f"/tenants/{org.pk}/members/invite/")
        assert resp.status_code == 200

    def test_should_create_user_and_membership(self, staff_client, org):
        resp = staff_client.post(
            f"/tenants/{org.pk}/members/invite/",
            {
                "username": "invited_user",
                "email": "invited@example.com",
                "password": "SecurePass123!",
                "role": Membership.Role.MEMBER,
            },
        )
        assert resp.status_code == 302
        assert Membership.objects.filter(
            tenant_id=org.tenant_id,
            user__username="invited_user",
        ).exists()


@pytest.mark.django_db
class TestMemberRemoveView:
    """member_remove tests."""

    def test_should_remove_member_on_post(self, staff_client, org):
        from tests.factories import UserFactory

        user = UserFactory()
        ms = Membership.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            user=user,
            role=Membership.Role.MEMBER,
        )
        resp = staff_client.post(f"/tenants/{org.pk}/members/{ms.pk}/remove/")
        assert resp.status_code == 302
        assert not Membership.objects.filter(pk=ms.pk).exists()


@pytest.fixture
def tenant_org(db):
    """An active organization for site tests."""
    return Organization.objects.create(
        slug="site-test-org",
        name="Site Test Org",
        status=Organization.Status.ACTIVE,
    )


@pytest.fixture
def tenant_client(db, tenant_org):
    """Client logged in as a user whose tenant_id matches tenant_org."""
    from tests.factories import UserFactory

    user = UserFactory(tenant_id=tenant_org.tenant_id)
    client = Client()
    client.force_login(user)
    return client, tenant_org


@pytest.mark.django_db
class TestSiteListView:
    """site_list tests."""

    def test_should_deny_without_tenant_id(self):
        from tests.factories import UserFactory

        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.get("/tenants/sites/")
        assert resp.status_code == 403

    def test_should_redirect_anonymous(self):
        resp = Client().get("/tenants/sites/")
        assert resp.status_code == 302

    def test_should_render_for_tenant(self, tenant_client):
        client, org = tenant_client
        resp = client.get("/tenants/sites/")
        assert resp.status_code == 200
        assert b"Standorte" in resp.content

    def test_should_show_existing_sites(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        Site.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            name="Hauptwerk",
            site_type="plant",
        )
        resp = client.get("/tenants/sites/")
        assert resp.status_code == 200
        assert b"Hauptwerk" in resp.content


@pytest.mark.django_db
class TestSiteCreateView:
    """site_create tests."""

    def test_should_deny_without_tenant_id(self):
        from tests.factories import UserFactory

        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.get("/tenants/sites/new/")
        assert resp.status_code == 403

    def test_should_render_form_for_tenant(self, tenant_client):
        client, _org = tenant_client
        resp = client.get("/tenants/sites/new/")
        assert resp.status_code == 200
        assert b"Standorttyp" in resp.content

    def test_should_create_site_on_post(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        resp = client.post(
            "/tenants/sites/new/",
            {
                "name": "Neues Werk",
                "code": "NW-1",
                "site_type": "plant",
                "address": "Musterstraße 1, 20095 Hamburg",
                "is_active": True,
            },
        )
        assert resp.status_code == 302
        assert Site.objects.filter(tenant_id=org.tenant_id, name="Neues Werk").exists()


@pytest.mark.django_db
class TestSiteEditView:
    """site_edit tests."""

    def test_should_deny_without_tenant_id(self):
        from tenancy.models import Organization, Site

        org2 = Organization.objects.create(slug="other-edit-org", name="Other")
        site = Site.objects.create(
            tenant_id=org2.tenant_id, organization=org2, name="Test Site"
        )
        from tests.factories import UserFactory

        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.get(f"/tenants/sites/{site.pk}/edit/")
        assert resp.status_code == 403

    def test_should_render_edit_form(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        site = Site.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            name="Edit Werk",
            site_type="plant",
        )
        resp = client.get(f"/tenants/sites/{site.pk}/edit/")
        assert resp.status_code == 200
        assert b"Edit Werk" in resp.content

    def test_should_return_404_for_other_tenant_site(self, tenant_client):
        from tenancy.models import Organization, Site

        client, _org = tenant_client
        other_org = Organization.objects.create(slug="other-tenant-org", name="Other Org")
        other_site = Site.objects.create(
            tenant_id=other_org.tenant_id,
            organization=other_org,
            name="Other Tenant Site",
        )
        resp = client.get(f"/tenants/sites/{other_site.pk}/edit/")
        assert resp.status_code == 404

    def test_should_update_site_on_post(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        site = Site.objects.create(
            tenant_id=org.tenant_id,
            organization=org,
            name="Old Name",
            site_type="plant",
        )
        resp = client.post(
            f"/tenants/sites/{site.pk}/edit/",
            {"name": "New Name", "code": "", "site_type": "office", "address": "", "is_active": True},
        )
        assert resp.status_code == 302
        site.refresh_from_db()
        assert site.name == "New Name"
        assert site.site_type == "office"


@pytest.mark.django_db
class TestSiteDeleteView:
    """site_delete tests."""

    def test_should_deny_without_tenant_id(self):
        from tenancy.models import Organization, Site

        org2 = Organization.objects.create(slug="other-del-org", name="Other")
        site = Site.objects.create(
            tenant_id=org2.tenant_id, organization=org2, name="Del Site"
        )
        from tests.factories import UserFactory

        user = UserFactory()
        client = Client()
        client.force_login(user)
        resp = client.post(f"/tenants/sites/{site.pk}/delete/")
        assert resp.status_code == 403

    def test_should_show_confirm_page(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        site = Site.objects.create(
            tenant_id=org.tenant_id, organization=org, name="Del Site"
        )
        resp = client.get(f"/tenants/sites/{site.pk}/delete/")
        assert resp.status_code == 200
        assert b"Del Site" in resp.content

    def test_should_delete_site_on_post(self, tenant_client):
        from tenancy.models import Site

        client, org = tenant_client
        site = Site.objects.create(
            tenant_id=org.tenant_id, organization=org, name="Del Site"
        )
        resp = client.post(f"/tenants/sites/{site.pk}/delete/")
        assert resp.status_code == 302
        assert not Site.objects.filter(pk=site.pk).exists()

    def test_should_return_404_for_other_tenant_site(self, tenant_client):
        from tenancy.models import Organization, Site

        client, _org = tenant_client
        other_org = Organization.objects.create(slug="del-other-org", name="Other Org")
        other_site = Site.objects.create(
            tenant_id=other_org.tenant_id,
            organization=other_org,
            name="Other Tenant Del",
        )
        resp = client.post(f"/tenants/sites/{other_site.pk}/delete/")
        assert resp.status_code == 404
