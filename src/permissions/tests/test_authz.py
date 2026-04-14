"""Tests for permissions.authz — has_permission, require_permission (ADR-003)."""

import uuid
from unittest.mock import patch

import pytest
from django.utils import timezone

from permissions.authz import PermissionDenied, has_permission, require_permission
from permissions.models import (
    Assignment,
    Permission,
    PermissionOverride,
    Role,
    RolePermission,
    Scope,
)


@pytest.mark.django_db
class TestHasPermission:
    """has_permission tests — RBAC with override support."""

    def test_should_grant_via_role_assignment(
        self, fixture_user, fixture_tenant, fixture_assignment, fixture_permission_read
    ):
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is True

    def test_should_deny_missing_permission(
        self, fixture_user, fixture_tenant, fixture_assignment
    ):
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.delete",
        )
        assert result is False

    def test_should_deny_user_without_membership(self, fixture_tenant):
        result = has_permission(
            user_id=uuid.uuid4(),
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is False

    def test_should_deny_user_in_wrong_tenant(
        self, fixture_user, fixture_tenant_b, fixture_assignment
    ):
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant_b.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is False

    def test_should_deny_via_explicit_deny_override(
        self, fixture_user, fixture_tenant, fixture_assignment, fixture_permission_read
    ):
        from tenancy.models import Membership

        ms = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        )
        PermissionOverride.objects.create(
            membership=ms,
            permission=fixture_permission_read,
            allowed=False,
            reason="Blocked for audit",
        )
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is False

    def test_should_grant_via_explicit_grant_override(
        self, fixture_user, fixture_tenant
    ):
        from tenancy.models import Membership

        ms = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        )
        perm = Permission.objects.create(
            code="special.access",
            module="special",
            resource="access",
            action=Permission.Action.MANAGE,
        )
        PermissionOverride.objects.create(
            membership=ms,
            permission=perm,
            allowed=True,
        )
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="special.access",
        )
        assert result is True

    def test_should_ignore_expired_deny_override(
        self, fixture_user, fixture_tenant, fixture_assignment, fixture_permission_read
    ):
        from tenancy.models import Membership

        ms = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        )
        PermissionOverride.objects.create(
            membership=ms,
            permission=fixture_permission_read,
            allowed=False,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is True

    def test_should_ignore_expired_grant_override(
        self, fixture_user, fixture_tenant
    ):
        from tenancy.models import Membership

        ms = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        )
        perm = Permission.objects.create(
            code="expired.grant",
            module="test",
            resource="expired",
        )
        PermissionOverride.objects.create(
            membership=ms,
            permission=perm,
            allowed=True,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="expired.grant",
        )
        assert result is False

    def test_deny_override_takes_precedence_over_role(
        self, fixture_user, fixture_tenant, fixture_assignment, fixture_permission_read
    ):
        """ADR-003: deny override wins over role-based grant."""
        from tenancy.models import Membership

        ms = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id, user=fixture_user
        )
        PermissionOverride.objects.create(
            membership=ms,
            permission=fixture_permission_read,
            allowed=False,
        )
        result = has_permission(
            user_id=fixture_user.pk,
            tenant_id=fixture_tenant.tenant_id,
            permission_code="risk.assessment.read",
        )
        assert result is False


@pytest.mark.django_db
class TestRequirePermission:
    """require_permission tests."""

    def test_should_pass_when_no_permissions_bootstrapped(self):
        """When zero Permission rows exist, all checks pass (bootstrap mode)."""
        assert Permission.objects.count() == 0
        require_permission("anything.goes")

    def test_should_raise_without_context(self, fixture_permission_read):
        """When permission rows exist but no context, should raise."""
        with patch("permissions.authz.get_context") as mock_ctx:
            mock_ctx.return_value.tenant_id = None
            mock_ctx.return_value.user_id = None
            with pytest.raises(PermissionDenied):
                require_permission("risk.assessment.read")

    def test_should_pass_with_valid_assignment(
        self, fixture_user, fixture_tenant, fixture_assignment, fixture_permission_read
    ):
        with patch("permissions.authz.get_context") as mock_ctx:
            mock_ctx.return_value.tenant_id = fixture_tenant.tenant_id
            mock_ctx.return_value.user_id = fixture_user.pk
            require_permission("risk.assessment.read")

    def test_should_raise_without_assignment(
        self, fixture_user, fixture_tenant, fixture_permission_read
    ):
        with patch("permissions.authz.get_context") as mock_ctx:
            mock_ctx.return_value.tenant_id = fixture_tenant.tenant_id
            mock_ctx.return_value.user_id = fixture_user.pk
            with pytest.raises(PermissionDenied):
                require_permission("risk.assessment.read")


@pytest.mark.unit
class TestPermissionDenied:
    """PermissionDenied exception tests."""

    def test_should_include_permission_code(self):
        exc = PermissionDenied("risk.assessment.delete")
        assert exc.permission_code == "risk.assessment.delete"
        assert "risk.assessment.delete" in str(exc)
