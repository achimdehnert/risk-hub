"""
Base Models
===========

Abstrakte Basismodelle für:
- Tenant-scoped Entities
- Timestamped Models
- Soft Delete
"""

import uuid

from django.db import models

from apps.core.request_context import get_context


class TimestampedModel(models.Model):
    """Mixin für created_at / updated_at."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantModel(TimestampedModel):
    """
    Basismodell für alle Tenant-scoped Entities.
    
    Erzwingt:
    - tenant_id auf jedem Record
    - Automatisches Setzen bei create()
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Tenant ID automatisch setzen wenn nicht vorhanden
        if not self.tenant_id:
            ctx = get_context()
            if ctx.tenant_id:
                self.tenant_id = ctx.tenant_id
            else:
                raise ValueError("tenant_id required but not in context")
        super().save(*args, **kwargs)


class TenantQuerySet(models.QuerySet):
    """QuerySet mit automatischem Tenant-Filter."""

    def for_tenant(self, tenant_id: uuid.UUID | None = None):
        """Filtert auf aktuellen Tenant."""
        if tenant_id is None:
            ctx = get_context()
            tenant_id = ctx.tenant_id

        if tenant_id is None:
            return self.none()

        return self.filter(tenant_id=tenant_id)


class TenantManager(models.Manager):
    """Manager mit Tenant-aware QuerySet."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant_id: uuid.UUID | None = None):
        return self.get_queryset().for_tenant(tenant_id)


class SoftDeleteModel(models.Model):
    """Mixin für Soft Delete."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])


class SoftDeleteQuerySet(TenantQuerySet):
    """QuerySet mit Soft Delete Filter."""

    def active(self):
        """Nur nicht-gelöschte Records."""
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        """Nur gelöschte Records."""
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(TenantManager):
    """Manager mit Soft Delete Support."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()
