# src/substances/models.py
"""
Datenmodelle für Gefahrstoff- und SDS-Management.

Enthält:
- Party (Hersteller/Lieferant)
- Substance (Gefahrstoff) — Legacy, wird langfristig durch Product ersetzt
- Identifier (CAS, UFI, EC)
- SdsRevision (Sicherheitsdatenblatt-Version)
- SiteInventoryItem (Standort-Inventar) — Legacy, wird durch SubstanceUsage ersetzt
- Referenztabellen (H-/P-Sätze, Piktogramme)
- Product (Handelsprodukt, UC-004)
- ProductComponent (Inhaltsstoffe eines Produkts, UC-004)
- SubstanceUsage (Produkt × Standort × Abteilung, UC-004)
- ImportBatch / ImportRow (Excel-Import, UC-004)
- RPhrase / SPhrase (Legacy R/S-Satz → H/P-Satz Mapping)
- SdsChangeLog (Diff zwischen SDS-Revisionen, UC-005)
- ComplianceReview (Periodisches Prüfprotokoll, UC-006)
- KatasterRevision (Versionierter Kataster-Snapshot, UC-007)
"""

import hashlib

from django.db import models
from django_tenancy.managers import TenantManager

# =============================================================================
# BASE CLASS (Tenant-Scoped)
# =============================================================================


class TenantScopedModel(models.Model):
    """Abstrakte Basisklasse für tenant-isolierte Models."""

    tenant_id = models.UUIDField(db_index=True, help_text="Tenant-ID für Mandantentrennung")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)

    objects = TenantManager()

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
        max_length=20, choices=PartyType.choices, help_text="Typ der Partei"
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
                fields=["tenant_id", "party_type", "name"], name="uq_party_tenant_type_name"
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "party_type"], name="ix_party_tenant_type"),
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
    name = models.CharField(max_length=240, help_text="Stoffname / Produktbezeichnung")
    trade_name = models.CharField(max_length=240, blank=True, default="", help_text="Handelsname")
    description = models.TextField(
        blank=True, default="", help_text="Beschreibung / Verwendungszweck"
    )

    # Klassifikation
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    storage_class = models.CharField(
        max_length=10,
        choices=StorageClass.choices,
        blank=True,
        default="",
        help_text="Lagerklasse nach TRGS 510",
    )
    is_cmr = models.BooleanField(
        default=False, help_text="CMR-Stoff (karzinogen, mutagen, reproduktionstoxisch)"
    )

    # Beziehungen
    manufacturer = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manufactured_substances",
        limit_choices_to={"party_type": "manufacturer"},
    )
    supplier = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_substances",
        limit_choices_to={"party_type": "supplier"},
    )

    # Ex-Schutz-relevante Daten (aus SDS extrahiert)
    flash_point_c = models.FloatField(null=True, blank=True, help_text="Flammpunkt in °C")
    ignition_temperature_c = models.FloatField(
        null=True, blank=True, help_text="Zündtemperatur in °C"
    )
    lower_explosion_limit = models.FloatField(
        null=True, blank=True, help_text="Untere Explosionsgrenze (UEG) in Vol.%"
    )
    upper_explosion_limit = models.FloatField(
        null=True, blank=True, help_text="Obere Explosionsgrenze (OEG) in Vol.%"
    )
    temperature_class = models.CharField(
        max_length=10, blank=True, default="", help_text="Temperaturklasse (T1-T6)"
    )
    explosion_group = models.CharField(
        max_length=10, blank=True, default="", help_text="Explosionsgruppe (IIA, IIB, IIC)"
    )
    vapor_density = models.FloatField(null=True, blank=True, help_text="Dampfdichte (Luft = 1)")

    # Physikalische Daten (GESTIS)
    boiling_point_c = models.FloatField(null=True, blank=True, help_text="Siedepunkt in °C")
    melting_point_c = models.FloatField(null=True, blank=True, help_text="Schmelzpunkt in °C")
    density = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Dichte (z.B. 0,79 g/cm³)",
    )
    molecular_formula = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Summenformel",
    )
    molecular_weight = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Molare Masse",
    )

    # Arbeitsschutz (GESTIS)
    agw = models.TextField(
        blank=True,
        default="",
        help_text="Arbeitsplatzgrenzwert (TRGS 900)",
    )
    wgk = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Wassergefährdungsklasse",
    )

    # Schutzmaßnahmen (GESTIS)
    first_aid = models.TextField(
        blank=True,
        default="",
        help_text="Erste Hilfe",
    )
    protective_measures = models.TextField(
        blank=True,
        default="",
        help_text="Technische + persönliche Schutzmaßnahmen",
    )
    storage_info = models.TextField(
        blank=True,
        default="",
        help_text="Lagerung (GESTIS)",
    )
    fire_protection = models.TextField(
        blank=True,
        default="",
        help_text="Brand- und Explosionsschutz",
    )
    disposal = models.TextField(
        blank=True,
        default="",
        help_text="Entsorgung",
    )
    spill_response = models.TextField(
        blank=True,
        default="",
        help_text="Maßnahmen bei Freisetzung",
    )

    # Vorschriften (GESTIS)
    regulations = models.TextField(
        blank=True,
        default="",
        help_text="Vorschriften/Regelwerke (JSON-Liste)",
    )

    # GESTIS-Referenz
    gestis_zvg = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="GESTIS ZVG-Nummer",
    )
    gestis_url = models.URLField(
        blank=True,
        default="",
        help_text="GESTIS Volltext-Link",
    )

    class Meta:
        db_table = "substances_substance"
        verbose_name = "Gefahrstoff"
        verbose_name_plural = "Gefahrstoffe"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "name"], name="uq_substance_tenant_name"),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="ix_substance_tenant_status"),
            models.Index(fields=["tenant_id", "is_cmr"], name="ix_substance_tenant_cmr"),
            models.Index(fields=["name"], name="ix_substance_name"),
        ]

    def __str__(self):
        return self.name

    @property
    def current_sds(self):
        """Aktuell gültige SDS-Revision (approved, neueste)."""
        return (
            self.sds_revisions.filter(status=SdsRevision.Status.APPROVED)
            .order_by("-revision_number")
            .first()
        )

    @property
    def cas_number(self):
        """CAS-Nummer (falls vorhanden)."""
        identifier = self.identifiers.filter(id_type=Identifier.IdType.CAS).first()
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

    substance = models.ForeignKey(Substance, on_delete=models.CASCADE, related_name="identifiers")
    id_type = models.CharField(max_length=20, choices=IdType.choices)
    id_value = models.CharField(max_length=100)

    class Meta:
        db_table = "substances_identifier"
        verbose_name = "Stoffkennung"
        verbose_name_plural = "Stoffkennungen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "substance", "id_type"], name="uq_identifier_substance_type"
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

    substance = models.ForeignKey(Substance, on_delete=models.CASCADE, related_name="sds_revisions")

    # Versionierung
    revision_number = models.PositiveIntegerField(default=1)
    revision_date = models.DateField(help_text="Datum des SDS")

    # Dokument (FK zu documents-Modul)
    document = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Verknüpftes PDF-Dokument",
    )

    # Klassifikation
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    signal_word = models.CharField(
        max_length=20, choices=SignalWord.choices, default=SignalWord.NONE
    )

    # H-/P-Sätze (ManyToMany zu Referenztabellen)
    hazard_statements = models.ManyToManyField(
        "HazardStatementRef", blank=True, related_name="sds_revisions"
    )
    precautionary_statements = models.ManyToManyField(
        "PrecautionaryStatementRef", blank=True, related_name="sds_revisions"
    )
    pictograms = models.ManyToManyField("PictogramRef", blank=True, related_name="sds_revisions")

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
                fields=["substance", "revision_number"], name="uq_sds_substance_revision"
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
        Substance, on_delete=models.CASCADE, related_name="inventory_items"
    )
    site = models.ForeignKey(
        "tenancy.Site", on_delete=models.CASCADE, related_name="substance_inventory"
    )
    facility = models.ForeignKey(
        "tenancy.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substance_inventory",
        help_text="Produktionsstätte / Werk (optional)",
    )

    quantity = models.DecimalField(max_digits=12, decimal_places=3, help_text="Menge")
    unit = models.CharField(max_length=20, default="kg", help_text="Einheit (kg, l, m³)")
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.LIQUID, help_text="Aggregatzustand"
    )
    storage_location = models.CharField(
        max_length=200, blank=True, default="", help_text="Lagerort (z.B. Gefahrstofflager A)"
    )
    responsible_user = models.UUIDField(null=True, blank=True, help_text="Verantwortliche Person")

    class Meta:
        db_table = "substances_site_inventory"
        verbose_name = "Standort-Inventar"
        verbose_name_plural = "Standort-Inventar"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "substance", "storage_location"],
                name="uq_inventory_site_substance_location",
            ),
        ]

    def __str__(self):
        return f"{self.substance.name} @ {self.site} ({self.quantity} {self.unit})"


# =============================================================================
# REFERENZTABELLEN (Global, nicht tenant-spezifisch)
# =============================================================================


class HazardStatementRef(models.Model):
    """H-Sätze Referenztabelle (GHS)."""

    code = models.CharField(max_length=10, unique=True, help_text="H-Code (z.B. H225)")
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="English text")
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Kategorie (physikalisch, Gesundheit, Umwelt)",
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

    code = models.CharField(max_length=20, unique=True, help_text="P-Code (z.B. P210, P210+P233)")
    text_de = models.TextField(help_text="Deutscher Text")
    text_en = models.TextField(blank=True, default="", help_text="English text")
    category = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Kategorie (Prävention, Reaktion, Lagerung, Entsorgung)",
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

    code = models.CharField(max_length=10, unique=True, help_text="GHS-Code (z.B. GHS01)")
    name_de = models.CharField(max_length=100, help_text="Deutscher Name")
    name_en = models.CharField(max_length=100, blank=True, default="", help_text="English name")
    svg_path = models.CharField(
        max_length=200, blank=True, default="", help_text="Pfad zur SVG-Datei"
    )
    description = models.TextField(blank=True, default="", help_text="Beschreibung der Gefahr")

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
        max_length=30,
        blank=True,
        default="",
    )

    # Quantities
    max_quantity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Maximale Lagermenge in kg",
    )
    current_quantity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Aktuelle Lagermenge in kg",
    )

    # TRGS 510
    storage_class = models.CharField(
        max_length=10,
        choices=Substance.StorageClass.choices,
        blank=True,
        default="",
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
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Untere Mengenschwelle (Tonnen)",
    )
    seveso_threshold_upper_t = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Obere Mengenschwelle (Tonnen)",
    )

    # GHS
    h_statements = models.TextField(
        blank=True,
        default="",
    )
    ghs_pictograms = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )

    notes = models.TextField(blank=True, default="")
    last_inventory_date = models.DateField(
        null=True,
        blank=True,
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
        return f"{self.substance_name} ({self.current_quantity_kg} kg)"

    @property
    def seveso_utilization_pct(self) -> float | None:
        """Seveso threshold utilization percentage."""
        thr = self.seveso_threshold_lower_t
        if not thr or thr == 0:
            return None
        qty_t = float(self.current_quantity_kg) / 1000
        return round(qty_t / float(thr) * 100, 1)


StorageClass = Substance.StorageClass


# =============================================================================
# PRODUCT (Handelsprodukt / Gemisch, UC-004)
# =============================================================================


class Product(TenantScopedModel):
    """Handelsprodukt oder Gemisch — mandantenspezifisch (UC-004).

    Ein Reinstoff ist ein Product mit genau 1 ProductComponent (100%).
    Kein separater FK global_substance → einheitlicher Query-Pfad.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Inaktiv"
        ARCHIVED = "archived", "Archiviert"

    trade_name = models.CharField(
        max_length=300,
        help_text="Handelsname / Produktbezeichnung",
    )
    manufacturer = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        limit_choices_to={"party_type": "manufacturer"},
    )
    supplier = models.ForeignKey(
        Party,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_products",
        limit_choices_to={"party_type": "supplier"},
    )
    material_number = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Interne Materialnummer",
    )
    sds_revision = models.ForeignKey(
        "global_sds.GlobalSdsRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Verknüpftes globales SDS (automatisch via CAS-Match)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung / allgemeiner Verwendungszweck",
    )

    class Meta:
        db_table = "substances_product"
        verbose_name = "Handelsprodukt"
        verbose_name_plural = "Handelsprodukte"
        ordering = ["trade_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "trade_name", "manufacturer"],
                name="uq_product_tenant_name_mfr",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="ix_product_tenant_status"),
        ]

    def __str__(self):
        mfr = f" ({self.manufacturer.name})" if self.manufacturer else ""
        return f"{self.trade_name}{mfr}"

    @property
    def is_pure_substance(self) -> bool:
        """True wenn Reinstoff (genau 1 Komponente)."""
        return self.components.count() == 1

    @property
    def cas_number(self) -> str | None:
        """CAS der Hauptkomponente (bei Reinstoff)."""
        comp = self.components.select_related("substance").first()
        return comp.substance.cas_number if comp and comp.substance else None


# =============================================================================
# PRODUCT COMPONENT (Inhaltsstoff eines Produkts, UC-004)
# =============================================================================


class ProductComponent(models.Model):
    """Inhaltsstoff eines Handelsprodukts — Brücke zu GlobalSubstance (UC-004).

    Reinstoff: 1 Component mit concentration_pct=100.
    Gemisch: N Components mit Konzentrationsbereichen.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="components",
    )
    substance = models.ForeignKey(
        "global_sds.GlobalSubstance",
        on_delete=models.PROTECT,
        related_name="product_components",
        help_text="Globale Substanz (CAS-basiert)",
    )
    concentration_pct = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Exakte Konzentration in % (bei Reinstoff: 100)",
    )
    concentration_min = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Untere Konzentrationsgrenze in %",
    )
    concentration_max = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Obere Konzentrationsgrenze in %",
    )
    reach_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="REACH-Registrierungsnummer",
    )

    class Meta:
        db_table = "substances_product_component"
        verbose_name = "Produktkomponente"
        verbose_name_plural = "Produktkomponenten"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "substance"],
                name="uq_product_component_substance",
            ),
        ]

    def __str__(self):
        pct = f" {self.concentration_pct}%" if self.concentration_pct else ""
        return f"{self.substance}{pct}"


# =============================================================================
# SUBSTANCE USAGE (Produkt × Standort × Abteilung, UC-004)
# =============================================================================


class SubstanceUsage(TenantScopedModel):
    """Verwendung eines Handelsprodukts an einem Standort (UC-004).

    Zentrale Tabelle des Gefahrstoffkatasters: Welches Produkt wird
    wo, in welcher Abteilung, wofür und in welcher Menge verwendet?
    Ersetzt langfristig SiteInventoryItem + LocationSubstanceEntry.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        INACTIVE = "inactive", "Inaktiv"
        PHASED_OUT = "phased_out", "Auslaufend"

    class SubstitutionStatus(models.TextChoices):
        OPEN = "open", "Offen"
        DONE = "done", "Durchgeführt"
        NOT_REQUIRED = "not_required", "Nicht erforderlich"

    class Unit(models.TextChoices):
        KG = "kg", "Kilogramm"
        L = "l", "Liter"
        M3 = "m3", "Kubikmeter"
        T = "t", "Tonnen"
        PIECES = "pcs", "Stück"

    class AggregateState(models.TextChoices):
        SOLID = "solid", "Fest"
        LIQUID = "liquid", "Flüssig"
        GAS = "gas", "Gasförmig"
        AEROSOL = "aerosol", "Aerosol"
        PASTE = "paste", "Pastös"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="usages",
    )
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="substance_usages",
    )
    department = models.ForeignKey(
        "tenancy.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substance_usages",
    )
    facility = models.ForeignKey(
        "tenancy.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substance_usages",
        help_text="Produktionsstätte / Werk (optional)",
    )

    usage_description = models.TextField(
        blank=True,
        default="",
        help_text="Verwendungszweck im Betrieb",
    )
    storage_location = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Lagerort (z.B. Gefahrstofflager Halle 3)",
    )
    storage_class = models.CharField(
        max_length=10,
        choices=Substance.StorageClass.choices,
        blank=True,
        default="",
        help_text="Lagerklasse nach TRGS 510 (standortabhängig)",
    )
    aggregate_state = models.CharField(
        max_length=20,
        choices=AggregateState.choices,
        blank=True,
        default="",
    )

    max_storage_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Max. zulässige Lagermenge",
    )
    max_storage_unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.KG,
    )
    annual_consumption = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Jahresverbrauch",
    )
    annual_consumption_unit = models.CharField(
        max_length=10,
        choices=Unit.choices,
        default=Unit.KG,
    )

    operating_instruction = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substance_usages_oi",
        help_text="Betriebsanweisung",
    )
    risk_assessment = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substance_usages_ra",
        help_text="Gefährdungsbeurteilung",
    )

    substitution_status = models.CharField(
        max_length=20,
        choices=SubstitutionStatus.choices,
        default=SubstitutionStatus.OPEN,
    )
    substitution_notes = models.TextField(
        blank=True,
        default="",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    last_reviewed = models.DateField(
        null=True,
        blank=True,
        help_text="Datum der letzten Überprüfung",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "substances_usage"
        verbose_name = "Gefahrstoff-Verwendung"
        verbose_name_plural = "Gefahrstoff-Verwendungen"
        ordering = ["product__trade_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "product", "site", "department"],
                name="uq_usage_product_site_dept",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "site"], name="ix_usage_tenant_site"),
            models.Index(fields=["tenant_id", "status"], name="ix_usage_tenant_status"),
            models.Index(
                fields=["tenant_id", "substitution_status"],
                name="ix_usage_tenant_subst_status",
            ),
        ]

    def __str__(self):
        dept = f" / {self.department.name}" if self.department else ""
        return f"{self.product.trade_name} @ {self.site.name}{dept}"


# =============================================================================
# IMPORT BATCH / ROW (Excel-Import, UC-004)
# =============================================================================


class ImportBatch(TenantScopedModel):
    """Excel-Import-Batch mit Spalten-Mapping und Status (UC-004)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Warte auf Bestätigung"
        PROCESSING = "processing", "Wird verarbeitet"
        DONE = "done", "Abgeschlossen"
        FAILED = "failed", "Fehlgeschlagen"

    file_name = models.CharField(max_length=500)
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 der hochgeladenen Datei (Duplikaterkennung)",
    )
    target_site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="import_batches",
    )
    column_mapping = models.JSONField(
        default=dict,
        blank=True,
        help_text="Spalten-Zuordnung {excel_col: model_field}",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    stats = models.JSONField(
        default=dict,
        blank=True,
        help_text="Import-Statistik {created: N, updated: N, skipped: N, errors: N}",
    )
    error_message = models.TextField(blank=True, default="")
    imported_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "substances_import_batch"
        verbose_name = "Import-Batch"
        verbose_name_plural = "Import-Batches"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} → {self.target_site} ({self.get_status_display()})"

    @staticmethod
    def compute_file_hash(file_content: bytes) -> str:
        """SHA-256 des Dateiinhalts berechnen."""
        return hashlib.sha256(file_content).hexdigest()


class ImportRow(TenantScopedModel):
    """Einzelzeile eines Excel-Imports mit Matching-Ergebnis (UC-004)."""

    class Status(models.TextChoices):
        OK = "ok", "OK"
        WARNING = "warning", "Warnung"
        ERROR = "error", "Fehler"
        SKIPPED = "skipped", "Übersprungen"

    batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField(help_text="Zeilennummer in der Excel-Datei")
    raw_data = models.JSONField(
        default=dict,
        help_text="Original-Zeile als JSON {spalte: wert}",
    )
    resolved_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_rows",
        help_text="Zugeordnetes Produkt nach Import",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OK,
    )
    messages = models.JSONField(
        default=list,
        blank=True,
        help_text="Validierungs-/Matching-Hinweise",
    )

    class Meta:
        db_table = "substances_import_row"
        verbose_name = "Import-Zeile"
        verbose_name_plural = "Import-Zeilen"
        ordering = ["row_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_number"],
                name="uq_import_row_per_batch",
            ),
        ]

    def __str__(self):
        return f"Row {self.row_number} ({self.get_status_display()})"


# =============================================================================
# LEGACY PHRASE MAPPING (R→H, S→P für Altdaten-Import)
# =============================================================================


class RPhrase(models.Model):
    """Legacy R-Satz → H-Satz Mapping (EU Richtlinie 67/548/EWG → CLP/GHS)."""

    r_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="R-Satz Code (z.B. R11, R36/37/38)",
    )
    r_text_de = models.TextField(help_text="Deutscher R-Satz Text")
    mapped_h_codes = models.ManyToManyField(
        HazardStatementRef,
        blank=True,
        related_name="r_phrase_sources",
        help_text="Zugeordnete H-Sätze (kann 0..N sein)",
    )
    mapping_notes = models.TextField(
        blank=True,
        default="",
        help_text="Hinweise zur Zuordnung (z.B. 'keine exakte Entsprechung')",
    )

    class Meta:
        db_table = "substances_r_phrase"
        verbose_name = "R-Satz (Legacy)"
        verbose_name_plural = "R-Sätze (Legacy)"
        ordering = ["r_code"]

    def __str__(self):
        return f"{self.r_code}: {self.r_text_de[:60]}"


class SPhrase(models.Model):
    """Legacy S-Satz → P-Satz Mapping (EU Richtlinie 67/548/EWG → CLP/GHS)."""

    s_code = models.CharField(
        max_length=20,
        unique=True,
        help_text="S-Satz Code (z.B. S2, S26, S36/37/39)",
    )
    s_text_de = models.TextField(help_text="Deutscher S-Satz Text")
    mapped_p_codes = models.ManyToManyField(
        PrecautionaryStatementRef,
        blank=True,
        related_name="s_phrase_sources",
        help_text="Zugeordnete P-Sätze (kann 0..N sein)",
    )
    mapping_notes = models.TextField(
        blank=True,
        default="",
        help_text="Hinweise zur Zuordnung",
    )

    class Meta:
        db_table = "substances_s_phrase"
        verbose_name = "S-Satz (Legacy)"
        verbose_name_plural = "S-Sätze (Legacy)"
        ordering = ["s_code"]

    def __str__(self):
        return f"{self.s_code}: {self.s_text_de[:60]}"


# =============================================================================
# SDS CHANGE LOG (UC-005: SDS-Aktualisierungszyklus)
# =============================================================================


class SdsChangeLog(TenantScopedModel):
    """Persistiertes Diff zwischen zwei SDS-Revisionen (UC-005).

    Speichert Änderungen (H-/P-Sätze, Grenzwerte, Piktogramme)
    und deren Bewertung für Audit und Konsequenz-Ableitung.
    """

    class Impact(models.TextChoices):
        NO_IMPACT = "no_impact", "Keine Auswirkung"
        INFORMATIONAL = "informational", "Informativ"
        ACTION_REQUIRED = "action_required", "Handlungsbedarf"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="sds_change_logs",
    )
    old_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs_old",
        help_text="Vorherige SDS-Revision (NULL bei Ersterfassung)",
    )
    new_revision = models.ForeignKey(
        SdsRevision,
        on_delete=models.CASCADE,
        related_name="change_logs_new",
    )
    impact = models.CharField(
        max_length=20,
        choices=Impact.choices,
        default=Impact.INFORMATIONAL,
    )
    changes = models.JSONField(
        default=dict,
        help_text='Strukturiertes Diff: {"h_statements": {"added": [...], "removed": [...]}, ...}',
    )
    reviewed_by = models.UUIDField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "substances_sds_change_log"
        verbose_name = "SDS-Änderungsprotokoll"
        verbose_name_plural = "SDS-Änderungsprotokolle"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "old_revision", "new_revision"],
                name="uq_sds_change_log_revisions",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "impact"],
                name="ix_sds_change_log_impact",
            ),
        ]

    def __str__(self):
        old = f"Rev.{self.old_revision.revision_number}" if self.old_revision else "–"
        return f"{self.product.trade_name}: {old} → Rev.{self.new_revision.revision_number}"


# =============================================================================
# COMPLIANCE REVIEW (UC-006: Periodische SDS-Prüfung)
# =============================================================================


class ComplianceReview(TenantScopedModel):
    """Prüfprotokoll für periodische SDS-/Kataster-Prüfungen (UC-006).

    Ersetzt das einfache DateField SubstanceUsage.last_reviewed
    durch ein vollständiges, revisionssicheres Prüfprotokoll.
    """

    class Result(models.TextChoices):
        CURRENT = "current", "Aktuell — keine Änderung"
        UPDATE_REQUIRED = "update_required", "Aktualisierung erforderlich"
        PHASED_OUT = "phased_out", "Auslaufend / Ersetzt"

    substance_usage = models.ForeignKey(
        SubstanceUsage,
        on_delete=models.CASCADE,
        related_name="compliance_reviews",
    )
    reviewer_id = models.UUIDField(
        db_index=True,
        help_text="User-ID des Prüfers",
    )
    review_date = models.DateField(help_text="Datum der Prüfung")
    result = models.CharField(
        max_length=20,
        choices=Result.choices,
    )
    next_review_date = models.DateField(
        help_text="Nächste Prüfung fällig am",
    )
    comment = models.TextField(blank=True, default="")

    class Meta:
        db_table = "substances_compliance_review"
        verbose_name = "Compliance-Prüfung"
        verbose_name_plural = "Compliance-Prüfungen"
        ordering = ["-review_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["substance_usage", "review_date"],
                name="uq_compliance_review_per_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "next_review_date"],
                name="ix_compliance_review_next",
            ),
            models.Index(
                fields=["tenant_id", "result"],
                name="ix_compliance_review_result",
            ),
        ]

    def __str__(self):
        return f"{self.substance_usage} — {self.review_date} ({self.get_result_display()})"


# =============================================================================
# KATASTER REVISION (UC-007: Gefahrstoffkataster-Versionierung)
# =============================================================================


class KatasterRevision(TenantScopedModel):
    """Versionierter Snapshot des Gefahrstoffkatasters pro Standort (UC-007).

    Implementiert Dokumentenlenkung: Jede Änderung am Kataster erzeugt
    eine neue Revision mit Snapshot, Changelog und Freigabe-Workflow.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        SUBMITTED = "submitted", "Zur Freigabe"
        APPROVED = "approved", "Freigegeben"
        SUPERSEDED = "superseded", "Abgelöst"

    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="kataster_revisions",
    )
    facility = models.ForeignKey(
        "tenancy.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kataster_revisions",
        help_text="Produktionsstätte / Werk (optional)",
    )
    revision_number = models.PositiveIntegerField(
        help_text="Fortlaufende Revisionsnummer pro Standort",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    snapshot = models.JSONField(
        default=list,
        help_text="Kataster-Snapshot: [{product_id, trade_name, manufacturer, ...}]",
    )
    changelog = models.JSONField(
        default=dict,
        help_text='Diff zur Vorgänger-Revision: {"added": [], "changed": [], "removed": []}',
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kataster_revisions",
        help_text="PDF-Export (Dokumentenlenkung)",
    )
    approved_by = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "substances_kataster_revision"
        verbose_name = "Kataster-Revision"
        verbose_name_plural = "Kataster-Revisionen"
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site", "revision_number"],
                name="uq_kataster_revision_per_site",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "site", "status"],
                name="ix_kataster_revision_status",
            ),
        ]

    def __str__(self):
        return f"Kataster {self.site.name} Rev.{self.revision_number} ({self.get_status_display()})"
