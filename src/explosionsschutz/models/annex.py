# src/explosionsschutz/models/annex.py
"""
Anhang-I-Checkliste nach GefStoffV Anhang I Nummer 1.

AnnexIChecklistItem: Seedbare globale Checklisten-Einträge (Phase 1A).
AnnexIChecklistAssessment: Konzept-gebundene Bewertung (Phase 4B — noch nicht implementiert).

Global, tenant-unabhängig — kein tenant_id für Items.

ADR-044 Phase 1A.
"""

from django.db import models


class AnnexIChecklistItem(models.Model):
    """
    Seedbare globale Checklisten-Einträge.

    Enthält die 22 Mindestanforderungen aus GefStoffV Anhang I Nummer 1
    (§ 6(9) GefStoffV, BetrSichV Anhang 1 Abschnitt 3).

    Kein tenant_id — globale Referenzdaten, nicht per Tenant konfigurierbar.
    Seeded via Management-Command `seed_annex_i_checklist`.

    Beispiele:
    - '1.2(3)' — Kennzeichnung der Zonen nach ATEX
    - '1.4(1)' — Auswahl geeigneter Betriebsmittel
    - '1.7(2)' — Explosionsschutzdokument erstellen
    """

    clause_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="Nummerierung nach GefStoffV Anhang I, z.B. '1.2(3)'",
    )
    requirement_text = models.TextField(
        help_text="Vollständiger Anforderungstext",
    )
    category = models.CharField(
        max_length=50,
        help_text=(
            "Fachliche Kategorie für Filterung, z.B. "
            "zone_marking, equipment_selection, documentation, inspection"
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Deaktivierte Einträge werden in neuen Konzepten nicht mehr vorgeschlagen",
    )

    class Meta:
        db_table = "ex_annex_i_checklist_item"
        verbose_name = "Anhang-I-Checklistenpunkt"
        verbose_name_plural = "Anhang-I-Checklistenpunkte"
        ordering = ["clause_number"]

    def __str__(self) -> str:
        excerpt = self.requirement_text[:80]
        if len(self.requirement_text) > 80:
            excerpt += "…"
        return f"{self.clause_number}: {excerpt}"
