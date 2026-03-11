# src/tests/conftest.py — ADR-058 §Confirmation
import uuid

import pytest

try:
    from platform_context.testing.fixtures import (  # noqa: F401
        admin_client,
        htmx_client,
    )
except ImportError:
    import django.test

    @pytest.fixture
    def admin_client(db):
        from tests.factories import UserFactory

        user = UserFactory(is_staff=True, is_superuser=True)
        client = django.test.Client()
        client.force_login(user)
        return client

    @pytest.fixture
    def htmx_client(client):
        class _HtmxClient:
            def __init__(self, c):
                self._c = c

            def get(self, url, **kw):
                return self._c.get(url, HTTP_HX_REQUEST="true", **kw)

            def post(self, url, **kw):
                return self._c.post(url, HTTP_HX_REQUEST="true", **kw)

        return _HtmxClient(client)

# ─── Basic fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def tenant_id():
    """A fixed tenant UUID for multi-tenant tests."""
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def user(db):
    """Standard authenticated user."""
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Admin user with superuser rights."""
    from tests.factories import UserFactory

    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def auth_client(client, user):
    """Pre-authenticated Django test client."""
    client.force_login(user)
    return client


# ─── Tenancy fixtures ─────────────────────────────────────────────


@pytest.fixture
def fixture_user(db):
    """A user for tenancy/authz tests."""
    from tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def fixture_tenant(db, fixture_user):
    """An active organization with the fixture_user as member."""
    from tenancy.models import Membership, Organization

    org = Organization.objects.create(
        slug="test-corp",
        name="Test Corp",
    )
    Membership.objects.create(
        tenant_id=org.tenant_id,
        organization=org,
        user=fixture_user,
        role=Membership.Role.MEMBER,
    )
    return org


@pytest.fixture
def fixture_tenant_b(db):
    """A second organization (no shared users)."""
    from tenancy.models import Organization

    return Organization.objects.create(
        slug="other-corp",
        name="Other Corp",
    )


@pytest.fixture
def fixture_site(db, fixture_tenant):
    """A site belonging to fixture_tenant."""
    from tenancy.models import Site

    return Site.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        organization=fixture_tenant,
        name="Hauptwerk",
    )


# ─── Module Access fixtures ───────────────────────────────────────────────


@pytest.fixture
def fixture_module_subscription(db, fixture_tenant):
    """Active ModuleSubscription for risk, dsb, gbu, ex modules."""
    from django_tenancy.module_models import ModuleSubscription

    subs = []
    for code in ("risk", "dsb", "gbu", "ex", "documents", "actions"):
        sub, _ = ModuleSubscription.objects.get_or_create(
            tenant_id=fixture_tenant.tenant_id,
            module=code,
            defaults={
                "organization_id": fixture_tenant.pk,
                "status": ModuleSubscription.Status.ACTIVE,
                "plan_code": "business",
            },
        )
        subs.append(sub)
    return subs


@pytest.fixture
def fixture_module_membership(db, fixture_module_subscription, fixture_tenant, fixture_user):
    """ModuleMembership granting fixture_user admin access to all subscribed modules."""
    from django_tenancy.module_models import ModuleMembership, ModuleSubscription

    memberships = []
    for sub in ModuleSubscription.objects.filter(tenant_id=fixture_tenant.tenant_id):
        mm, _ = ModuleMembership.objects.get_or_create(
            tenant_id=fixture_tenant.tenant_id,
            user=fixture_user,
            module=sub.module,
            defaults={"role": ModuleMembership.Role.ADMIN},
        )
        memberships.append(mm)
    return memberships


# ─── Permissions / RBAC fixtures ──────────────────────────────────────────


@pytest.fixture
def fixture_permission_read(db):
    """A read permission for risk.assessment."""
    from permissions.models import Permission

    perm, _ = Permission.objects.get_or_create(
        code="risk.assessment.read",
        defaults={
            "module": "risk",
            "resource": "assessment",
            "action": Permission.Action.VIEW,
        },
    )
    return perm


@pytest.fixture
def fixture_permission_write(db):
    """A write permission for risk.assessment."""
    from permissions.models import Permission

    perm, _ = Permission.objects.get_or_create(
        code="risk.assessment.write",
        defaults={
            "module": "risk",
            "resource": "assessment",
            "action": Permission.Action.EDIT,
        },
    )
    return perm


@pytest.fixture
def fixture_assignment(db, fixture_user, fixture_tenant, fixture_permission_read):
    """An Assignment: fixture_user has 'reader' role with read permission in fixture_tenant."""
    from permissions.models import Assignment, Role, RolePermission, Scope

    scope = Scope.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        scope_type=Scope.SCOPE_TENANT,
    )
    role, _ = Role.objects.get_or_create(
        tenant_id=fixture_tenant.tenant_id,
        name="reader",
        defaults={"is_system": False},
    )
    RolePermission.objects.get_or_create(role=role, permission=fixture_permission_read)
    assignment = Assignment.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        user_id=fixture_user.id,
        role=role,
        scope=scope,
    )
    return assignment
