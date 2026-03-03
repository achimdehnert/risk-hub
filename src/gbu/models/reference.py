"""
Globale Referenzdaten für GBU-Automation (tenant-unabhängig).

HazardCategoryRef    — Gefährdungskategorien nach TRGS 400
HCodeCategoryMapping — H-Code → Kategorie (admin-pflegbar, idempotent seeded)
MeasureTemplate      — TOPS-Schutzmaßnahmen-Vorlagen
"""
from enum import StrEnum

from django.db import models


class HazardCategoryType(StrEnum):
    FIRE_EXPLOSION = "fire_explosion"
    ACUTE_TOXIC = "acute_toxic"
    CHRONIC_TOXIC = "chronic_toxic"
    SKIN_CORROSION = "skin_corrosion"
    EYE_DAMAGE = "eye_damage"
    RESPIRATORY = "respiratory"
    SKIN_SENS = "skin_sens"
    CMR = "cmr"
    ENVIRONMENT = "environment"
    ASPHYXIANT = "asphyxiant"


class TOPSType(StrEnum):
    SUBSTITUTION = "S"
    TECHNICAL = "T"
    ORGANISATIONAL = "O"
    PERSONAL = "P"


class HazardCategoryRef(models.Model):
    """Gefährdungskategorie nach TRGS 400 — global, tenant-unabhängig."""

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    category_type = models.CharField(
        max_length=30,
        choices=[(t.value, t.value) for t in HazardCategoryType],
        db_index=True,
    )
    trgs_reference = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="z.B. 'TRGS 400 Abschnitt 5.3'",
    )
    description = models.TextField(blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_hazard_category_ref"
        ordering = ["category_type", "sort_order", "name"]
        verbose_name = "Gefährdungskategorie"
        verbose_name_plural = "Gefährdungskategorien"

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class HCodeCategoryMapping(models.Model):
    """H-Code → Gefährdungskategorie (n:m, datenbankgetrieben, admin-pflegbar)."""

    h_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="z.B. 'H220', 'H301'",
    )
    category = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,
        related_name="h_code_mappings",
    )
    annotation = models.TextField(
        blank=True,
        default="",
        help_text="Begründung / TRGS-Verweis",
    )

    class Meta:
        db_table = "gbu_h_code_category_mapping"
        unique_together = [("h_code", "category")]
        verbose_name = "H-Code Mapping"
        verbose_name_plural = "H-Code Mappings"
        ordering = ["h_code"]

    def __str__(self) -> str:
        return f"{self.h_code} → {self.category.code}"


class MeasureTemplate(models.Model):
    """TOPS-Schutzmaßnahmen-Vorlage, verknüpft mit Gefährdungskategorie."""

    category = models.ForeignKey(
        HazardCategoryRef,
        on_delete=models.CASCADE,
        related_name="measure_templates",
    )
    tops_type = models.CharField(
        max_length=1,
        choices=[(t.value, t.name.title()) for t in TOPSType],
        db_index=True,
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    legal_basis = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="z.B. 'GefStoffV §7, TRGS 500'",
    )
    is_mandatory = models.BooleanField(
        default=False,
        help_text="Pflichtmaßnahme (keine Ablehnung möglich)",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "gbu_measure_template"
        ordering = ["tops_type", "sort_order"]
        verbose_name = "Maßnahmen-Vorlage"
        verbose_name_plural = "Maßnahmen-Vorlagen"

    def __str__(self) -> str:
        return f"[{self.tops_type}] {self.title}"
