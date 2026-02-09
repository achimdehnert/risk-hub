# src/substances/models.py
"""
Datenmodelle für Gefahrstoff- und SDS-Management.

Enthält:
- Party (Hersteller/Lieferant)
- Substance (Gefahrstoff)
- Identifier (CAS, UFI, EC)
- SdsRevision (Sicherheitsdatenblatt-Version)
- SiteInventoryItem (Standort-Inventar)
- Referenztabellen (H-/P-Sätze, Piktogramme)
"""

import uuid
from django.db import models


# =============================================================================
# BASE CLASS (Tenant-Scoped)
# =============================================================================

class TenantScopedModel(models.Model):
    """Abstrakte Basisklasse für tenant-isolierte Models."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Tenant-ID für Mandantentrennung"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    class Meta:
        abstract = True


# =============================================================================
# PARTY (Hersteller / Lieferant)
# =============================================================================

class Party(TenantScopedModel):
    """Hersteller oder Lieferant von Gefahrstoffen."""

    class PartyType(models.TextChoices):
        MANUFACTURER = "manufacturer", "Hersteller"
        SUPPLIER = "supplier", "Lieferant"

    name = models.CharField(max_length=240, help_text="Firmenname")
    party_type = models.CharField(
        max_length=20,
        choices=PartyType.choices,
        help_text="Typ der Partei"
    )
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    address = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, default="")

    class Meta:
        db_table = "substances_party"
        verbose_name = "Partei"
        verbose_name_plural = "Parteien"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "party_type", "name"],
                name="uq_party_tenant_type_name"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "party_type"],
                name="ix_party_tenant_type"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"


# =============================================================================
# SUBSTANCE (Gefahrstoff)
# =============================================================================

class Substance(TenantScopedModel):
    """Gefahrstoff / Chemisches Produkt."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Inaktiv"
        ARCHIVED = "archived", "Archiviert"

    class StorageClass(models.TextChoices):
        """Lagerklassen nach TRGS 510."""
        SC_1 = "1", "1 - Explosive Stoffe"
        SC_2A = "2A", "2A - Verdichtete Gase"
        SC_2B = "2B", "2B - Druckgaspackungen"
        SC_3 = "3", "3 - Entzündbare Flüssigkeiten"
        SC_4_1A = "4.1A", "4.1A - Selbstzersetzliche Stoffe"
        SC_4_1B = "4.1B", "4.1B - Desensibilisierte explosive Stoffe"
        SC_4_2 = "4.2", "4.2 - Pyrophore/selbsterhitzungsfähige Stoffe"
        SC_4_3 = "4.3", "4.3 - Stoffe, die mit Wasser reagieren"
        SC_5_1A = "5.1A", "5.1A - Stark oxidierende Stoffe"
        SC_5_1B = "5.1B", "5.1B - Oxidierende Stoffe"
        SC_5_1C = "5.1C", "5.1C - Ammoniumnitrat"
        SC_5_2 = "5.2", "5.2 - Organische Peroxide"
        SC_6_1A = "6.1A", "6.1A - Brennbare akut toxische Stoffe"
        SC_6_1B = "6.1B", "6.1B - Nicht brennbare akut toxische Stoffe"
        SC_6_1C = "6.1C", "6.1C - Brennbare chronisch toxische Stoffe"
        SC_6_1D = "6.1D", "6.1D - Nicht brennbare chronisch toxische"
        SC_6_2 = "6.2", "6.2 - Ansteckungsgefährliche Stoffe"
        SC_7 = "7", "7 - Radioaktive Stoffe"
        SC_8A = "8A", "8A - Brennbare ätzende Stoffe"
        SC_8B = "8B", "8B - Nicht brennbare ätzende Stoffe"
        SC_10 = "10", "10 - Brennbare Flüssigkeiten (nicht LGK 3)"
        SC_11 = "11", "11 - Brennbare Feststoffe"
        SC_12 = "12", "12 - Nicht brennbare Flüssigkeiten"
        SC_13 = "13", "13 - Nicht brennbare Feststoffe"

    # Stammdaten
    name = models.CharField(
        max_length=240,
        help_text="Stoffname / Produktbezeichnung"
    )
    trade_name = models.CharField(
        max_length=240,
        blank=True,
        default="",
        help_text="Handelsname"
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung / Verwendungszweck"
    )

    # Klassifikation
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    storage_class = models.CharField(
        max_length=10,
        choices=StorageClass.choices,
        blank=True,
        default="",
        help_text="Lagerklasse nach TRGS 510"
    )
    is_cmr = models.BooleanField(
        default=False,
        help_text="CMR-Stoff (karzinogen, mutagen, reproduktionstoxisch)"
    )

    # Beziehungen
    manufacturer = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufactured_substances",
        limit_choices_to={"party_type": "manufacturer"}
    )
    supplier = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_substances",
        limit_choices_to={"party_type": "supplier"}
    )

    # Ex-Schutz-relevante Daten (aus SDS extrahiert)
    flash_point_c = models.FloatField(
        null=True,
        blank=True,
        help_text="Flammpunkt in °C"
    )
    ignition_temperature_c = models.FloatField(
        null=True,
        blank=True,
        help_text="Zündtemperatur in °C"
    )
    lower_explosion_limit = models.FloatField(
        null=True,
        blank=True,
        help_text="Untere Explosionsgrenze (UEG) in Vol.%"
    )
    upper_explosion_limit = models.FloatField(
        null=True,
        blank=True,
        help_text="Obere Explosionsgrenze (OEG) in Vol.%"
    )
    temperature_class = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Temperaturklasse (T1-T6)"
    )
    explosion_group = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Explosionsgruppe (IIA, IIB, IIC)"
    )
    vapor_density = models.FloatField(
        null=True,
        blank=True,
        help_text="Dampfdichte (Luft = 1)"
    )

    class Meta:
        db_table = "substances_substance"
        verbose_name = "Gefahrstoff"
        verbose_name_plural = "Gefahrstoffe"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_substance_tenant_name"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_substance_tenant_status"
            ),
            models.Index(
                fields=["tenant_id", "is_cmr"],
                name="ix_substance_tenant_cmr"
            ),
            models.Index(fields=["name"], name="ix_substance_name"),
        ]

    def __str__(self):
        return self.name

    @property
    def current_sds(self):
        """Aktuell gültige SDS-Revision (approved, neueste)."""
        return self.sds_revisions.filter(
            status=SdsRevision.Status.APPROVED
        ).order_by("-revision_number").first()

    @property
    def cas_number(self):
        """CAS-Nummer (falls vorhanden)."""
        identifier = self.identifiers.filter(
            id_type=Identifier.IdType.CAS
        ).first()
        return identifier.id_value if identifier else None


# =============================================================================
# IDENTIFIER (Stoffkennungen)
# =============================================================================

class Identifier(TenantScopedModel):
    """Stoffkennungen (CAS, EC, UFI, intern)."""

    class IdType(models.TextChoices):
        CAS = "cas", "CAS-Nummer"
        EC = "ec", "EC-Nummer"
        UFI = "ufi", "UFI-Code"
        GTIN = "gtin", "GTIN/EAN"
        INTERNAL = "internal", "Interne Nummer"
        INDEX = "index", "Index-Nummer"
        REACH = "reach", "REACH-Registrierungsnr."

    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="identifiers"
    )
    id_type = models.CharField(max_length=20, choices=IdType.choices)
    id_value = models.CharField(max_length=100)

    class Meta:
        db_table = "substances_identifier"
        verbose_name = "Stoffkennung"
        verbose_name_plural = "Stoffkennungen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "substance", "id_type"],
                name="uq_identifier_substance_type"
            ),
        ]

    def __str__(self):
        return f"{self.get_id_type_display()}: {self.id_value}"


# =============================================================================
# SDS REVISION (Sicherheitsdatenblatt)
# =============================================================================

class SdsRevision(TenantScopedModel):
    """Sicherheitsdatenblatt-Revision."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        PENDING = "pending", "Zur Freigabe"
        APPROVED = "approved", "Freigegeben"
        ARCHIVED = "archived", "Archiviert"

    class SignalWord(models.TextChoices):
        DANGER = "danger", "Gefahr"
        WARNING = "warning", "Achtung"
        NONE = "none", "Kein Signalwort"

    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="sds_revisions"
    )

    # Versionierung
    revision_number = models.PositiveIntegerField(default=1)
    revision_date = models.DateField(help_text="Datum des SDS")

    # Dokument (FK zu documents-Modul)
    document = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Verknüpftes PDF-Dokument"
    )

    # Klassifikation
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    signal_word = models.CharField(
        max_length=20,
        choices=SignalWord.choices,
        default=SignalWord.NONE
    )

    # H-/P-Sätze (ManyToMany zu Referenztabellen)
    hazard_statements = models.ManyToManyField(
        "HazardStatementRef",
        blank=True,
        related_name="sds_revisions"
    )
    precautionary_statements = models.ManyToManyField(
        "PrecautionaryStatementRef",
        blank=True,
        related_name="sds_revisions"
    )
    pictograms = models.ManyToManyField(
        "PictogramRef",
        blank=True,
        related_name="sds_revisions"
    )

    # Freigabe
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "substances_sds_revision"
        verbose_name = "SDS-Revision"
        verbose_name_plural = "SDS-Revisionen"
        ordering = ["-revision_date", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["substance", "revision_number"],
                name="uq_sds_substance_revision"
            ),
        ]

    def __str__(self):
        return f"{self.substance.name} - Rev. {self.revision_number}"


# =============================================================================
# SITE INVENTORY (Standort-Inventar)
# =============================================================================

class SiteInventoryItem(TenantScopedModel):
    """Standort-Inventar: Welcher Stoff wo und wieviel."""

    class State(models.TextChoices):
        SOLID = "solid", "Fest"
        LIQUID = "liquid", "Flüssig"
        GAS = "gas", "Gasförmig"

    substance = models.ForeignKey(
        Substance,
        on_delete=models.CASCADE,
        related_name="inventory_items"
    )
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="substance_inventory"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Menge"
    )
    unit = models.CharField(
        max_length=20,
        default="kg",
        help_text="Einheit (kg, l, m³)"
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.LIQUID,
        help_text="Aggregatzustand"
    )
    storage_location = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Lagerort (z.B. Gefahrstofflager A)"
    )
    responsible_user = models.UUIDField(
        null=True,
        blank=True,
        help_text="Verantwortliche Person"
    )

    class Meta:
        db_table = "substances_site_inventory"
        verbose_name = "Standort-Inventar"
        verbose_name_plural = "Standort-Inventar"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "substance", "storage_location"],
                name="uq_inventory_site_substance_location"
            ),
        ]

    def __str__(self):
        return f"{self.substance.name} @ {self.site} ({self.quantity} {self.unit})"


# =============================================================================
# REFERENZTABELLEN (Global, nicht tenant-spezifisch)
# =============================================================================

class HazardStatementRef(models.Model):
    """H-Sätze Referenztabelle (GHS)."""

    code = models.CharField(
        max_length=10,
        primary_key=True,
        help_text="H-Code (z.B. H225)"
    )
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="English text")
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Kategorie (physikalisch, Gesundheit, Umwelt)"
    )

    class Meta:
        db_table = "substances_ref_hazard_statement"
        verbose_name = "H-Satz (Referenz)"
        verbose_name_plural = "H-Sätze (Referenz)"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.text_de[:50]}..."


class PrecautionaryStatementRef(models.Model):
    """P-Sätze Referenztabelle (GHS)."""

    code = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="P-Code (z.B. P210, P210+P233)"
    )
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="English text")
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Kategorie (Prävention, Reaktion, Lagerung, Entsorgung)"
    )

    class Meta:
        db_table = "substances_ref_precautionary_statement"
        verbose_name = "P-Satz (Referenz)"
        verbose_name_plural = "P-Sätze (Referenz)"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.text_de[:50]}..."


class PictogramRef(models.Model):
    """GHS-Piktogramme Referenztabelle."""

    code = models.CharField(
        max_length=10,
        primary_key=True,
        help_text="GHS-Code (z.B. GHS01)"
    )
    name_de = models.CharField(max_length=100, help_text="Deutscher Name")
    name_en = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="English name"
    )
    svg_path = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Pfad zur SVG-Datei"
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung der Gefahr"
    )

    class Meta:
        db_table = "substances_ref_pictogram"
        verbose_name = "Piktogramm (Referenz)"
        verbose_name_plural = "Piktogramme (Referenz)"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.name_de}"


# =============================================================================
# HAZARDOUS SUBSTANCE REGISTRY (TRGS 510 / Seveso III)
# NOTE: Standalone StorageClass removed (Finding 4a).
# Use Substance.StorageClass for all storage class references.
# =============================================================================


class SevesoCategory(models.TextChoices):
    """Seveso III Kategorien (12. BImSchV)."""

    NONE = "none", "Nicht Seveso-relevant"
    LOWER = "lower", "Untere Klasse (Grundpflichten)"
    UPPER = "upper", "Obere Klasse (Erweiterte Pflichten)"


class LocationSubstanceEntry(TenantScopedModel):
    """
    Hazardous substance stored at a specific location.

    Tracks quantities, TRGS 510 storage classes, and
    Seveso III relevance per tenant location.
    """

    area_id = models.UUIDField(
        db_index=True,
        help_text="Standort/Bereich (Area-ID)",
    )
    substance = models.ForeignKey(
        Substance,
        on_delete=models.PROTECT,
        related_name="location_entries",
    )
    substance_name = models.CharField(
        max_length=300,
        help_text="Denormalisierter Stoffname",
    )
    cas_number = models.CharField(
        max_length=30, blank=True, default="",
    )

    # Quantities
    max_quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Maximale Lagermenge in kg",
    )
    current_quantity_kg = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Aktuelle Lagermenge in kg",
    )

    # TRGS 510
    storage_class = models.CharField(
        max_length=10,
        choices=Substance.StorageClass.choices,
        blank=True, default="",
        db_index=True,
    )

    # Seveso III
    seveso_category = models.CharField(
        max_length=10,
        choices=SevesoCategory.choices,
        default=SevesoCategory.NONE,
        db_index=True,
    )
    seveso_threshold_lower_t = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Untere Mengenschwelle (Tonnen)",
    )
    seveso_threshold_upper_t = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Obere Mengenschwelle (Tonnen)",
    )

    # GHS
    h_statements = models.TextField(
        blank=True, default="",
    )
    ghs_pictograms = models.CharField(
        max_length=200, blank=True, default="",
    )

    notes = models.TextField(blank=True, default="")
    last_inventory_date = models.DateField(
        null=True, blank=True,
    )

    class Meta:
        db_table = "substances_location_entry"
        ordering = ["substance_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "area_id", "substance_id"],
                name="uq_location_substance",
            ),
        ]

    def __str__(self):
        return (
            f"{self.substance_name}"
            f" ({self.current_quantity_kg} kg)"
        )

    @property
    def seveso_utilization_pct(self) -> float | None:
        """Seveso threshold utilization percentage."""
        thr = self.seveso_threshold_lower_t
        if not thr or thr == 0:
            return None
        qty_t = float(self.current_quantity_kg) / 1000
        return round(qty_t / float(thr) * 100, 1)
