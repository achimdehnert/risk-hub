# src/explosionsschutz/models/reference.py
"""
Hierarchische Absatz-Referenzen für Regelwerke (DGUV, TRGS, EN-Normen).

ReferenceStandardClause: Seedbare globale Klausel-Referenzen.
Global, tenant-unabhängig — kein tenant_id. Nur Seed-Daten via Management-Commands.

ADR-044 Phase 1A.
"""

from django.db import models


class ReferenceStandardClause(models.Model):
    """
    Hierarchische Absatz-Referenz für ein Regelwerk.

    Seedbare globale Daten (kein Tenant-Bezug). Verknüpft über FK mit
    ReferenceStandard (z.B. DGUV 113-001). Wird in ZoneDefinition
    als `derived_from_clause` FK referenziert, um die normative Begründung
    einer Zoneneinteilung strukturiert abzulegen.

    Beispiele:
    - DGUV 113-001 Abschnitt 2.3.1.2 b3) — Holzstaub Zone 22 Abfüllraum
    - TRGS 722 Abschnitt 5.4 — Primärer Explosionsschutz
    """

    standard = models.ForeignKey(
        "explosionsschutz.ReferenceStandard",
        on_delete=models.CASCADE,
        related_name="clauses",
    )
    clause_path = models.JSONField(
        help_text="Hierarchische Absatz-Nummerierung, z.B. [2, 3, 1, 2, 'b3']",
    )
    clause_label = models.CharField(
        max_length=50,
        help_text="Lesbare Darstellung, z.B. '2.3.1.2 b3)'",
    )
    title = models.CharField(max_length=200, blank=True)
    content_excerpt = models.TextField(
        blank=True,
        help_text="Auszug aus dem Regelwerkstext (nicht vollständig, nur für Kontext)",
    )

    class Meta:
        db_table = "ex_reference_standard_clause"
        verbose_name = "Regelwerks-Klausel"
        verbose_name_plural = "Regelwerks-Klauseln"
        ordering = ["standard", "clause_label"]
        indexes = [
            models.Index(
                fields=["standard", "clause_label"],
                name="idx_ref_clause_std_label",
            ),
        ]

    def __str__(self) -> str:
        standard_code = self.standard.code if self.standard_id else ""
        label = f"{standard_code} {self.clause_label}".strip()
        if self.title:
            return f"{label} — {self.title}"
        return label
