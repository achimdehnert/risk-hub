# src/common/views.py
"""
Shared base ViewSets for Risk-Hub.

Provides consistent tenant-aware behavior across all modules:
- Tenant filtering via request.tenant_id (set by middleware)
- Fail-safe: returns empty queryset if no tenant context
- Tenant-ID guard on create operations
- Hybrid isolation for master data (global + tenant-scoped)
"""

from uuid import UUID

from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied


class TenantAwareViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet with mandatory tenant isolation.

    - get_queryset(): filters by tenant_id, returns empty QS if missing
    - perform_create(): sets tenant_id, raises if missing
    - get_tenant_id(): reads from request.tenant_id (middleware)
      with fallback to user.tenant_id and X-Tenant-ID header
    """

    def get_tenant_id(self) -> UUID | None:
        """Resolve tenant_id from request context."""
        # Primary: middleware-set attribute
        tenant_id = getattr(self.request, "tenant_id", None)
        if tenant_id:
            return tenant_id

        # Secondary: user model
        user = getattr(self.request, "user", None)
        if user and hasattr(user, "tenant_id") and user.tenant_id:
            return user.tenant_id

        # Tertiary: header (for tests / API clients)
        header = self.request.META.get("HTTP_X_TENANT_ID")
        if header:
            try:
                return UUID(header)
            except (ValueError, TypeError):
                pass

        return None

    def get_queryset(self):
        """Filter by tenant_id. Returns EMPTY queryset if no tenant."""
        qs = super().get_queryset()
        tenant_id = self.get_tenant_id()
        if tenant_id:
            return qs.filter(tenant_id=tenant_id)
        return qs.none()

    def perform_create(self, serializer):
        """Set tenant_id on create. Raises if no tenant context."""
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise PermissionDenied("Tenant context required for create.")
        extra = {"tenant_id": tenant_id}
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            model = serializer.Meta.model
            field_names = [
                f.name
                for f in model._meta.get_fields()
            ]
            if "created_by" in field_names:
                extra["created_by"] = user.id
        serializer.save(**extra)


class ReadOnlyMasterDataViewSet(TenantAwareViewSet):
    """
    ViewSet for master data with hybrid tenant isolation.

    Read: global (tenant_id IS NULL) + tenant-specific data
    Write: only tenant-specific (is_system=False)
    Delete: only tenant-specific (is_system=False)
    """

    def get_queryset(self):
        """Return global + tenant-scoped records."""
        qs = self.queryset
        tenant_id = self.get_tenant_id()
        if tenant_id:
            return qs.filter(
                Q(tenant_id__isnull=True)
                | Q(tenant_id=tenant_id)
            )
        return qs.filter(tenant_id__isnull=True)

    def perform_create(self, serializer):
        """Create tenant-specific master data only."""
        tenant_id = self.get_tenant_id()
        if not tenant_id:
            raise PermissionDenied("Tenant context required.")
        serializer.save(tenant_id=tenant_id, is_system=False)

    def perform_update(self, serializer):
        """Block updates to system data."""
        if serializer.instance.is_system:
            raise PermissionDenied("System data is read-only.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        """Block deletion of system data."""
        if instance.is_system:
            raise PermissionDenied("System data cannot be deleted.")
        super().perform_destroy(instance)


class ReadOnlyRefViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only ViewSet for global reference data (H/P statements etc.)."""

    permission_classes = [permissions.AllowAny]
