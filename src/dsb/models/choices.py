"""Shared TextChoices für DSB Module (F7: DRY)."""

from django.db import models


class MeasureStatus(models.TextChoices):
    """Status für TOM (TechnicalMeasure + OrganizationalMeasure)."""

    PLANNED = "planned", "Geplant"
    IMPLEMENTED = "implemented", "Umgesetzt"
    VERIFIED = "verified", "Verifiziert"
    OBSOLETE = "obsolete", "Obsolet"


class SeverityLevel(models.TextChoices):
    """Schweregrad (AuditFinding + Breach)."""

    LOW = "low", "Gering"
    MEDIUM = "medium", "Mittel"
    HIGH = "high", "Hoch"
    CRITICAL = "critical", "Kritisch"
