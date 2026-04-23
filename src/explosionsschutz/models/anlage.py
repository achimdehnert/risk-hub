# src/explosionsschutz/models/anlage.py
"""
Anlagen-Hierarchie und Betriebszustands-Matrix.

AnlageComponent: 3-Ebenen-Hierarchie Area → AnlageComponent → SubComponent.
OperationalStateAssessment: 5-Betriebszustände-GBU-Matrix pro Component.

ADR-044 Phase 3B.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class OperationalState(models.TextChoices):
    NORMAL = "NORMAL", "Normalbetrieb"
    STARTUP_SHUTDOWN = "START_STOP", "An-/Abfahrvorgänge"
    MALFUNCTION = "MALFUNC", "Fehlbedienung / Störung"
    ENERGY_FAILURE = "ENERGY", "Energieausfall"
    MAINTENANCE = "MAINT", "Wartung / Instandhaltung"


class AnlageComponent(models.Model):
    """
    Anlagen-Komponente innerhalb eines Explosionsschutzkonzepts.

    Unterstützt 3-Ebenen-Hierarchie über self-FK (parent_component).
    Ebene 1: Anlage/Prozesseinheit (z.B. 'Drehrohrofen 1')
    Ebene 2: Baugruppe (z.B. 'Eintragsschleuse')
    Ebene 3: Einzelkomponente (z.B. 'Doppelklappenschleuse Typ K')

    Bestandsschutz-Flag: legacy_installation steuert automatisch welche
    Anhang-I-Punkte entfallen (§ 15 BetrSichV greift nicht).
    """

    class ComponentType(models.TextChoices):
        OVEN = "ofen", "Ofen / Reaktor"
        FILTER = "filter", "Filter / Entstauber"
        VESSEL = "behaelter", "Behälter / Tank"
        CONVEYOR = "foerder", "Förderanlage"
        FILLING = "abfuell", "Abfüll- / Dosieranlage"
        CABINET = "schrank", "Gefahrstoffschrank"
        PIPE = "leitung", "Rohrleitung / Kanal"
        PUMP = "pumpe", "Pumpe / Verdichter"
        AGITATOR = "ruehrer", "Rührer / Mischer"
        OTHER = "andere", "Sonstiges"

    class MobilityType(models.TextChoices):
        STATIONARY = "STATIONARY", "Stationär"
        MOBILE = "MOBILE", "Mobil"
        TRANSPORTABLE = "TRANSPORTABLE", "Transportabel"

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="components",
    )
    parent_component = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    name = models.CharField(max_length=200)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices,
        default=ComponentType.OTHER,
    )
    commissioning_date = models.DateField(
        null=True,
        blank=True,
        help_text="Erstes Inbetriebnahmedatum (relevant für Bestandsschutz)",
    )
    legacy_installation = models.BooleanField(
        default=False,
        help_text=(
            "Bestandsanlage ohne ATEX-Zulassung nach § 15 BetrSichV. "
            "Entbindet von Vor-Inbetriebnahme-Prüfung, Anhang-I-Punkte 1.8(2-3) entfallen."
        ),
    )
    mobility_type = models.CharField(
        max_length=15,
        choices=MobilityType.choices,
        default=MobilityType.STATIONARY,
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_anlage_component"
        verbose_name = "Anlagenkomponente"
        verbose_name_plural = "Anlagenkomponenten"

    def __str__(self) -> str:
        return f"{self.get_component_type_display()}: {self.name}"

    @property
    def level(self) -> int:
        """Hierarchie-Tiefe (0=top-level, 1=Untergruppe, 2=Einzelkomponente)."""
        if not self.parent_component_id:
            return 0
        if not self.parent_component.parent_component_id:
            return 1
        return 2


class OperationalStateAssessment(models.Model):
    """
    GBU-Matrix: Bewertung pro Betriebszustand und Anlagenkomponente.

    5 Betriebszustände × n Komponenten. Pro Zeile: Ist ein Fehler/Versagen
    in diesem Zustand möglich, und wenn ja, welche Maßnahme.

    tenant_id wird nicht direkt gespeichert — Tenant-Isolation über
    component → concept → tenant_id FK-Chain (konsistent mit Repo-Pattern).
    """

    component = models.ForeignKey(
        AnlageComponent,
        on_delete=models.CASCADE,
        related_name="operational_state_assessments",
    )
    state = models.CharField(
        max_length=12,
        choices=OperationalState.choices,
    )
    failure_possible = models.BooleanField(
        help_text="Ist in diesem Betriebszustand ein Versagen/Fehler möglich?",
    )
    mitigation_measure_text = models.TextField(
        blank=True,
        help_text="Gegenmaßnahmen falls failure_possible=True",
    )

    class Meta:
        db_table = "ex_operational_state_assessment"
        verbose_name = "Betriebszustands-Bewertung"
        verbose_name_plural = "Betriebszustands-Bewertungen"
        constraints = [
            models.UniqueConstraint(
                fields=["component", "state"],
                name="uniq_state_assessment_per_component",
            ),
        ]

    def __str__(self) -> str:
        component_name = self.component.name if self.component_id else "?"
        status = "⚠️" if self.failure_possible else "✓"
        return f"{status} {component_name} — {self.get_state_display()}"
