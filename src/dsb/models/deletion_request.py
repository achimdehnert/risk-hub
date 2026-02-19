"""DeletionRequest — Art. 17 DSGVO Löschungsworkflow."""

import uuid

from django.conf import settings
from django.db import models

from .mandate import Mandate


class DeletionRequestStatus(models.TextChoices):
    PENDING = "pending", "Beantragt"
    AUTH_SENT = "auth_sent", "Authentifizierung angefordert"
    AUTH_RECEIVED = "auth_received", "Authentifizierung erhalten"
    DELETION_ORDERED = "deletion_ordered", "Löschung beauftragt"
    DELETION_CONFIRMED = "deletion_confirmed", "Löschung bestätigt"
    NOTIFIED = "notified", "Betroffener benachrichtigt"
    CLOSED = "closed", "Abgeschlossen"
    REJECTED = "rejected", "Abgelehnt"


WORKFLOW_TRANSITIONS = {
    DeletionRequestStatus.PENDING: [
        DeletionRequestStatus.AUTH_SENT,
        DeletionRequestStatus.REJECTED,
    ],
    DeletionRequestStatus.AUTH_SENT: [
        DeletionRequestStatus.AUTH_RECEIVED,
        DeletionRequestStatus.REJECTED,
    ],
    DeletionRequestStatus.AUTH_RECEIVED: [
        DeletionRequestStatus.DELETION_ORDERED,
        DeletionRequestStatus.REJECTED,
    ],
    DeletionRequestStatus.DELETION_ORDERED: [
        DeletionRequestStatus.DELETION_CONFIRMED,
    ],
    DeletionRequestStatus.DELETION_CONFIRMED: [
        DeletionRequestStatus.NOTIFIED,
    ],
    DeletionRequestStatus.NOTIFIED: [
        DeletionRequestStatus.CLOSED,
    ],
}

STEP_LABELS = {
    DeletionRequestStatus.PENDING: ("1", "Antrag eingegangen"),
    DeletionRequestStatus.AUTH_SENT: ("2", "Authentifizierung angefordert"),
    DeletionRequestStatus.AUTH_RECEIVED: ("3", "Authentifizierung bestätigt"),
    DeletionRequestStatus.DELETION_ORDERED: ("4", "Löschung beauftragt"),
    DeletionRequestStatus.DELETION_CONFIRMED: ("5", "Löschung bestätigt"),
    DeletionRequestStatus.NOTIFIED: ("6", "Betroffener benachrichtigt"),
    DeletionRequestStatus.CLOSED: ("✓", "Abgeschlossen"),
    DeletionRequestStatus.REJECTED: ("✗", "Abgelehnt"),
}


class DeletionRequest(models.Model):
    """Löschantrag gemäß Art. 17 DSGVO mit vollständigem Workflow."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="deletion_requests",
    )

    # Betroffene Person
    subject_name = models.CharField(max_length=200, verbose_name="Name der betroffenen Person")
    subject_email = models.EmailField(verbose_name="E-Mail der betroffenen Person")
    subject_reference = models.CharField(
        max_length=100, blank=True,
        verbose_name="Referenz / Kundennummer",
        help_text="Interne Referenz zur Identifikation",
    )

    # Antrag
    request_date = models.DateField(verbose_name="Antragsdatum")
    request_description = models.TextField(
        verbose_name="Beschreibung des Löschantrags",
        help_text="Welche Daten sollen gelöscht werden?",
    )
    data_categories = models.TextField(
        blank=True,
        verbose_name="Betroffene Datenkategorien",
    )

    # Workflow-Status
    status = models.CharField(
        max_length=30,
        choices=DeletionRequestStatus.choices,
        default=DeletionRequestStatus.PENDING,
        db_index=True,
    )

    # Zeitstempel je Schritt
    auth_sent_at = models.DateTimeField(null=True, blank=True)
    auth_received_at = models.DateTimeField(null=True, blank=True)
    deletion_ordered_at = models.DateTimeField(null=True, blank=True)
    deletion_confirmed_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Notizen je Schritt
    auth_notes = models.TextField(blank=True, verbose_name="Notizen Authentifizierung")
    deletion_notes = models.TextField(blank=True, verbose_name="Notizen Löschung")
    rejection_reason = models.TextField(blank=True, verbose_name="Ablehnungsgrund")

    # Verantwortlicher DSB
    assigned_to_id = models.UUIDField(null=True, blank=True)

    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_deletion_request"
        verbose_name = "Löschantrag"
        verbose_name_plural = "Löschanträge"
        ordering = ["-request_date", "-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_delreq_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_delreq_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return f"Löschantrag {self.subject_name} ({self.get_status_display()})"

    @property
    def is_open(self) -> bool:
        return self.status not in (
            DeletionRequestStatus.CLOSED,
            DeletionRequestStatus.REJECTED,
        )

    @property
    def next_steps(self) -> list:
        return WORKFLOW_TRANSITIONS.get(self.status, [])

    @property
    def step_number(self) -> str:
        return STEP_LABELS.get(self.status, ("?", ""))[0]

    @property
    def deadline_days(self) -> int | None:
        """Art. 17: 1 Monat Frist ab Antragsdatum."""
        from datetime import date
        if self.request_date:
            delta = (self.request_date.replace(
                month=self.request_date.month % 12 + 1,
                year=self.request_date.year + (1 if self.request_date.month == 12 else 0),
            ) - date.today()).days
            return delta
        return None
