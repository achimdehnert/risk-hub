"""Risk assessment models."""

import uuid
from django.db import models


class Assessment(models.Model):
    """Risk assessment / Gefährdungsbeurteilung."""
    
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("archived", "Archived"),
    ]
    
    CATEGORY_CHOICES = [
        ("brandschutz", "Brandschutz"),
        ("explosionsschutz", "Explosionsschutz"),
        ("arbeitssicherheit", "Arbeitssicherheit"),
        ("arbeitsschutz", "Arbeitsschutz"),
        ("general", "Allgemein"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    
    site_id = models.UUIDField(null=True, blank=True, db_index=True)
    
    created_by_id = models.UUIDField(null=True, blank=True)
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "risk_assessment"
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=["draft", "in_review", "approved", "archived"]),
                name="ck_assessment_status_valid",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_assessment_title_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "category"]),
        ]

    def __str__(self) -> str:
        return self.title


class Hazard(models.Model):
    """Individual hazard within an assessment."""
    
    SEVERITY_CHOICES = [
        (1, "Gering"),
        (2, "Mittel"),
        (3, "Hoch"),
        (4, "Sehr hoch"),
        (5, "Kritisch"),
    ]
    
    PROBABILITY_CHOICES = [
        (1, "Unwahrscheinlich"),
        (2, "Selten"),
        (3, "Gelegentlich"),
        (4, "Wahrscheinlich"),
        (5, "Häufig"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="hazards")
    
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    probability = models.IntegerField(choices=PROBABILITY_CHOICES, default=1)
    
    mitigation = models.TextField(blank=True, default="")
    residual_risk = models.IntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "risk_hazard"
        indexes = [
            models.Index(fields=["tenant_id", "assessment"]),
        ]

    def __str__(self) -> str:
        return self.title
    
    @property
    def risk_score(self) -> int:
        """Calculate risk score (severity * probability)."""
        return self.severity * self.probability
