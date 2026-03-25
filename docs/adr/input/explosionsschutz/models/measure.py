"""
Schutzmaßnahmen (primär/sekundär/konstruktiv/organisatorisch).
Entspricht Kapitel 7.2 und Kapitel 8 des Explosionsschutzdokuments.
"""
from __future__ import annotations

import uuid
from enum import StrEnum

from django.db import models


class MeasureCategory(StrEnum):
    """
    T-O-P-S Hierarchie der Schutzmaßnahmen.
    Primär → Sekundär → Konstruktiv → Organisatorisch.
    """
    PRIMARY = "primary"           # Technisch-primär: Vermeidung ex. Atmosphäre
    SECONDARY = "secondary"       # Technisch-sekundär: Zündquellenvermeidung
    CONSTRUCTIVE = "constructive" # Konstruktiv: Schadensminimierung
    ORGANISATIONAL = "organisational"  # Organisatorisch: Betriebsanweisungen, Unterweisungen


class ProtectionMeasure(models.Model):
    """
    Einzelne Schutzmaßnahme innerhalb eines Ex-Konzepts.
    FK zu MeasureCatalog optional – ermöglicht Wiederverwendung von Vorlagen.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Umsetzung"
        DONE = "done", "Umgesetzt"
        OBSOLETE = "obsolete", "Entfallen"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(
        "concept.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="measures",
    )
    category = models.CharField(
        max_length=20,
        choices=[(c.value, c.value) for c in MeasureCategory],
    )

    # Vorlage (optional)
    catalog_reference = models.ForeignKey(
        "master_data.MeasureCatalog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    title = models.CharField(max_length=300)
    description = models.TextField()
    justification = models.TextField(
        blank=True,
        help_text="Begründung/Nachweis der Wirksamkeit",
    )

    # MSR-Sicherheitsfunktion (nur wenn Maßnahme eine Steuerung/Regelung ist)
    safety_function = models.ForeignKey(
        "master_data.SafetyFunction",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="measures",
        help_text="MSR-Sicherheitsfunktion nach TRGS 725 (nur wenn zutreffend)",
    )

    # Zuständigkeit
    responsible_id = models.UUIDField(null=True, blank=True)
    responsible_name = models.CharField(max_length=200, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DONE
    )
    completion_date = models.DateField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)

    # Normativer Nachweis
    standard_reference = models.ForeignKey(
        "master_data.ReferenceStandard",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_protection_measure"
        ordering = ["category", "sort_order", "title"]

    def __str__(self) -> str:
        return f"[{self.category}] {self.title}"
