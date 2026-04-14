"""Tests for permissions models — Permission, Role, Scope, Assignment, Override."""

import uuid

import pytest

from permissions.models import (
    Assignment,
    Permission,
    PermissionOverride,
    Role,
    RolePermission,
    Scope,
)


@pytest.mark.django_db
class TestPermission:
    """Permission model tests."""

    def test_should_create_permission(self):
        perm = Permission.objects.create(
            code="risk.assessment.view",
            module="risk",
            resource="assessment",
            action=Permission.Action.VIEW,
        )
        assert perm.pk is not None
        assert str(perm) == "risk.assessment.view"

    def test_should_enforce_unique_code(self):
        Permission.objects.create(code="dup.test", module="dup", resource="test")
        with pytest.raises(Exception):
            Permission.objects.create(code="dup.test", module="dup", resource="test2")

    def test_action_choices(self):
        actions = [c[0] for c in Permission.Action.choices]
        assert "view" in actions
        assert "create" in actions
        assert "delete" in actions
        assert "approve" in actions


@pytest.mark.django_db
class TestRole:
    """Role model tests."""

    def test_should_create_role(self, fixture_tenant):
        role = Role.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            name="editor",
        )
        assert str(role) == "editor"

    def test_should_enforce_unique_name_per_tenant(self, fixture_tenant):
        Role.objects.create(tenant_id=fixture_tenant.tenant_id, name="admin")
        with pytest.raises(Exception):
            Role.objects.create(tenant_id=fixture_tenant.tenant_id, name="admin")

    def test_same_name_allowed_in_different_tenant(self, fixture_tenant, fixture_tenant_b):
        Role.objects.create(tenant_id=fixture_tenant.tenant_id, name="shared-name")
        role_b = Role.objects.create(tenant_id=fixture_tenant_b.tenant_id, name="shared-name")
        assert role_b.pk is not None

    def test_should_link_permissions_via_rolepermission(self, fixture_tenant):
        perm = Permission.objects.create(code="test.link", module="test", resource="link")
        role = Role.objects.create(tenant_id=fixture_tenant.tenant_id, name="linker")
        RolePermission.objects.create(role=role, permission=perm)
        assert perm in role.permissions.all()


@pytest.mark.django_db
class TestScope:
    """Scope model tests."""

    def test_should_create_tenant_scope(self, fixture_tenant):
        scope = Scope.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            scope_type=Scope.SCOPE_TENANT,
        )
        assert "TENANT:" in str(scope)

    def test_should_create_site_scope(self, fixture_tenant, fixture_site):
        scope = Scope.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            scope_type=Scope.SCOPE_SITE,
            site_id=fixture_site.pk,
        )
        assert "SITE:" in str(scope)

    def test_should_create_asset_scope(self, fixture_tenant):
        asset_id = uuid.uuid4()
        scope = Scope.objects.create(
            tenant_id=fixture_tenant.tenant_id,
            scope_type=Scope.SCOPE_ASSET,
            asset_id=asset_id,
        )
        assert "ASSET:" in str(scope)


@pytest.mark.django_db
class TestAssignment:
    """Assignment model tests."""

    def test_should_create_assignment(self, fixture_assignment):
        assert fixture_assignment.pk is not None
        assert fixture_assignment.tenant_id is not None

    def test_should_enforce_unique_assignment(self, fixture_assignment):
        with pytest.raises(Exception):
            Assignment.objects.create(
                tenant_id=fixture_assignment.tenant_id,
                user_id=fixture_assignment.user_id,
                role=fixture_assignment.role,
                scope=fixture_assignment.scope,
            )


@pytest.mark.django_db
class TestPermissionOverride:
    """PermissionOverride model tests."""

    def test_should_create_grant_override(self, fixture_tenant, fixture_user):
        from tenancy.models import Membership

        ms = Membership.objects.get(tenant_id=fixture_tenant.tenant_id, user=fixture_user)
        perm = Permission.objects.create(code="override.test", module="test", resource="override")
        override = PermissionOverride.objects.create(
            membership=ms,
            permission=perm,
            allowed=True,
            reason="Special access for testing",
        )
        assert override.allowed is True

    def test_should_create_deny_override(self, fixture_tenant, fixture_user):
        from tenancy.models import Membership

        ms = Membership.objects.get(tenant_id=fixture_tenant.tenant_id, user=fixture_user)
        perm = Permission.objects.create(code="deny.test", module="test", resource="deny")
        override = PermissionOverride.objects.create(
            membership=ms,
            permission=perm,
            allowed=False,
            reason="Restricted",
        )
        assert override.allowed is False

    def test_should_enforce_unique_membership_permission(self, fixture_tenant, fixture_user):
        from tenancy.models import Membership

        ms = Membership.objects.get(tenant_id=fixture_tenant.tenant_id, user=fixture_user)
        perm = Permission.objects.create(code="unique.override", module="test", resource="unique")
        PermissionOverride.objects.create(membership=ms, permission=perm, allowed=True)
        with pytest.raises(Exception):
            PermissionOverride.objects.create(membership=ms, permission=perm, allowed=False)
