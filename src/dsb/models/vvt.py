"""VVT — Verarbeitungsverzeichnis (Art. 30 DSGVO)."""

import uuid

from django.db import models

from .lookups import (
    Category,
    Purpose,
    Recipient,
    StandardRetentionPeriod,
    SubjectGroup,
)
from .mandate import Mandate


class ProcessingActivity(models.Model):
    """Verarbeitungstätigkeit gemäß Art. 30 DSGVO (VVT)."""

    class LegalBasis(models.TextChoices):
        CONSENT = "consent", "Art. 6(1)(a) Einwilligung"
        CONTRACT = "contract", "Art. 6(1)(b) Vertragserfüllung"
        LEGAL_OBLIGATION = (
            "legal_obligation",
            "Art. 6(1)(c) Rechtl. Verpflichtung",
        )
        VITAL_INTEREST = (
            "vital_interest",
            "Art. 6(1)(d) Lebenswichtige Interessen",
        )
        PUBLIC_INTEREST = (
            "public_interest",
            "Art. 6(1)(e) Öffentliches Interesse",
        )
        LEGITIMATE_INTEREST = (
            "legitimate_interest",
            "Art. 6(1)(f) Berechtigtes Interesse",
        )

    class RiskLevel(models.TextChoices):
        LOW = "low", "Gering"
        MEDIUM = "medium", "Mittel"
        HIGH = "high", "Hoch"
        VERY_HIGH = "very_high", "Sehr hoch"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="processing_activities",
    )
    number = models.PositiveIntegerField(
        help_text="Laufende Nummer im Mandat (z.B. 1, 2, 3)",
    )
    name = models.CharField(max_length=300)
    purposes = models.ManyToManyField(
        Purpose,
        blank=True,
        help_text="Zwecke der Verarbeitung (Art. 30 Abs. 1 lit. b)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Ergänzende Beschreibung der Verarbeitung",
    )
    legal_basis = models.CharField(
        max_length=30,
        choices=LegalBasis.choices,
        help_text="Rechtsgrundlage nach Art. 6 Abs. 1 DSGVO",
    )
    data_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Kategorien personenbezogener Daten",
    )
    data_subjects = models.ManyToManyField(
        SubjectGroup,
        blank=True,
        help_text="Kategorien betroffener Personen",
    )
    recipients = models.ManyToManyField(
        Recipient,
        blank=True,
        help_text="Empfängerkategorien (Art. 30 Abs. 1 lit. d)",
    )
    technical_measures = models.ManyToManyField(
        "TechnicalMeasure",
        blank=True,
        help_text="Zugeordnete technische Maßnahmen",
    )
    organizational_measures = models.ManyToManyField(
        "OrganizationalMeasure",
        blank=True,
        help_text="Zugeordnete organisatorische Maßnahmen",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )
    dsfa_required = models.BooleanField(
        default=False,
        help_text="DSFA erforderlich (Art. 35 DSGVO)",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_processing_activity"
        verbose_name = "Verarbeitungstätigkeit"
        verbose_name_plural = "Verarbeitungstätigkeiten"
        ordering = ["mandate", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "name"],
                name="uq_dsb_vvt_name_per_mandate",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "number"],
                name="uq_dsb_vvt_num_per_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_vvt_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}. {self.name}"


class ThirdCountryTransfer(models.Model):
    """Drittlandübermittlung zu einer Verarbeitungstätigkeit (Art. 44ff)."""

    class Safeguard(models.TextChoices):
        SCC = "scc", "Standardvertragsklauseln (SCC)"
        DPF = "dpf", "Data Privacy Framework (DPF)"
        BCR = "bcr", "Binding Corporate Rules (BCR)"
        ADEQUACY = "adequacy", "Angemessenheitsbeschluss"
        CONSENT = "consent", "Einwilligung (Art. 49)"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.CASCADE,
        related_name="third_country_transfers",
    )
    country = models.CharField(
        max_length=100,
        help_text="Zielland (z.B. USA, Indien)",
    )
    recipient_entity = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Empfänger im Drittland (z.B. LinkedIn)",
    )
    safeguard = models.CharField(
        max_length=20,
        choices=Safeguard.choices,
        help_text="Absicherungsmechanismus (Art. 46 DSGVO)",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Ergänzende Hinweise",
    )

    class Meta:
        db_table = "dsb_third_country_transfer"
        verbose_name = "Drittlandübermittlung"
        verbose_name_plural = "Drittlandübermittlungen"
        ordering = ["country"]

    def __str__(self) -> str:
        entity = f" ({self.recipient_entity})" if self.recipient_entity else ""
        return f"{self.country}{entity}"


class RetentionRule(models.Model):
    """Löschfrist/Aufbewahrungsregel einer Verarbeitungstätigkeit."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.CASCADE,
        related_name="retention_rules",
    )
    standard_period = models.ForeignKey(
        StandardRetentionPeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usages",
        help_text="Referenz auf Löschfristen-Stammdaten",
    )
    condition = models.CharField(
        max_length=200,
        help_text="Bedingung (z.B. 'bei fehlender Reaktion')",
    )
    period = models.CharField(
        max_length=100,
        help_text="Frist (z.B. '6-12 Monate', 'unverzüglich')",
    )
    legal_reference = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Gesetzliche Grundlage (z.B. '§ 257 HGB')",
    )

    class Meta:
        db_table = "dsb_retention_rule"
        verbose_name = "Löschfrist"
        verbose_name_plural = "Löschfristen"
        ordering = ["condition"]

    def __str__(self) -> str:
        return f"{self.condition}: {self.period}"
