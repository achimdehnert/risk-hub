"""Notification models for deadline alerts and system events."""

import uuid

from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """In-app notification for a tenant user."""

    class Severity(models.TextChoices):
        INFO = "info", "Information"
        WARNING = "warning", "Warnung"
        CRITICAL = "critical", "Kritisch"

    class Category(models.TextChoices):
        INSPECTION_DUE = "inspection_due", "Prüfung fällig"
        INSPECTION_OVERDUE = "inspection_overdue", "Prüfung überfällig"
        MEASURE_DUE = "measure_due", "Maßnahme fällig"
        CONCEPT_STATUS = "concept_status", "Konzept-Status"
        SDS_EXPIRING = "sds_expiring", "SDB läuft ab"
        APPROVAL_REQUIRED = "approval_required", "Freigabe erforderlich"
        SYSTEM = "system", "System"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    recipient_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="Target user; NULL = all tenant users",
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        db_index=True,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.INFO,
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default="")

    # Link to related entity
    entity_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    entity_id = models.UUIDField(null=True, blank=True)
    action_url = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "is_read", "-created_at"],
                name="notif_unread_idx",
            ),
            models.Index(
                fields=["tenant_id", "category", "-created_at"],
                name="notif_category_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.title}"

    def mark_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationPreference(models.Model):
    """Per-user notification delivery preferences."""

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "E-Mail"
        BOTH = "both", "Beides"
        NONE = "none", "Keine"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    category = models.CharField(
        max_length=30,
        choices=Notification.Category.choices,
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.BOTH,
    )
    # Reminder thresholds in days (e.g. [30, 7, 3, 1])
    reminder_days = models.JSONField(
        default=list,
        help_text="Erinnerung X Tage vorher, z.B. [30, 7, 3, 1]",
    )

    class Meta:
        db_table = "notifications_preference"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "user_id", "category"],
                name="uq_notif_pref_user_cat",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} / {self.category} → {self.channel}"
