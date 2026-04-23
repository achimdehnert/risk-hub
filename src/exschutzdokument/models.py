# src/exschutzdokument/models.py
"""
Ex-Schutzdokument UC-2 — Thin Wrapper App (~50 Zeilen).

ExSchutzGutachten: Domain-Kontext-Anker für iil-doc-templates.
Kein eigenes Fach-Datenmodell — delegiert an iil-doc-templates für
PDF-Export, Prefill und Strukturierung.

Gemäß ADR-044 Section 4.2 (Option C): Diese App hat KEINE eigene
Freigabe-Logik, KEINE eigenen Snapshot-Mechanismen und KEINEN
eigenen Workflow. Ausschließlich als Brücke zu iil-doc-templates.

ADR-044 Phase 6.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class ExSchutzGutachten(models.Model):
    """
    UC-2 Gutachten: Freitext-basiertes Ex-Schutzdokument via iil-doc-templates.

    compliance_anchor: Optionale Verknüpfung mit einem UC-1 Konzept
    für strukturierte Compliance-Daten-Vorbelegung (prefill via fieldprefill).

    Alle Dokument-Logik (PDF, Versionierung, Freigabe) liegt in iil-doc-templates.
    """

    title = models.CharField(max_length=200)
    tenant_id = models.UUIDField(db_index=True)

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ex_schutz_gutachten",
        help_text="ADR-041 Container. UC-2 ist direkt im Projekt verankert.",
    )

    compliance_anchor = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gutachten",
        help_text=(
            "Optional: UC-1-Konzept als Datenquelle für KI-Prefill. "
            "Ermöglicht fieldprefill.prefill_field() mit strukturierten Konzept-Daten."
        ),
    )

    objects = TenantManager()

    class Meta:
        db_table = "ex_schutz_gutachten"
        verbose_name = "Ex-Schutz-Gutachten"
        verbose_name_plural = "Ex-Schutz-Gutachten"

    def __str__(self) -> str:
        return self.title
