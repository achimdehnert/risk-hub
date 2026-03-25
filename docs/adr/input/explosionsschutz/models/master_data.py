"""
Stammdaten-Modelle für das Explosionsschutz-Modul.

Hybrid-Isolation: tenant_id=NULL bedeutet globale Systemdaten,
tenant_id=UUID bedeutet tenant-spezifische Erweiterung.
"""
from __future__ import annotations

import uuid

from django.db import models


class TenantScopedMasterDataManager(models.Manager):
    """
    Custom Manager für Hybrid-Isolation:
    - .for_tenant(tid) → globale + tenant-eigene Daten
    - .global_only()   → nur Systemdaten
    - .tenant_only(tid)→ nur tenant-eigene Daten
    """

    def for_tenant(self, tenant_id: uuid.UUID):
        return self.filter(
            models.Q(tenant_id__isnull=True) | models.Q(tenant_id=tenant_id)
        )

    def global_only(self):
        return self.filter(tenant_id__isnull=True)

    def tenant_only(self, tenant_id: uuid.UUID):
        return self.filter(tenant_id=tenant_id)


class ReferenceStandard(models.Model):
    """
    Rechtliche und normative Grundlagen (TRGS, BetrSichV, DIN EN …).

    Hybrid-Isolation: is_system=True Daten sind schreibgeschützt für Tenants.
    Tenants können eigene Normen ergänzen (is_system=False).
    """

    class Category(models.TextChoices):
        TRGS = "trgs", "Technische Regeln für Gefahrstoffe"
        TRBS = "trbs", "Technische Regeln für Betriebssicherheit"
        DGUV = "dguv", "DGUV Regelwerk"
        DIN_EN = "din_en", "DIN EN Norm"
        ATEX = "atex", "ATEX Richtlinie"
        VERORDNUNG = "verordnung", "Verordnung (GefStoffV, BetrSichV …)"
        SONSTIGE = "sonstige", "Sonstige"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="NULL = globale Systemdaten, UUID = tenant-spezifisch",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Systemdaten dürfen von Tenants nicht geändert werden",
    )

    code = models.CharField(
        max_length=80,
        help_text="z.B. 'TRGS 722:2021-06' oder 'BetrSichV 2015'",
    )
    title = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices)
    issue_date = models.CharField(
        max_length=20,
        blank=True,
        help_text="Ausgabedatum für Betriebsprüfungen (z.B. '2021-06')",
    )
    url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = TenantScopedMasterDataManager()

    class Meta:
        db_table = "ex_reference_standard"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "code"],
                name="uq_ex_reference_standard_code_per_tenant",
                nulls_distinct=False,  # NULL = global, unique über global
            ),
        ]
        ordering = ["category", "code"]

    def __str__(self) -> str:
        return self.code


class MeasureCatalog(models.Model):
    """
    Vorlage für wiederkehrende Schutzmaßnahmen (z.B. N₂-Inertisierung).
    Ermöglicht konsistente Dokumentation über mehrere Konzepte.
    """

    class DefaultCategory(models.TextChoices):
        PRIMARY = "primary", "Primär (Vermeidung ex. Atmosphäre)"
        SECONDARY = "secondary", "Sekundär (Zündquellenvermeidung)"
        CONSTRUCTIVE = "constructive", "Konstruktiv (Schadensminimierung)"
        ORGANISATIONAL = "organisational", "Organisatorisch"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_system = models.BooleanField(default=False)

    title = models.CharField(max_length=200)
    default_category = models.CharField(
        max_length=20, choices=DefaultCategory.choices
    )
    description_template = models.TextField(
        blank=True,
        help_text="Vorlage-Text; Platzhalter wie {STOFF} möglich",
    )
    trgs_reference = models.ForeignKey(
        ReferenceStandard,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_active = models.BooleanField(default=True)

    objects = TenantScopedMasterDataManager()

    class Meta:
        db_table = "ex_measure_catalog"
        ordering = ["default_category", "title"]

    def __str__(self) -> str:
        return self.title


class SafetyFunction(models.Model):
    """
    MSR-Sicherheitsfunktion nach IEC 62061 / ISO 13849 / TRGS 725.
    Wird als FK in ProtectionMeasure verknüpft.
    """

    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"

    class SILLevel(models.IntegerChoices):
        SIL_1 = 1, "SIL 1"
        SIL_2 = 2, "SIL 2"
        SIL_3 = 3, "SIL 3"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    performance_level = models.CharField(
        max_length=1,
        choices=PerformanceLevel.choices,
        null=True,
        blank=True,
    )
    sil_level = models.IntegerField(
        choices=SILLevel.choices, null=True, blank=True
    )
    monitoring_method = models.TextField(
        blank=True,
        help_text="Wie wird Ausfall erkannt? (z.B. Selbstüberwachung, Prüfintervall)",
    )
    test_interval_months = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Prüfintervall in Monaten"
    )
    trgs_reference = models.ForeignKey(
        ReferenceStandard,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ex_safety_function"
        ordering = ["name"]

    def __str__(self) -> str:
        pl = f" (PL {self.performance_level})" if self.performance_level else ""
        return f"{self.name}{pl}"


class EquipmentType(models.Model):
    """
    Katalog von Betriebsmittel-Typen mit ATEX-Kennzeichnung.
    Hybrid-Isolation: Systemdaten für Standard-Geräte, tenant-spezifisch erweiterbar.
    """

    class ATEXGroup(models.TextChoices):
        GROUP_I = "I", "Gruppe I (Bergbau)"
        GROUP_II = "II", "Gruppe II (Oberirdisch Gas/Dampf)"
        GROUP_III = "III", "Gruppe III (Staub)"

    class ATEXCategory(models.TextChoices):
        CAT_1G = "1G", "Kategorie 1G (Zone 0)"
        CAT_2G = "2G", "Kategorie 2G (Zone 1)"
        CAT_3G = "3G", "Kategorie 3G (Zone 2)"
        CAT_1D = "1D", "Kategorie 1D (Zone 20)"
        CAT_2D = "2D", "Kategorie 2D (Zone 21)"
        CAT_3D = "3D", "Kategorie 3D (Zone 22)"
        CAT_M1 = "M1", "Kategorie M1 (Bergbau sehr hoch)"
        CAT_M2 = "M2", "Kategorie M2 (Bergbau hoch)"

    class TemperatureClass(models.TextChoices):
        T1 = "T1", "T1 (450 °C)"
        T2 = "T2", "T2 (300 °C)"
        T3 = "T3", "T3 (200 °C)"
        T4 = "T4", "T4 (135 °C)"
        T5 = "T5", "T5 (100 °C)"
        T6 = "T6", "T6 (85 °C)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    is_system = models.BooleanField(default=False)

    manufacturer = models.CharField(max_length=200)
    model_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Strukturierte ATEX-Kennzeichnung (statt Freitext)
    atex_group = models.CharField(
        max_length=3, choices=ATEXGroup.choices, blank=True
    )
    atex_category = models.CharField(
        max_length=3, choices=ATEXCategory.choices, blank=True
    )
    temperature_class = models.CharField(
        max_length=2, choices=TemperatureClass.choices, blank=True
    )
    protection_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ex-Schutzart (z.B. 'Ex d', 'Ex e', 'Ex ic nA')",
    )
    explosion_group = models.CharField(
        max_length=10,
        blank=True,
        help_text="Explosionsgruppe (z.B. IIA, IIB, IIC)",
    )

    # Prüfintervall-Vorgaben nach BetrSichV §15
    default_inspection_interval_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Standardprüfintervall in Monaten",
    )

    objects = TenantScopedMasterDataManager()

    class Meta:
        db_table = "ex_equipment_type"
        ordering = ["manufacturer", "model_name"]

    def __str__(self) -> str:
        return f"{self.manufacturer} {self.model_name}"

    @property
    def atex_marking(self) -> str:
        """Zusammengesetzte ATEX-Kennzeichnung für Anzeige."""
        parts = []
        if self.atex_group:
            parts.append(f"Ex {self.atex_group}")
        if self.atex_category:
            parts.append(self.atex_category)
        if self.protection_type:
            parts.append(self.protection_type)
        if self.explosion_group:
            parts.append(self.explosion_group)
        if self.temperature_class:
            parts.append(self.temperature_class)
        return " ".join(parts) if parts else "—"

    def is_suitable_for_zone(self, zone_type: str) -> bool:
        """
        Prüft ob Gerät für gegebene Zone geeignet ist.
        Zone 0/20 → Kategorie 1, Zone 1/21 → Kategorie 1 oder 2,
        Zone 2/22 → Kategorie 1, 2 oder 3.
        """
        zone_category_map: dict[str, list[str]] = {
            "0": ["1G"],
            "1": ["1G", "2G"],
            "2": ["1G", "2G", "3G"],
            "20": ["1D"],
            "21": ["1D", "2D"],
            "22": ["1D", "2D", "3D"],
        }
        allowed = zone_category_map.get(zone_type, [])
        return self.atex_category in allowed
