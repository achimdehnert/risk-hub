"""
Zonendefinition und Zündquellenbewertung.
Entspricht Kapitel 6.2 (Zündquellen) und Kapitel 7.1 (Zoneneinteilung).
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from django.db import models


class IgnitionSource(StrEnum):
    """
    13 Zündquellenarten nach EN 1127-1:2019-10 / TRGS 723.
    Jede Zone muss alle 13 Zündquellen bewerten.
    """

    S01_HOT_SURFACES = "S01"       # Heiße Oberflächen
    S02_FLAMES = "S02"             # Flammen und heiße Gase (inkl. Partikel)
    S03_MECH_SPARKS = "S03"        # Mechanisch erzeugte Funken
    S04_ELECTRICAL = "S04"         # Elektrische Anlagen und Streuströme
    S05_STRAY_CURRENTS = "S05"     # Kathodischer Korrosionsschutz / Ausgleichsströme
    S06_STATIC = "S06"             # Elektrostatische Entladungen
    S07_LIGHTNING = "S07"          # Blitzschlag
    S08_EM_FIELDS = "S08"          # Elektromagnetische Felder (HF)
    S09_OPTICAL = "S09"            # Optische Strahlung (Laser, UV)
    S10_IONIZING = "S10"           # Ionisierende Strahlung
    S11_ULTRASOUND = "S11"         # Ultraschall
    S12_ADIABATIC = "S12"          # Adiabatische Kompression / Stoßwellen
    S13_EXOTHERMIC = "S13"         # Exotherme Reaktionen inkl. Selbstentzündung


IGNITION_SOURCE_LABELS: dict[str, str] = {
    "S01": "Heiße Oberflächen",
    "S02": "Flammen und heiße Gase (inkl. Partikel)",
    "S03": "Mechanisch erzeugte Funken",
    "S04": "Elektrische Anlagen und Streuströme",
    "S05": "Kathodischer Korrosionsschutz / Ausgleichsströme",
    "S06": "Elektrostatische Entladungen",
    "S07": "Blitzschlag",
    "S08": "Elektromagnetische Felder (Hochfrequenz)",
    "S09": "Optische Strahlung (Laser, UV)",
    "S10": "Ionisierende Strahlung",
    "S11": "Ultraschall",
    "S12": "Adiabatische Kompression / Stoßwellen",
    "S13": "Exotherme Reaktionen inkl. Selbstentzündung",
}


class ZoneDefinition(models.Model):
    """
    Zonendefinition nach ATEX-Richtlinie 1999/92/EG und TRGS 721.

    Zone 0/1/2 für Gase/Dämpfe/Nebel.
    Zone 20/21/22 für Stäube.
    """

    class ZoneType(models.TextChoices):
        # Gasbereiche
        ZONE_0 = "0", "Zone 0 (ständig ex. Atmosphäre)"
        ZONE_1 = "1", "Zone 1 (gelegentlich ex. Atmosphäre)"
        ZONE_2 = "2", "Zone 2 (selten und kurzfristig ex. Atmosphäre)"
        # Staubbereiche
        ZONE_20 = "20", "Zone 20 (ständig ex. Staubatmosphäre)"
        ZONE_21 = "21", "Zone 21 (gelegentlich ex. Staubatmosphäre)"
        ZONE_22 = "22", "Zone 22 (selten ex. Staubatmosphäre)"
        # Sonderfall: keine Zone notwendig (durch Schutzmaßnahmen vermieden)
        NO_ZONE = "none", "Keine Zone (ex. Atmosphäre vermieden)"

    class ExtentShape(models.TextChoices):
        SPHERE = "sphere", "Kugelförmig (Radius)"
        CYLINDER = "cylinder", "Zylindrisch (Radius + Höhe)"
        BOX = "box", "Quaderförmig (L × B × H)"
        ROOM = "room", "Raumbereich (Beschreibung)"
        CUSTOM = "custom", "Freigeometrie (Beschreibung)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(
        "concept.ExplosionConcept",
        on_delete=models.CASCADE,  # Zone gehört zum Konzept
        related_name="zones",
    )
    zone_type = models.CharField(max_length=4, choices=ZoneType.choices)
    name = models.CharField(
        max_length=200,
        help_text="Bezeichnung der Zone (z.B. 'Umgebung Füllstutzen')",
    )
    location_in_area = models.CharField(
        max_length=300,
        blank=True,
        help_text="Lage im Betriebsbereich",
    )

    # Geometrie der Zonenausdehnung
    extent_shape = models.CharField(
        max_length=10,
        choices=ExtentShape.choices,
        default=ExtentShape.CUSTOM,
    )
    extent_radius_m = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Radius in Metern (für Kugel/Zylinder)"
    )
    extent_height_m = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Höhe in Metern (für Zylinder/Quader)"
    )
    extent_length_m = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Länge in Metern (für Quader)"
    )
    extent_width_m = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Breite in Metern (für Quader)"
    )
    extent_description = models.TextField(
        blank=True,
        help_text="Freitext-Beschreibung der Zonenausdehnung",
    )

    # Normativer Nachweis
    trgs_reference = models.ForeignKey(
        "master_data.ReferenceStandard",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Referenznorm für Zoneneinteilung (z.B. TRGS 722)",
    )
    justification = models.TextField(
        help_text="Begründung der Zoneneinteilung (TRGS-Nachweis)"
    )

    # Lüftung (primärer Ex-Schutz via Verdünnung)
    ventilation_type = models.CharField(
        max_length=20,
        choices=[
            ("natural", "Natürliche Lüftung"),
            ("technical_dilution", "Technische Lüftung (Verdünnung)"),
            ("local_exhaust", "Objektabsaugung"),
            ("inertization", "Inertisierung"),
            ("none", "Keine Lüftung"),
        ],
        default="natural",
    )
    ventilation_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_zone_definition"
        ordering = ["zone_type", "name"]

    def __str__(self) -> str:
        return f"Zone {self.zone_type}: {self.name}"

    @property
    def ignition_assessment_complete(self) -> bool:
        """Sind alle 13 Zündquellen bewertet?"""
        assessed = self.ignition_assessments.values_list(
            "ignition_source", flat=True
        )
        return set(assessed) == set(s.value for s in IgnitionSource)

    @property
    def active_ignition_sources(self) -> list[str]:
        """Zündquellen, die als 'wirksam' bewertet wurden."""
        return list(
            self.ignition_assessments.filter(is_effective=True).values_list(
                "ignition_source", flat=True
            )
        )


class ZoneIgnitionSourceAssessment(models.Model):
    """
    Bewertung einer Zündquelle für eine Zone nach EN 1127-1.

    Für jede Zone MÜSSEN alle 13 Zündquellen bewertet werden.
    Das ist Pflichtbestandteil des Explosionsschutzdokuments (§6 GefStoffV).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    zone = models.ForeignKey(
        ZoneDefinition,
        on_delete=models.CASCADE,
        related_name="ignition_assessments",
    )
    ignition_source = models.CharField(
        max_length=3,
        choices=[(s.value, IGNITION_SOURCE_LABELS[s.value]) for s in IgnitionSource],
    )

    is_present = models.BooleanField(
        default=False,
        help_text="Ist diese Zündquelle im Bereich vorhanden?",
    )
    is_effective = models.BooleanField(
        default=False,
        help_text="Kann diese Zündquelle wirksam werden (Energie ≥ MZE)?",
    )
    mitigation = models.TextField(
        blank=True,
        help_text="Schutzmaßnahmen gegen diese Zündquelle",
    )
    residual_risk_acceptable = models.BooleanField(
        default=True,
        help_text="Restrisiko nach Maßnahmen akzeptabel?",
    )

    assessed_by_id = models.UUIDField(null=True, blank=True)
    assessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ex_zone_ignition_assessment"
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "ignition_source"],
                name="uq_ex_zone_ignition_source",
            ),
        ]

    def __str__(self) -> str:
        label = IGNITION_SOURCE_LABELS.get(self.ignition_source, self.ignition_source)
        status = (
            "wirksam" if self.is_effective
            else ("vorhanden" if self.is_present else "nicht relevant")
        )
        return f"{self.zone.name} – {label}: {status}"
