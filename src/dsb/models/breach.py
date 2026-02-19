"""Breach — Datenpannen (Art. 33 DSGVO)."""

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from .choices import SeverityLevel
from .lookups import Category
from .mandate import Mandate


class BreachStatus(models.TextChoices):
    REPORTED = "reported", "Panne gemeldet"
    DSB_NOTIFIED = "dsb_notified", "DSB kontaktiert"
    AUTHORITY_NOTIFIED = "authority_notified", "Behörde benachrichtigt"
    REMEDIATION = "remediation", "Behebung läuft"
    RESOLVED = "resolved", "Panne behoben"
    AUTHORITY_CLOSED = "authority_closed", "Behörde informiert (Abschluss)"
    CLOSED = "closed", "Abgeschlossen"


BREACH_TRANSITIONS = {
    BreachStatus.REPORTED: [BreachStatus.DSB_NOTIFIED],
    BreachStatus.DSB_NOTIFIED: [BreachStatus.AUTHORITY_NOTIFIED],
    BreachStatus.AUTHORITY_NOTIFIED: [BreachStatus.REMEDIATION],
    BreachStatus.REMEDIATION: [BreachStatus.RESOLVED],
    BreachStatus.RESOLVED: [BreachStatus.AUTHORITY_CLOSED],
    BreachStatus.AUTHORITY_CLOSED: [BreachStatus.CLOSED],
}


class Breach(models.Model):
    """Datenpanne gemäß Art. 33 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)

    # Workflow
    workflow_status = models.CharField(
        max_length=30,
        choices=BreachStatus.choices,
        default=BreachStatus.REPORTED,
        db_index=True,
    )

    # Meldender (Firma)
    reported_by_name = models.CharField(max_length=200, blank=True, verbose_name="Gemeldet von")
    reported_by_email = models.EmailField(blank=True, verbose_name="E-Mail Meldender")
    title = models.CharField(max_length=300, blank=True, verbose_name="Kurzbeschreibung")

    # Behörde
    authority_name = models.CharField(
        max_length=200, blank=True,
        verbose_name="Aufsichtsbehörde",
        help_text="z.B. LfDI Baden-Württemberg",
    )
    authority_reference = models.CharField(max_length=100, blank=True, verbose_name="Aktenzeichen Behörde")

    # Zeitstempel Workflow-Schritte
    dsb_notified_at = models.DateTimeField(null=True, blank=True)
    authority_notified_at = models.DateTimeField(null=True, blank=True)
    remediation_started_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    authority_closed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Notizen je Schritt
    dsb_notes = models.TextField(blank=True)
    authority_notes = models.TextField(blank=True)
    remediation_notes = models.TextField(blank=True)
    resolution_notes = models.TextField(blank=True)

    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="breaches",
    )
    discovered_at = models.DateTimeField()
    reported_to_authority_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Meldezeitpunkt an Aufsichtsbehörde",
    )
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
    )
    affected_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Betroffene Datenkategorien (Art. 33 Abs. 3 lit. a)",
    )
    affected_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Ungefähre Anzahl betroffener Personen",
    )
    root_cause = models.TextField(blank=True, default="")
    measures_taken = models.TextField(
        blank=True,
        default="",
        help_text="Ergriffene Abhilfemaßnahmen (Art. 33 Abs. 3 lit. d)",
    )
    notified_subjects = models.BooleanField(
        default=False,
        help_text="Betroffene benachrichtigt (Art. 34 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_breach"
        verbose_name = "Datenpanne"
        verbose_name_plural = "Datenpannen"
        ordering = ["-discovered_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "severity"],
                name="idx_dsb_breach_tenant_sev",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Datenpanne {self.discovered_at:%Y-%m-%d}"
            f" ({self.get_severity_display()})"
        )

    @property
    def deadline_72h(self):
        """72h-Meldefrist (Art. 33)."""
        return self.discovered_at + timedelta(hours=72)

    @property
    def is_overdue(self) -> bool:
        """Prüft ob 72h-Frist überschritten und noch nicht gemeldet."""
        return (
            self.reported_to_authority_at is None
            and timezone.now() > self.deadline_72h
        )

    @property
    def is_open(self) -> bool:
        return self.workflow_status not in (BreachStatus.CLOSED,)

    @property
    def next_steps(self) -> list:
        return BREACH_TRANSITIONS.get(self.workflow_status, [])
