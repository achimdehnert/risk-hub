# src/explosionsschutz/models/zone.py
"""
Zoneneinteilung, Zündquellen-Bewertung und Zonenberechnungs-Nachweis.

ZoneDefinition: Zoneneinteilung nach ATEX
IgnitionSource: 13 Zündquellen nach EN 1127-1
ZoneIgnitionSourceAssessment: Bewertung pro Zone
ZoneCalculationResult: Archivierter TRGS 721 Nachweis
"""

from django.contrib.auth import get_user_model
from django.db import models
from django_tenancy.managers import TenantManager

from .concept import ExplosionConcept
from .master_data import ReferenceStandard

User = get_user_model()


class ZoneDefinition(models.Model):
    """Zoneneinteilung nach ATEX"""

    class ZoneType(models.TextChoices):
        ZONE_0 = "0", "Zone 0 (Gas/Dampf, ständig)"
        ZONE_1 = "1", "Zone 1 (Gas/Dampf, gelegentlich)"
        ZONE_2 = "2", "Zone 2 (Gas/Dampf, selten)"
        ZONE_20 = "20", "Zone 20 (Staub, ständig)"
        ZONE_21 = "21", "Zone 21 (Staub, gelegentlich)"
        ZONE_22 = "22", "Zone 22 (Staub, selten)"
        NON_EX = "non_ex", "Nicht Ex-Bereich"

    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(ExplosionConcept, on_delete=models.CASCADE, related_name="zones")

    zone_type = models.CharField(max_length=10, choices=ZoneType.choices, default=ZoneType.ZONE_2)
    name = models.CharField(
        max_length=200, help_text="Bezeichnung der Zone (z.B. 'Abfüllbereich Tank 1')"
    )
    description = models.TextField(blank=True, default="")
    justification = models.TextField(
        blank=True, default="", help_text="Begründung für Zoneneinteilung"
    )

    # Ausdehnung (GeoJSON-kompatibel)
    extent = models.JSONField(
        null=True, blank=True, help_text="Geometrie als GeoJSON (Point, Polygon, etc.)"
    )
    extent_horizontal_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Horizontale Ausdehnung in Metern",
    )
    extent_vertical_m = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Vertikale Ausdehnung in Metern",
    )

    # Regelwerksreferenz
    reference_standard = models.ForeignKey(
        ReferenceStandard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zone_definitions",
    )
    reference_section = models.CharField(
        max_length=50, blank=True, default="", help_text="Abschnitt im Regelwerk (z.B. '4.2.1')"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_zone_definition"
        verbose_name = "Zonendefinition"
        verbose_name_plural = "Zonendefinitionen"

    def __str__(self) -> str:
        return f"{self.get_zone_type_display()} - {self.name}"

    @property
    def required_equipment_category(self) -> str:
        """Erforderliche Gerätekategorie für diese Zone"""
        mapping = {
            "0": "1G",
            "1": "2G",
            "2": "3G",
            "20": "1D",
            "21": "2D",
            "22": "3D",
            "non_ex": "non_ex",
        }
        return mapping.get(self.zone_type, "unknown")


class IgnitionSource(models.TextChoices):
    """13 Zündquellen nach EN 1127-1"""

    S1_HOT_SURFACES = "S1", "Heiße Oberflächen"
    S2_FLAMES = "S2", "Flammen und heiße Gase"
    S3_MECHANICAL_SPARKS = "S3", "Mechanisch erzeugte Funken"
    S4_ELECTRICAL = "S4", "Elektrische Anlagen"
    S5_STRAY_CURRENTS = "S5", "Kathodischer Korrosionsschutz / Streuströme"
    S6_STATIC = "S6", "Statische Elektrizität"
    S7_LIGHTNING = "S7", "Blitzschlag"
    S8_ELECTROMAGNETIC = "S8", "Elektromagnetische Felder (HF)"
    S9_OPTICAL = "S9", "Optische Strahlung"
    S10_IONIZING = "S10", "Ionisierende Strahlung"
    S11_ULTRASOUND = "S11", "Ultraschall"
    S12_ADIABATIC = "S12", "Adiabatische Kompression / Stoßwellen"
    S13_EXOTHERMIC = "S13", "Exotherme Reaktionen"


class ZoneIgnitionSourceAssessment(models.Model):
    """
    Bewertung der 13 Zündquellen pro Zone nach EN 1127-1.
    """

    tenant_id = models.UUIDField(db_index=True)

    zone = models.ForeignKey(
        ZoneDefinition, on_delete=models.CASCADE, related_name="ignition_assessments"
    )
    ignition_source = models.CharField(max_length=10, choices=IgnitionSource.choices)

    is_present = models.BooleanField(
        default=False, help_text="Ist diese Zündquelle im Bereich vorhanden?"
    )
    is_effective = models.BooleanField(
        default=False, help_text="Kann diese Zündquelle wirksam werden (Energie ausreichend)?"
    )
    mitigation = models.TextField(
        blank=True, default="", help_text="Beschreibung der Schutzmaßnahmen gegen diese Zündquelle"
    )

    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    assessed_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_zone_ignition_assessment"
        verbose_name = "Zündquellen-Bewertung"
        verbose_name_plural = "Zündquellen-Bewertungen"
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "ignition_source"], name="uq_zone_ignition_source"
            ),
        ]

    def __str__(self) -> str:
        status = (
            "wirksam"
            if self.is_effective
            else ("vorhanden" if self.is_present else "nicht vorhanden")
        )
        return f"{self.zone.name} - {self.get_ignition_source_display()}: {status}"


class ZoneCalculationResult(models.Model):
    """
    Archivierter TRGS 721 Zonenberechnungs-Nachweis.
    Nachweispflicht nach BetrSichV §§ 14-17.

    INVARIANTE: Unveränderlich und unlöschbar nach Erstellung.
    Kein 'change'- oder 'delete'-Permission — nur 'add' und 'view'.
    PostgreSQL RLS verhindert DELETE auf DB-Ebene (siehe Migration).
    """

    tenant_id = models.UUIDField(db_index=True)

    zone = models.ForeignKey(
        ZoneDefinition,
        on_delete=models.PROTECT,
        related_name="calculations",
        help_text="PROTECT: Zone nicht löschbar solange Nachweis existiert",
    )
    substance_name = models.CharField(max_length=200)
    release_rate_kg_s = models.DecimalField(max_digits=12, decimal_places=6)
    ventilation_rate_m3_s = models.DecimalField(max_digits=12, decimal_places=4)
    release_type = models.CharField(
        max_length=20,
        choices=[("jet", "Strahl"), ("pool", "Lache"), ("diffuse", "Diffus")],
    )
    calculated_zone_type = models.CharField(
        max_length=5,
        choices=[("0", "Zone 0"), ("1", "Zone 1"), ("2", "Zone 2")],
    )
    calculated_radius_m = models.DecimalField(max_digits=8, decimal_places=3)
    calculated_volume_m3 = models.DecimalField(max_digits=12, decimal_places=3)
    basis_norm = models.CharField(
        max_length=100,
        default="TRGS 721:2017-09",
        help_text="Normversion inkl. Ausgabejahr (z.B. 'TRGS 721:2017-09')",
    )
    riskfw_version = models.CharField(
        max_length=20,
        help_text="riskfw Package-Version zum Zeitpunkt der Berechnung",
    )
    raw_result = models.JSONField(
        help_text="Vollständiges ZoneExtentResult (dataclasses.asdict())",
    )
    calculated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zone_calculations",
    )
    calculated_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    objects = TenantManager()

    class Meta:
        db_table = "ex_zone_calculation_result"
        verbose_name = "Zonenberechnungs-Nachweis"
        verbose_name_plural = "Zonenberechnungs-Nachweise"
        ordering = ["-calculated_at"]
        default_permissions = ("add", "view")

    def __str__(self) -> str:
        return (
            f"Zone {self.calculated_zone_type} — {self.substance_name} "
            f"r={self.calculated_radius_m}m ({self.calculated_at:%Y-%m-%d})"
        )
