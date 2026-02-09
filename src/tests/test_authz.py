"""Tests for authorization service (permissions/authz.py)."""

from __future__ import annotations

import pytest
from django.utils import timezone

from common.context import set_tenant, set_user_id
from permissions.authz import (
    PermissionDenied,
    has_permission,
    require_permission,
)
from permissions.models import PermissionOverride
from tenancy.models import Membership


@pytest.mark.django_db
class TestHasPermission:
    """Test has_permission() with 3-step evaluation."""

    def test_should_grant_via_role(self, fixture_assignment):
        """User with role-based read permission should pass."""
        a = fixture_assignment
        assert has_permission(
            a.user_id, a.tenant_id, "risk.assessment.read",
        ) is True

    def test_should_deny_without_assignment(
        self, fixture_user, fixture_tenant,
    ):
        """User without any assignment should be denied."""
        assert has_permission(
            fixture_user.id, fixture_tenant.tenant_id,
            "risk.assessment.read",
        ) is False

    def test_should_deny_without_membership(
        self, fixture_tenant,
    ):
        """Non-existent user should be denied."""
        import uuid
        assert has_permission(
            uuid.uuid4(), fixture_tenant.tenant_id,
            "risk.assessment.read",
        ) is False

    def test_should_deny_wrong_permission(self, fixture_assignment):
        """User should be denied for permission not in role."""
        a = fixture_assignment
        assert has_permission(
            a.user_id, a.tenant_id, "risk.assessment.write",
        ) is False

    def test_should_deny_via_override(
        self, fixture_assignment, fixture_permission_read,
    ):
        """Explicit deny override should block role-based grant."""
        a = fixture_assignment
        membership = Membership.objects.get(
            tenant_id=a.tenant_id, user_id=a.user_id,
        )
        PermissionOverride.objects.create(
            membership=membership,
            permission=fixture_permission_read,
            allowed=False,
            reason="Test deny",
        )
        assert has_permission(
            a.user_id, a.tenant_id, "risk.assessment.read",
        ) is False

    def test_should_grant_via_override(
        self,
        fixture_user,
        fixture_tenant,
        fixture_permission_write,
    ):
        """Explicit grant override should allow without role."""
        membership = Membership.objects.get(
            tenant_id=fixture_tenant.tenant_id,
            user_id=fixture_user.id,
        )
        PermissionOverride.objects.create(
            membership=membership,
            permission=fixture_permission_write,
            allowed=True,
        )
        assert has_permission(
            fixture_user.id, fixture_tenant.tenant_id,
            "risk.assessment.write",
        ) is True

    def test_should_ignore_expired_override(
        self, fixture_assignment, fixture_permission_read,
    ):
        """Expired deny override should not block access."""
        a = fixture_assignment
        membership = Membership.objects.get(
            tenant_id=a.tenant_id, user_id=a.user_id,
        )
        PermissionOverride.objects.create(
            membership=membership,
            permission=fixture_permission_read,
            allowed=False,
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )
        assert has_permission(
            a.user_id, a.tenant_id, "risk.assessment.read",
        ) is True


@pytest.mark.django_db
class TestRequirePermission:
    """Test require_permission() context-based check."""

    def test_should_raise_without_context(self):
        """Missing context should raise PermissionDenied."""
        set_tenant(None, None)
        set_user_id(None)
        with pytest.raises(PermissionDenied):
            require_permission("risk.assessment.read")

    def test_should_pass_with_valid_context(
        self, fixture_assignment,
    ):
        """Valid context + assignment should pass."""
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)
        require_permission("risk.assessment.read")

    def test_should_raise_for_wrong_permission(
        self, fixture_assignment,
    ):
        """Valid context but wrong permission should raise."""
        a = fixture_assignment
        set_tenant(a.tenant_id, "test-corp")
        set_user_id(a.user_id)
        with pytest.raises(PermissionDenied):
            require_permission("risk.assessment.delete")


@pytest.mark.django_db
class TestTenantIsolation:
    """Test cross-tenant isolation."""

    def test_should_deny_cross_tenant_access(
        self, fixture_assignment, fixture_tenant_b,
    ):
        """User in tenant A should not access tenant B."""
        a = fixture_assignment
        assert has_permission(
            a.user_id, fixture_tenant_b.tenant_id,
            "risk.assessment.read",
        ) is False
