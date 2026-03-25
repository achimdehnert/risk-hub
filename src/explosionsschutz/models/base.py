# src/explosionsschutz/models/base.py
"""
Hybrid Tenant-Isolation Infrastructure für Stammdaten.

tenant_id = NULL + is_system = True  → Globale System-Daten (nicht editierbar)
tenant_id = UUID + is_system = False → Tenant-spezifische Daten
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TenantScopedMasterDataManager(models.Manager):
    """
    Custom Manager für Stammdaten mit Hybrid-Tenant-Isolation.

    Liefert:
    - Globale Daten (tenant_id=NULL) UND
    - Tenant-spezifische Daten für den aktuellen Tenant
    """

    def for_tenant(self, tenant_id: uuid.UUID):
        """
        Gibt alle für einen Tenant sichtbaren Einträge zurück:
        - Globale Einträge (tenant_id IS NULL)
        - Eigene Einträge (tenant_id = tenant_id)
        """
        return self.filter(models.Q(tenant_id__isnull=True) | models.Q(tenant_id=tenant_id))

    def global_only(self):
        """Nur globale System-Einträge"""
        return self.filter(tenant_id__isnull=True, is_system=True)

    def tenant_only(self, tenant_id: uuid.UUID):
        """Nur tenant-spezifische Einträge"""
        return self.filter(tenant_id=tenant_id)


class TenantScopedMasterData(models.Model):
    """
    Abstrakte Basisklasse für Stammdaten mit Hybrid-Tenant-Isolation.

    tenant_id = NULL + is_system = True  → Globale System-Daten (nicht editierbar)
    tenant_id = UUID + is_system = False → Tenant-spezifische Daten
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="NULL = global/system, UUID = tenant-spezifisch",
    )

    is_system = models.BooleanField(
        default=False, help_text="System-Daten sind global und nicht editierbar"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedMasterDataManager()

    class Meta:
        abstract = True

    def clean(self):
        """Validierung: System-Daten müssen global sein"""
        if self.is_system and self.tenant_id is not None:
            raise ValidationError(
                "System-Daten (is_system=True) müssen global sein (tenant_id=NULL)"
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
