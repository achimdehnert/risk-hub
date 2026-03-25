# src/explosionsschutz/models/master_data.py
"""
Stammdaten: ReferenceStandard, MeasureCatalog, SafetyFunction, EquipmentType.

Alle erben von TenantScopedMasterData für Hybrid-Isolation
(global + tenant-spezifisch).
"""

from django.db import models

from .base import TenantScopedMasterData


class ReferenceStandard(TenantScopedMasterData):
    """
    Normative Referenzen (TRGS, IEC, EN, etc.)

    Beispiele (global):
    - TRGS 720: Gefährliche explosionsfähige Atmosphäre - Allgemeines
    - IEC 60079-10-1: Klassifizierung von Bereichen

    Beispiele (tenant-spezifisch):
    - Interne Richtlinie XY-001
    """

    class Category(models.TextChoices):
        TRGS = "TRGS", "Technische Regeln für Gefahrstoffe"
        IEC = "IEC", "IEC Normen"
        EN = "EN", "Europäische Normen"
        DIN = "DIN", "DIN Normen"
        VDSI = "VDSI", "VDSI Richtlinien"
        INTERNAL = "INTERNAL", "Interne Richtlinien"

    code = models.CharField(max_length=50, help_text="z.B. 'TRGS 720', 'IEC 60079-10-1'")
    title = models.CharField(max_length=500)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TRGS)
    url = models.URLField(blank=True, default="", help_text="Link zur offiziellen Quelle")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "ex_reference_standard"
        verbose_name = "Regelwerksreferenz"
        verbose_name_plural = "Regelwerksreferenzen"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code"], name="uq_reference_standard_tenant_code"
            ),
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(tenant_id__isnull=True),
                name="uq_reference_standard_global_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "category"],
                name="idx_refstd_tenant_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}: {self.title}"


class MeasureCatalog(TenantScopedMasterData):
    """
    Katalog wiederverwendbarer Schutzmaßnahmen-Vorlagen.

    Beispiele (global):
    - "Erdung aller leitfähigen Teile"
    - "Technische Lüftung nach DIN EN 60079-10-1"

    Beispiele (tenant-spezifisch):
    - "Interne Prozedur ABC-123"
    """

    class DefaultType(models.TextChoices):
        PRIMARY = "primary", "Primäre Maßnahme (Vermeidung)"
        SECONDARY = "secondary", "Sekundäre Maßnahme (Zündquellenvermeidung)"
        TERTIARY = "tertiary", "Tertiäre Maßnahme (Auswirkungsbegrenzung)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme"

    code = models.CharField(
        max_length=50, blank=True, default="", help_text="Optionaler Kurzcode, z.B. 'M-ERD-001'"
    )
    title = models.CharField(max_length=300)
    default_type = models.CharField(
        max_length=20, choices=DefaultType.choices, default=DefaultType.SECONDARY
    )
    description_template = models.TextField(
        blank=True, default="", help_text="Vorlage für Beschreibung, kann Platzhalter enthalten"
    )
    reference_standards = models.ManyToManyField(
        ReferenceStandard, blank=True, related_name="measure_catalog_entries"
    )

    class Meta:
        db_table = "ex_measure_catalog"
        verbose_name = "Maßnahmenkatalog"
        verbose_name_plural = "Maßnahmenkataloge"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "title"], name="uq_measure_catalog_tenant_title"
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "default_type"],
                name="idx_meascat_tenant_type",
            ),
        ]

    def __str__(self) -> str:
        prefix = f"[{self.code}] " if self.code else ""
        return f"{prefix}{self.title}"


class SafetyFunction(TenantScopedMasterData):
    """
    MSR-Sicherheitsfunktion nach IEC 62061 / ISO 13849.

    Wird verwendet für komplexe Schutzmaßnahmen mit:
    - Performance Level (PLr) nach ISO 13849
    - Safety Integrity Level (SIL) nach IEC 62061
    - Überwachungsanforderungen
    """

    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"

    class SILLevel(models.TextChoices):
        SIL_1 = "1", "SIL 1"
        SIL_2 = "2", "SIL 2"
        SIL_3 = "3", "SIL 3"

    class MonitoringMethod(models.TextChoices):
        CONTINUOUS = "continuous", "Kontinuierlich"
        PERIODIC = "periodic", "Periodisch"
        DEMAND = "demand", "Bei Anforderung"

    name = models.CharField(
        max_length=100, help_text="Eindeutiger Name, z.B. 'GW-001' für Gaswarnanlage 001"
    )
    description = models.TextField(blank=True, default="")

    performance_level = models.CharField(
        max_length=5,
        choices=PerformanceLevel.choices,
        blank=True,
        default="",
        help_text="Required Performance Level nach ISO 13849",
    )
    sil_level = models.CharField(
        max_length=5,
        choices=SILLevel.choices,
        blank=True,
        default="",
        help_text="Safety Integrity Level nach IEC 62061",
    )
    monitoring_method = models.CharField(
        max_length=20, choices=MonitoringMethod.choices, default=MonitoringMethod.CONTINUOUS
    )

    # Technische Details
    response_time_ms = models.IntegerField(
        null=True, blank=True, help_text="Ansprechzeit in Millisekunden"
    )
    proof_test_interval_months = models.IntegerField(
        null=True, blank=True, help_text="Proof-Test-Intervall in Monaten"
    )

    reference_standards = models.ManyToManyField(
        ReferenceStandard, blank=True, related_name="safety_functions"
    )

    class Meta:
        db_table = "ex_safety_function"
        verbose_name = "Sicherheitsfunktion"
        verbose_name_plural = "Sicherheitsfunktionen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="uq_safety_function_tenant_name"
            ),
        ]

    def __str__(self) -> str:
        levels = []
        if self.performance_level:
            levels.append(f"PL {self.performance_level}")
        if self.sil_level:
            levels.append(f"SIL {self.sil_level}")
        level_str = " / ".join(levels) if levels else "n/a"
        return f"{self.name} ({level_str})"


class EquipmentType(TenantScopedMasterData):
    """
    Stammdaten für Betriebsmittel-Typen mit strukturierter ATEX-Kennzeichnung.
    """

    class AtexGroup(models.TextChoices):
        GROUP_I = "I", "Gruppe I (Bergbau)"
        GROUP_II = "II", "Gruppe II (Industrie)"

    class AtexCategory(models.TextChoices):
        CAT_1G = "1G", "Kategorie 1G (Zone 0)"
        CAT_2G = "2G", "Kategorie 2G (Zone 0, 1)"
        CAT_3G = "3G", "Kategorie 3G (Zone 0, 1, 2)"
        CAT_1D = "1D", "Kategorie 1D (Zone 20)"
        CAT_2D = "2D", "Kategorie 2D (Zone 20, 21)"
        CAT_3D = "3D", "Kategorie 3D (Zone 20, 21, 22)"

    class ProtectionType(models.TextChoices):
        EX_D = "Ex d", "Druckfeste Kapselung"
        EX_E = "Ex e", "Erhöhte Sicherheit"
        EX_I = "Ex i", "Eigensicherheit"
        EX_P = "Ex p", "Überdruckkapselung"
        EX_M = "Ex m", "Vergusskapselung"
        EX_O = "Ex o", "Ölkapselung"
        EX_Q = "Ex q", "Sandkapselung"
        EX_N = "Ex n", "Nicht-funkend"
        EX_T = "Ex t", "Schutz durch Gehäuse (Staub)"

    class ExplosionGroup(models.TextChoices):
        IIA = "IIA", "IIA (Propan)"
        IIB = "IIB", "IIB (Ethylen)"
        IIC = "IIC", "IIC (Wasserstoff, Acetylen)"
        IIIA = "IIIA", "IIIA (brennbare Flusen)"
        IIIB = "IIIB", "IIIB (nicht leitfähiger Staub)"
        IIIC = "IIIC", "IIIC (leitfähiger Staub)"

    class TemperatureClass(models.TextChoices):
        T1 = "T1", "T1 (≤450°C)"
        T2 = "T2", "T2 (≤300°C)"
        T3 = "T3", "T3 (≤200°C)"
        T4 = "T4", "T4 (≤135°C)"
        T5 = "T5", "T5 (≤100°C)"
        T6 = "T6", "T6 (≤85°C)"

    class EPL(models.TextChoices):
        """Equipment Protection Level"""

        GA = "Ga", "Ga (sehr hohes Schutzniveau)"
        GB = "Gb", "Gb (hohes Schutzniveau)"
        GC = "Gc", "Gc (erhöhtes Schutzniveau)"
        DA = "Da", "Da (sehr hohes Schutzniveau - Staub)"
        DB = "Db", "Db (hohes Schutzniveau - Staub)"
        DC = "Dc", "Dc (erhöhtes Schutzniveau - Staub)"

    manufacturer = models.CharField(max_length=200)
    model = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")

    atex_group = models.CharField(
        max_length=5, choices=AtexGroup.choices, default=AtexGroup.GROUP_II
    )
    atex_category = models.CharField(
        max_length=5, choices=AtexCategory.choices, blank=True, default=""
    )
    protection_type = models.CharField(
        max_length=10, choices=ProtectionType.choices, blank=True, default=""
    )
    explosion_group = models.CharField(
        max_length=10, choices=ExplosionGroup.choices, blank=True, default=""
    )
    temperature_class = models.CharField(
        max_length=5, choices=TemperatureClass.choices, blank=True, default=""
    )
    epl = models.CharField(
        max_length=5,
        choices=EPL.choices,
        blank=True,
        default="",
        help_text="Equipment Protection Level",
    )
    ip_rating = models.CharField(max_length=10, blank=True, default="", help_text="z.B. IP65, IP66")
    ambient_temp_min = models.IntegerField(
        null=True, blank=True, help_text="Min. Umgebungstemperatur in °C"
    )
    ambient_temp_max = models.IntegerField(
        null=True, blank=True, help_text="Max. Umgebungstemperatur in °C"
    )
    datasheet_url = models.URLField(blank=True, default="")
    certificate_number = models.CharField(max_length=100, blank=True, default="")
    notified_body = models.CharField(
        max_length=100, blank=True, default="", help_text="z.B. 'PTB', 'DEKRA', 'TÜV'"
    )
    default_inspection_interval_months = models.PositiveIntegerField(
        default=12, help_text="Standard-Prüfintervall in Monaten"
    )

    class Meta:
        db_table = "ex_equipment_type"
        verbose_name = "Betriebsmitteltyp"
        verbose_name_plural = "Betriebsmitteltypen"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "manufacturer", "model"],
                name="uq_equipment_type_tenant_mfr_model",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "atex_category"],
                name="idx_eqtype_tenant_atex",
            ),
            models.Index(
                fields=["tenant_id", "manufacturer"],
                name="idx_eqtype_tenant_mfr",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model} ({self.full_atex_marking})"

    @property
    def full_atex_marking(self) -> str:
        """Vollständige ATEX-Kennzeichnung aus Einzelfeldern"""
        parts = [self.atex_group]
        if self.atex_category:
            parts.append(self.atex_category)
        if self.protection_type:
            parts.append(self.protection_type)
        if self.explosion_group:
            parts.append(self.explosion_group)
        if self.temperature_class:
            parts.append(self.temperature_class)
        if self.epl:
            parts.append(self.epl)
        return " ".join(parts) if len(parts) > 1 else "N/A"

    @property
    def allowed_zones(self) -> list:
        """Liste der Zonen, in denen dieses Gerät eingesetzt werden darf"""
        CATEGORY_ZONES = {
            "1G": ["0", "1", "2"],
            "2G": ["1", "2"],
            "3G": ["2"],
            "1D": ["20", "21", "22"],
            "2D": ["21", "22"],
            "3D": ["22"],
        }
        return CATEGORY_ZONES.get(self.atex_category, [])

    def is_suitable_for_zone(self, zone_type: str) -> bool:
        """Prüft ob dieses Gerätetyp für eine bestimmte Zone geeignet ist"""
        return zone_type in self.allowed_zones
