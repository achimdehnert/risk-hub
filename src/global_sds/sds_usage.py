# src/global_sds/sds_usage.py
"""
SdsUsage — Tenant-spezifische Nutzung globaler SDS-Revisionen (ADR-012).

Verknüpft globale SdsRevision mit einem Tenant.
ALLE EHS-Module (GBU, Ex-Schutz) referenzieren SdsUsage,
niemals direkt GlobalSdsRevision.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q

from django_tenancy.managers import TenantManager

from global_sds.models import GlobalSdsRevision


class SdsUsageStatus(models.TextChoices):
    """Status einer SDS-Nutzung pro Tenant."""

    ACTIVE = "ACTIVE", "Aktiv"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Wartet auf Freigabe"
    REVIEW_REQUIRED = (
        "REVIEW_REQUIRED",
        "Überprüfung erforderlich (Safety Critical)",
    )
    UPDATE_AVAILABLE = (
        "UPDATE_AVAILABLE",
        "Update verfügbar (Regulatory)",
    )
    SUPERSEDED = "SUPERSEDED", "Abgelöst"
    WITHDRAWN = "WITHDRAWN", "Zurückgezogen"


class SdsUsage(models.Model):
    """
    Verknüpft eine globale SdsRevision mit einem Tenant.

    Enthält Freigabe-Workflow und Update-Tracking.
    GefStoffV §6(4): aktive Nutzung erfordert namentliche Freigabe.
    """

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID für Mandantentrennung",
    )

    sds_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.PROTECT,
        related_name="usages",
        help_text="Globale SDS-Revision (BetrSichV Audit-Immutabilität)",
    )
    status = models.CharField(
        max_length=20,
        choices=SdsUsageStatus.choices,
        default=SdsUsageStatus.PENDING_APPROVAL,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_sds_usages",
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    internal_note = models.TextField(blank=True, default="")

    # Update-Tracking (befüllt durch SdsSupersessionService)
    pending_update_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_for_usages",
    )
    pending_update_impact = models.CharField(
        max_length=20, blank=True, default="",
    )
    review_deadline = models.DateField(
        null=True, blank=True,
        help_text="Frist für Review (GefStoffV §7)",
    )

    # Zurückstell-Nachweis — GefStoffV §7 Compliance
    update_deferred_reason = models.TextField(
        blank=True, default="",
        help_text="Pflichtbegründung bei Zurückstellung",
    )
    update_deferred_until = models.DateField(
        null=True, blank=True,
    )
    update_deferred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deferred_sds_updates",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "global_sds_usage"
        verbose_name = "SDS-Nutzung (Tenant)"
        verbose_name_plural = "SDS-Nutzungen (Tenant)"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "sds_revision"],
                name="uq_sds_usage_per_tenant",
            ),
            # M-3: GefStoffV §6(4) — aktive Nutzung erfordert
            # namentliche Freigabe
            models.CheckConstraint(
                check=(
                    ~Q(status="ACTIVE")
                    | Q(approved_by__isnull=False)
                ),
                name="chk_sds_usage_active_requires_approver",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_sds_usage_tenant_status",
            ),
        ]

    def __str__(self):
        return (
            f"SdsUsage {self.sds_revision} "
            f"(Tenant {str(self.tenant_id)[:8]})"
        )
