"""Root conftest for Risk-Hub tests."""

from __future__ import annotations

import pytest

from identity.models import User
from permissions.models import (
    Assignment,
    Permission,
    Role,
    RolePermission,
    Scope,
)
from tenancy.models import Membership, Organization, Site


@pytest.fixture()
def fixture_tenant(db):
    """Create a test tenant organization."""
    org = Organization.objects.create(
        slug="test-corp",
        name="Test Corp",
        status=Organization.Status.ACTIVE,
        plan_code="pro",
    )
    return org


@pytest.fixture()
def fixture_tenant_b(db):
    """Create a second tenant for isolation tests."""
    org = Organization.objects.create(
        slug="other-corp",
        name="Other Corp",
        status=Organization.Status.ACTIVE,
    )
    return org


@pytest.fixture()
def fixture_user(db, fixture_tenant):
    """Create a test user with membership in fixture_tenant."""
    user = User.objects.create_user(
        username="testuser",
        password="testpass123",
        tenant_id=fixture_tenant.tenant_id,
    )
    Membership.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        user=user,
        role=Membership.Role.MEMBER,
    )
    return user


@pytest.fixture()
def fixture_admin_user(db, fixture_tenant):
    """Create an admin user with membership."""
    user = User.objects.create_user(
        username="adminuser",
        password="adminpass123",
        tenant_id=fixture_tenant.tenant_id,
    )
    Membership.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        user=user,
        role=Membership.Role.ADMIN,
    )
    return user


@pytest.fixture()
def fixture_user_b(db, fixture_tenant_b):
    """Create a user in tenant B (for isolation tests)."""
    user = User.objects.create_user(
        username="otheruser",
        password="otherpass123",
        tenant_id=fixture_tenant_b.tenant_id,
    )
    Membership.objects.create(
        tenant_id=fixture_tenant_b.tenant_id,
        user=user,
        role=Membership.Role.MEMBER,
    )
    return user


@pytest.fixture()
def fixture_permission_read(db):
    """Create a read permission."""
    return Permission.objects.create(
        code="risk.assessment.read",
        module="risk",
        resource="assessment",
        action="view",
        is_system=True,
    )


@pytest.fixture()
def fixture_permission_write(db):
    """Create a write permission."""
    return Permission.objects.create(
        code="risk.assessment.write",
        module="risk",
        resource="assessment",
        action="create",
        is_system=True,
    )


@pytest.fixture()
def fixture_role_with_read(
    db, fixture_tenant, fixture_permission_read,
):
    """Create a role with read permission."""
    role = Role.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        name="reader",
    )
    RolePermission.objects.create(
        role=role, permission=fixture_permission_read,
    )
    return role


@pytest.fixture()
def fixture_scope_tenant(db, fixture_tenant):
    """Create a TENANT-level scope."""
    return Scope.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        scope_type=Scope.SCOPE_TENANT,
    )


@pytest.fixture()
def fixture_assignment(
    db,
    fixture_user,
    fixture_tenant,
    fixture_role_with_read,
    fixture_scope_tenant,
):
    """Assign fixture_user the reader role at tenant scope."""
    return Assignment.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        user_id=fixture_user.id,
        role=fixture_role_with_read,
        scope=fixture_scope_tenant,
    )


@pytest.fixture()
def fixture_site(db, fixture_tenant):
    """Create a test site."""
    return Site.objects.create(
        tenant_id=fixture_tenant.tenant_id,
        organization=fixture_tenant,
        name="Hauptwerk",
        address="Musterstr. 1, 12345 Berlin",
    )
