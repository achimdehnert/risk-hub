"""Audit — Datenschutz-Audits."""

import uuid

from django.db import models

from .choices import SeverityLevel
from .mandate import Mandate


class PrivacyAudit(models.Model):
    """Datenschutz-Audit."""

    class AuditType(models.TextChoices):
        INTERNAL = "internal", "Intern"
        EXTERNAL = "external", "Extern"
        SPOT_CHECK = "spot_check", "Stichprobe"

    class Status(models.TextChoices):
        PLANNED = "planned", "Geplant"
        IN_PROGRESS = "in_progress", "In Durchführung"
        COMPLETED = "completed", "Abgeschlossen"
        CANCELLED = "cancelled", "Abgebrochen"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="audits",
    )
    title = models.CharField(
        max_length=300,
        help_text="Titel / Gegenstand des Audits",
    )
    audit_type = models.CharField(
        max_length=20,
        choices=AuditType.choices,
    )
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
    )
    report_document_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu documents.Document (lose Kopplung)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_privacy_audit"
        verbose_name = "Datenschutz-Audit"
        verbose_name_plural = "Datenschutz-Audits"
        ordering = ["-scheduled_date"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_audit_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_audit_type_display()})"


class AuditFinding(models.Model):
    """Einzelbefund eines Audits."""

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        RESOLVED = "resolved", "Behoben"
        ACCEPTED = "accepted", "Akzeptiert"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    audit = models.ForeignKey(
        PrivacyAudit,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    action_item_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu actions.ActionItem (lose Kopplung)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_audit_finding"
        verbose_name = "Audit-Befund"
        verbose_name_plural = "Audit-Befunde"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_finding_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title
