"""Risk assessment models."""

import uuid

from django.db import models
from django_tenancy.managers import TenantManager

class Assessment(models.Model):
    """Risk assessment / Gefährdungsbeurteilung."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        ARCHIVED = "archived", "Archived"

    class Category(models.TextChoices):
        BRANDSCHUTZ = "brandschutz", "Brandschutz"
        EXPLOSIONSSCHUTZ = "explosionsschutz", "Explosionsschutz"
        ARBEITSSICHERHEIT = "arbeitssicherheit", "Arbeitssicherheit"
        ARBEITSSCHUTZ = "arbeitsschutz", "Arbeitsschutz"
        GENERAL = "general", "Allgemein"

    tenant_id = models.UUIDField(db_index=True)

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    site_id = models.UUIDField(null=True, blank=True, db_index=True)

    created_by_id = models.UUIDField(null=True, blank=True)
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_assessment"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["draft", "in_review", "approved", "archived"],
                ),
                name="ck_assessment_status_valid",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_assessment_title_per_tenant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_assessment_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "category"],
                name="idx_assessment_tenant_category",
            ),
        ]

    def __str__(self) -> str:
        return self.title

class Hazard(models.Model):
    """Individual hazard within an assessment."""

    class Severity(models.IntegerChoices):
        LOW = 1, "Gering"
        MEDIUM = 2, "Mittel"
        HIGH = 3, "Hoch"
        VERY_HIGH = 4, "Sehr hoch"
        CRITICAL = 5, "Kritisch"

    class Probability(models.IntegerChoices):
        UNLIKELY = 1, "Unwahrscheinlich"
        RARE = 2, "Selten"
        OCCASIONAL = 3, "Gelegentlich"
        PROBABLE = 4, "Wahrscheinlich"
        FREQUENT = 5, "Häufig"

    class MitigationStatus(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        MITIGATED = "mitigated", "Gemindert"
        ACCEPTED = "accepted", "Akzeptiert"

    tenant_id = models.UUIDField(db_index=True)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="hazards",
    )

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")

    severity = models.IntegerField(
        choices=Severity.choices,
        default=Severity.LOW,
    )
    probability = models.IntegerField(
        choices=Probability.choices,
        default=Probability.UNLIKELY,
    )

    mitigation = models.TextField(blank=True, default="")
    residual_risk = models.IntegerField(null=True, blank=True)
    mitigation_status = models.CharField(
        max_length=15,
        choices=MitigationStatus.choices,
        default=MitigationStatus.OPEN,
        db_index=True,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID der verantwortlichen Person für die Maßnahme",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fälligkeitsdatum der Maßnahme",
    )
    substance_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Verknüpfter Gefahrstoff (substances.Substance, optional)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_hazard"
        indexes = [
            models.Index(
                fields=["tenant_id", "assessment"],
                name="idx_hazard_tenant_assessment",
            ),
            models.Index(
                fields=["tenant_id", "mitigation_status"],
                name="idx_hazard_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "due_date"],
                name="idx_hazard_tenant_due_date",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def risk_score(self) -> int:
        """Calculate risk score (severity * probability)."""
        return self.severity * self.probability

    @property
    def is_overdue(self) -> bool:
        """True if mitigation is not done and due_date has passed."""
        from django.utils import timezone

        if not self.due_date:
            return False
        return (
            self.mitigation_status
            not in (
                self.MitigationStatus.MITIGATED,
                self.MitigationStatus.ACCEPTED,
            )
            and self.due_date < timezone.now().date()
        )
