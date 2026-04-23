# src/global_sds/models.py
"""
Globale SDS-Stammdaten — tenant-übergreifend (ADR-012).

BigAutoField als PK (Platform-Standard), UUID für externe Referenz/API.
Kein tenant_id auf diesen Models — Sichtbarkeit über QuerySet gesteuert.
"""

import re
import uuid

from django.db import models
from django.db.models import Q

from global_sds.querysets import SdsRevisionQuerySet


def _normalize_cas(cas: str | None) -> str:
    """Remove dashes/spaces from CAS for uniform lookup."""
    if not cas:
        return ""
    return re.sub(r"[\s\-]", "", cas.strip())


# ─────────────────────────────────────────────────────────────────────
# Impact-Klassifizierung (§6.1)
# ─────────────────────────────────────────────────────────────────────


class ImpactLevel(models.TextChoices):
    """Impact-Stufe für SDS-Änderungen."""

    SAFETY_CRITICAL = "SAFETY_CRITICAL", "Safety Critical"
    REGULATORY = "REGULATORY", "Regulatory"
    INFORMATIONAL = "INFORMATIONAL", "Informational"


# ─────────────────────────────────────────────────────────────────────
# SUBSTANCE — Globale Gefahrstoff-Stammdaten
# ─────────────────────────────────────────────────────────────────────


class GlobalSubstance(models.Model):
    """
    Globale Gefahrstoff-Stammdaten.

    CAS ist natürlicher Schlüssel. Kein tenant_id — diese Daten
    sind für alle Tenants identisch (REACH Art. 31).
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    cas_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="CAS Registry Number (z.B. 111-76-2)",
    )
    ec_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="EC/EINECS-Nummer",
    )
    name = models.CharField(
        max_length=512,
        help_text="IUPAC oder gebräuchlicher Name",
    )
    synonyms = models.JSONField(
        default=list,
        blank=True,
        help_text="Alternative Namen (z.B. Handelsnamen)",
    )
    cas_number_normalized = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        editable=False,
        help_text="Auto-normalisierte CAS (ohne Trennzeichen) für Lookup",
    )
    common_name_de = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Gebräuchlicher deutscher Name",
    )
    chemical_formula = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "global_sds_substance"
        verbose_name = "Globale Substanz"
        verbose_name_plural = "Globale Substanzen"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["cas_number_normalized"],
                name="uq_substance_cas_normalized",
                condition=Q(cas_number_normalized__gt=""),
            ),
        ]

    def save(self, *args, **kwargs):
        self.cas_number_normalized = _normalize_cas(self.cas_number)
        super().save(*args, **kwargs)

    def __str__(self):
        cas = f" (CAS {self.cas_number})" if self.cas_number else ""
        return f"{self.name}{cas}"


# ─────────────────────────────────────────────────────────────────────
# SDS REVISION — Versioniertes Sicherheitsdatenblatt
# ─────────────────────────────────────────────────────────────────────


class GlobalSdsRevision(models.Model):
    """
    Versioniertes SDS — global, SHA-256 als Idempotenz-Key.

    Status-Flow: PENDING → VERIFIED → SUPERSEDED
    PENDING: nur für hochladenden Tenant sichtbar.
    VERIFIED: global sichtbar für alle Tenants.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Ausstehend (nur Uploader)"
        VERIFIED = "VERIFIED", "Verifiziert (global)"
        REJECTED = "REJECTED", "Abgelehnt"
        SUPERSEDED = "SUPERSEDED", "Abgelöst"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    substance = models.ForeignKey(
        GlobalSubstance,
        on_delete=models.PROTECT,
        related_name="revisions",
    )
    source_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 des Original-PDFs (Idempotenz)",
    )
    superseded_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supersedes",
    )
    pdf_file = models.FileField(
        upload_to="sds/pdfs/",
        null=True,
        blank=True,
        help_text="Original-PDF (BetrSichV Archivierungspflicht)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    uploaded_by_tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant der dieses SDS hochgeladen hat",
    )

    # Metadaten (aus PDF extrahiert)
    manufacturer_name = models.CharField(
        max_length=256,
        blank=True,
        default="",
    )
    product_name = models.CharField(max_length=512)
    revision_date = models.DateField(
        null=True,
        blank=True,
        help_text="Revisionsdatum des SDS",
    )
    version_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    # Regulatorisch (SDS Abschnitt 15)
    wgk = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Wassergefährdungsklasse (1-3)",
    )
    storage_class_trgs510 = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text="Lagerklasse nach TRGS 510",
    )
    voc_percent = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    voc_g_per_l = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Ex-relevant (SDS Abschnitt 9)
    flash_point_c = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Flammpunkt in °C",
    )
    ignition_temperature_c = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Zündtemperatur in °C",
    )
    lower_explosion_limit = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="UEG in Vol.%",
    )
    upper_explosion_limit = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="OEG in Vol.%",
    )

    # Parser-Qualität
    parse_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Gesamt-Konfidenz des Regex-Parsers (0.0-1.0)",
    )
    llm_corrections = models.JSONField(
        default=list,
        blank=True,
        help_text="Audit-Trail der LLM-Korrekturen",
    )

    # CLP/GHS (SDS Abschnitt 2)
    signal_word = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )
    hazard_statements = models.ManyToManyField(
        "substances.HazardStatementRef",
        blank=True,
        related_name="global_sds_revisions",
    )
    precautionary_statements = models.ManyToManyField(
        "substances.PrecautionaryStatementRef",
        blank=True,
        related_name="global_sds_revisions",
    )
    pictograms = models.ManyToManyField(
        "substances.PictogramRef",
        blank=True,
        related_name="global_sds_revisions",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SdsRevisionQuerySet.as_manager()

    class Meta:
        db_table = "global_sds_sdsrevision"
        verbose_name = "Globale SDS-Revision"
        verbose_name_plural = "Globale SDS-Revisionen"
        ordering = ["-revision_date", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(superseded_by=models.F("id")),
                name="chk_sdsrevision_no_self_supersession",
            ),
        ]
        indexes = [
            models.Index(
                fields=["source_hash"],
                name="ix_global_sds_source_hash",
            ),
            models.Index(
                fields=["status", "uploaded_by_tenant_id"],
                name="ix_global_sds_status_tenant",
            ),
        ]

    def __str__(self):
        ver = f" v{self.version_number}" if self.version_number else ""
        return f"{self.product_name}{ver} ({self.get_status_display()})"

    @property
    def is_current(self) -> bool:
        """True wenn verifiziert und nicht abgelöst."""
        return self.superseded_by_id is None and self.status == self.Status.VERIFIED


# ─────────────────────────────────────────────────────────────────────
# SDS COMPONENT — Inhaltsstoffe (Abschnitt 3.2)
# ─────────────────────────────────────────────────────────────────────


class GlobalSdsComponent(models.Model):
    """Inhaltsstoff eines Gemischs (SDS Abschnitt 3.2). Global."""

    sds_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.CASCADE,
        related_name="components",
    )
    chemical_name = models.CharField(max_length=512)
    cas_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
    )
    ec_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )
    concentration_min = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Untere Konzentrationsgrenze (%)",
    )
    concentration_max = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Obere Konzentrationsgrenze (%)",
    )
    concentration_note = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    hazard_statements = models.ManyToManyField(
        "substances.HazardStatementRef",
        blank=True,
        related_name="global_sds_components",
    )
    m_factor_acute = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="M-Faktor (akut)",
    )
    m_factor_chronic = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="M-Faktor (chronisch)",
    )

    class Meta:
        db_table = "global_sds_sdscomponent"
        verbose_name = "SDS-Inhaltsstoff"
        verbose_name_plural = "SDS-Inhaltsstoffe"

    def __str__(self):
        cas = f" (CAS {self.cas_number})" if self.cas_number else ""
        return f"{self.chemical_name}{cas}"


# ─────────────────────────────────────────────────────────────────────
# EXPOSURE LIMIT — AGW/DNEL/PNEC (Abschnitt 8.1)
# ─────────────────────────────────────────────────────────────────────


class GlobalSdsExposureLimit(models.Model):
    """AGW/DNEL/PNEC pro Inhaltsstoff (Abschnitt 8.1). Global."""

    class LimitType(models.TextChoices):
        AGW = "AGW", "Arbeitsplatzgrenzwert (TRGS 900)"
        STEL = "STEL", "Kurzzeitgrenzwert"
        TWA = "TWA", "Zeitgewichteter Mittelwert"
        BGW = "BGW", "Biologischer Grenzwert (TRGS 903)"
        DNEL_WORKER = "DNEL_W", "DNEL Arbeitnehmer"
        DNEL_CONSUMER = "DNEL_C", "DNEL Verbraucher"
        PNEC = "PNEC", "PNEC Umwelt"

    class ExposureRoute(models.TextChoices):
        INHALATION = "INH", "Einatmung"
        DERMAL = "DERM", "Haut"
        ORAL = "ORAL", "Oral"
        FRESH_WATER = "FW", "Süßwasser"
        MARINE = "MW", "Meerwasser"
        SOIL = "SOIL", "Boden"
        STP = "STP", "Abwasserkläranlage"

    component = models.ForeignKey(
        GlobalSdsComponent,
        on_delete=models.CASCADE,
        related_name="exposure_limits",
        null=True,
        blank=True,
    )
    sds_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.CASCADE,
        related_name="exposure_limits",
    )
    limit_type = models.CharField(
        max_length=10,
        choices=LimitType.choices,
    )
    route = models.CharField(
        max_length=10,
        choices=ExposureRoute.choices,
    )
    value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=40)
    effect_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )
    basis = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Rechtsgrundlage (z.B. TRGS 900)",
    )

    class Meta:
        db_table = "global_sds_sdsexposurelimit"
        verbose_name = "Expositionsgrenzwert"
        verbose_name_plural = "Expositionsgrenzwerte"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "sds_revision",
                    "component",
                    "limit_type",
                    "route",
                ],
                name="uq_exposure_limit_per_component_route",
            ),
        ]

    def __str__(self):
        return f"{self.get_limit_type_display()} {self.value} {self.unit}"


# ─────────────────────────────────────────────────────────────────────
# REVISION DIFF RECORD — Persistierter Diff (§6 M-1)
# ─────────────────────────────────────────────────────────────────────


class SdsRevisionDiffRecord(models.Model):
    """
    Persistierter Diff zwischen zwei globalen Revisionen (M-1).

    Wird beim Supersede einmalig durch SdsRevisionDiffService angelegt.
    Immutable nach Anlage — kein UPDATE erlaubt.
    Ermöglicht Audit-Trail: In 5 Jahren nachvollziehbar warum
    GBU-Review nötig war.
    """

    old_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.PROTECT,
        related_name="diffs_as_old",
    )
    new_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.PROTECT,
        related_name="diffs_as_new",
    )
    overall_impact = models.CharField(
        max_length=20,
        choices=ImpactLevel.choices,
    )
    field_diffs = models.JSONField(
        help_text="Serialisierte FieldDiff-Liste",
    )
    added_h_codes = models.JSONField(default=list)
    removed_h_codes = models.JSONField(default=list)
    changed_components = models.JSONField(default=list)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "global_sds_revisiondiff"
        verbose_name = "SDS-Revisions-Diff"
        verbose_name_plural = "SDS-Revisions-Diffs"
        constraints = [
            models.UniqueConstraint(
                fields=["old_revision", "new_revision"],
                name="uq_diff_per_revision_pair",
            ),
        ]

    @property
    def requires_gbu_review(self) -> bool:
        """True wenn GBU-Review nötig (H-Codes geändert oder Safety Critical)."""
        return (
            self.overall_impact == ImpactLevel.SAFETY_CRITICAL
            or bool(self.added_h_codes)
            or bool(self.removed_h_codes)
        )

    @property
    def requires_ex_review(self) -> bool:
        """True wenn Ex-Review nötig (Ex-relevante Felder geändert)."""
        ex_fields = {
            "flash_point_c",
            "ignition_temperature_c",
            "lower_explosion_limit",
            "upper_explosion_limit",
        }
        for diff in self.field_diffs or []:
            if isinstance(diff, dict) and diff.get("field") in ex_fields:
                return True
        return self.overall_impact == ImpactLevel.SAFETY_CRITICAL

    def __str__(self):
        return f"Diff {self.old_revision_id} → {self.new_revision_id} ({self.overall_impact})"


# ─────────────────────────────────────────────────────────────────────
# SDS PROPERTY DEFINITION — DB-Katalog aller SDS-Eigenschaften (§5.3)
# ─────────────────────────────────────────────────────────────────────


class SdsPropertyDefinition(models.Model):
    """
    DB-Katalog aller SDS-Eigenschaften (Abschnitt 9 etc.).

    Ermöglicht dynamische Erweiterung ohne Schema-Migration.
    Definiert ValueType, Extraction-Patterns und Promotion-Pfad.
    """

    class ValueType(models.TextChoices):
        NUMERIC = "NUMERIC", "Numerisch (Einzelwert)"
        NUMERIC_RANGE = "NUMERIC_RANGE", "Numerisch (Bereich)"
        NUMERIC_AT_TEMP = "NUMERIC_AT_TEMP", "Numerisch bei Temperatur"
        BOOLEAN = "BOOLEAN", "Boolean"
        ENUM = "ENUM", "Enum (Auswahlliste)"
        TEXT = "TEXT", "Freitext"

    key = models.CharField(
        max_length=100,
        unique=True,
        help_text="Interner Schlüssel (z.B. 'flash_point', 'density')",
    )
    label_de = models.CharField(max_length=200, help_text="Deutscher Anzeigename")
    label_en = models.CharField(max_length=200, blank=True, default="")
    sds_section = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="SDS-Abschnitt (z.B. '9.1', '14.1')",
    )
    value_type = models.CharField(
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.NUMERIC,
    )
    unit = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Standard-Einheit (z.B. '°C', 'mg/m³')",
    )
    extraction_patterns = models.JSONField(
        default=list,
        blank=True,
        help_text="Regex-Patterns für Parser [{pattern, group, transform}]",
    )
    is_promoted = models.BooleanField(
        default=False,
        help_text="True wenn als dedizierte Spalte auf SdsRevision existiert",
    )
    promoted_column_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Spaltenname auf GlobalSdsRevision (wenn promoted)",
    )
    coverage_percent = models.FloatField(
        default=0.0,
        help_text="Anteil der Revisionen mit diesem Property (%)",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "global_sds_propertydefinition"
        verbose_name = "SDS-Eigenschaftsdefinition"
        verbose_name_plural = "SDS-Eigenschaftsdefinitionen"
        ordering = ["sort_order", "key"]

    def __str__(self):
        return f"{self.key} ({self.get_value_type_display()})"


class SdsRevisionProperty(models.Model):
    """
    Typisierter Key-Value-Store für SDS-Revision-Eigenschaften.

    Ergänzt promoted Felder auf GlobalSdsRevision um dynamische
    Eigenschaften ohne Schema-Migration.
    """

    sds_revision = models.ForeignKey(
        GlobalSdsRevision,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    definition = models.ForeignKey(
        SdsPropertyDefinition,
        on_delete=models.PROTECT,
        related_name="values",
    )
    value_numeric_lo = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Unterer Wert (oder Einzelwert)",
    )
    value_numeric_hi = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Oberer Wert (bei Bereich)",
    )
    value_text = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Textwert (bei ENUM/TEXT/BOOLEAN)",
    )
    raw_text = models.TextField(
        blank=True,
        default="",
        help_text="Original-Text aus dem SDS (für Audit/Suche)",
    )
    confidence = models.FloatField(
        default=1.0,
        help_text="Konfidenz des Parsers (0.0-1.0)",
    )
    parse_source = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Extraktionsquelle (regex, llm, manual)",
    )
    temperature_c = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bezugstemperatur (bei NUMERIC_AT_TEMP)",
    )

    class Meta:
        db_table = "global_sds_revisionproperty"
        verbose_name = "SDS-Revisions-Eigenschaft"
        verbose_name_plural = "SDS-Revisions-Eigenschaften"
        constraints = [
            models.UniqueConstraint(
                fields=["sds_revision", "definition"],
                name="uq_revision_property_per_def",
            ),
        ]
        indexes = [
            models.Index(
                fields=["definition", "value_numeric_lo"],
                name="ix_revprop_def_numeric",
            ),
        ]

    def __str__(self):
        return f"{self.definition.key}: {self.value_numeric_lo or self.value_text}"
