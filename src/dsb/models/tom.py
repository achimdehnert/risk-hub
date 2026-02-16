"""TOM — Technische und organisatorische Maßnahmen (Art. 32 DSGVO)."""

import uuid

from django.db import models

from .choices import MeasureStatus
from .lookups import TomCategory
from .mandate import Mandate


class TechnicalMeasure(models.Model):
    """Technische Maßnahme gemäß Art. 32 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="technical_measures",
    )
    category = models.ForeignKey(
        TomCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="technical_instances",
        help_text="Referenz auf TOM-Katalog (Stammdaten)",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=MeasureStatus.choices,
        default=MeasureStatus.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_technical_measure"
        verbose_name = "Technische Maßnahme"
        verbose_name_plural = "Technische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_tech_meas_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_tech_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class OrganizationalMeasure(models.Model):
    """Organisatorische Maßnahme gemäß Art. 32 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="organizational_measures",
    )
    category = models.ForeignKey(
        TomCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="organizational_instances",
        help_text="Referenz auf TOM-Katalog (Stammdaten)",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=MeasureStatus.choices,
        default=MeasureStatus.PLANNED,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortliche Person (User-ID)",
    )
    review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächster Überprüfungstermin",
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_organizational_measure"
        verbose_name = "Organisatorische Maßnahme"
        verbose_name_plural = "Organisatorische Maßnahmen"
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "mandate", "title"],
                name="uq_dsb_org_meas_mandate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_org_measure_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title
