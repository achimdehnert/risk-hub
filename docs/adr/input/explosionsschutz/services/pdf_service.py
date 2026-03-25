"""
PDF-Erzeugung des Explosionsschutzdokuments via WeasyPrint.

Struktur des erzeugten Dokuments (nach §6 GefStoffV):
  A  Angaben Betriebsbereich + Verantwortlichkeiten
  B  Betrachtete Anlage
  C  Rechtliche Grundlagen
  D  Mitgeltende Dokumente
  1  Anlagen-/Verfahrensbeschreibung
  2  Gefährdungsbeurteilung (Substitutionsprüfung, Freisetzungsquellen, Zündquellen)
  3  Explosionsschutzkonzept + Schutzmaßnahmen
  4  Zoneneinteilung
  5  Arbeitsmittel (Betriebsmittel mit ATEX-Kennzeichnung)
  6  Organisatorische Maßnahmen
  7  Prüfungen (Wirksamkeitsprüfungen)
  8  Mindestvorschriften (Anhang 1 GefStoffV)
  9  Freigabe
"""
from __future__ import annotations

import io
import uuid
from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from django.utils import timezone

if TYPE_CHECKING:
    from .models import ExplosionConcept


class ExDocumentPdfService:
    """
    Erzeugt das Explosionsschutzdokument als PDF-Bytes.

    Aufruf aus dem Service-Layer (nicht direkt aus Views):
        pdf_bytes = ExDocumentPdfService().generate(concept, tenant_id, user_id)

    Der Caller speichert das PDF via documents-Service und verknüpft
    document-FK mit concept.pdf_document.
    """

    TEMPLATE = "explosionsschutz/pdf/explosionsschutzdokument.html"

    def generate(
        self,
        concept: "ExplosionConcept",
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bytes:
        """Gibt PDF als bytes zurück."""
        try:
            from weasyprint import CSS, HTML
        except ImportError as exc:
            raise RuntimeError(
                "WeasyPrint ist nicht installiert. "
                "Füge 'weasyprint' zu den Dependencies hinzu."
            ) from exc

        context = self._build_context(concept)
        html_string = render_to_string(self.TEMPLATE, context)

        # Base URL für statische Dateien (Logos, CSS)
        from django.conf import settings
        base_url = getattr(settings, "WEASYPRINT_BASEURL", "http://localhost:8000")

        pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf(
            stylesheets=[
                CSS(string=self._get_print_css()),
            ]
        )
        return pdf_bytes

    def _build_context(self, concept: "ExplosionConcept") -> dict:
        from .models import MeasureCategory

        zones = list(
            concept.zones.select_related("trgs_reference").prefetch_related(
                "ignition_assessments"
            )
        )
        measures_primary = list(
            concept.measures.filter(category=MeasureCategory.PRIMARY)
            .select_related("safety_function", "standard_reference")
        )
        measures_secondary = list(
            concept.measures.filter(category=MeasureCategory.SECONDARY)
        )
        measures_constructive = list(
            concept.measures.filter(category=MeasureCategory.CONSTRUCTIVE)
        )
        measures_organisational = list(
            concept.measures.filter(category=MeasureCategory.ORGANISATIONAL)
        )
        equipment = list(
            concept.area.equipment.filter(is_active=True)
            .select_related("equipment_type")
            .prefetch_related("zones", "inspections")
        )
        verification_docs = list(
            concept.verification_documents.select_related("document")
        )
        return {
            "concept": concept,
            "area": concept.area,
            "zones": zones,
            "measures_primary": measures_primary,
            "measures_secondary": measures_secondary,
            "measures_constructive": measures_constructive,
            "measures_organisational": measures_organisational,
            "equipment": equipment,
            "verification_docs": verification_docs,
            "generated_at": timezone.now(),
        }

    @staticmethod
    def _get_print_css() -> str:
        return """
        @page {
            size: A4;
            margin: 2cm 2.5cm 2cm 2.5cm;
            @bottom-right {
                content: "Seite " counter(page) " von " counter(pages);
                font-size: 8pt;
                color: #666;
            }
            @bottom-left {
                content: string(doc-title);
                font-size: 8pt;
                color: #666;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #1a1a1a;
        }
        h1 { font-size: 14pt; color: #1a3560; border-bottom: 2px solid #1a3560; padding-bottom: 4pt; }
        h2 { font-size: 12pt; color: #1a3560; margin-top: 16pt; }
        h3 { font-size: 10pt; color: #333; }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
            margin-bottom: 12pt;
        }
        th {
            background-color: #1a3560;
            color: white;
            padding: 5pt 6pt;
            text-align: left;
        }
        td {
            padding: 4pt 6pt;
            border: 1px solid #ddd;
            vertical-align: top;
        }
        tr:nth-child(even) td { background-color: #f5f7fa; }
        .badge-zone-0   { background: #7b0000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-zone-1   { background: #c45000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-zone-2   { background: #e8a000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-zone-20  { background: #7b0000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-zone-21  { background: #c45000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-zone-22  { background: #e8a000; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .badge-none     { background: #2e7d32; color: white; padding: 1pt 4pt; border-radius: 3pt; }
        .status-effective   { color: #c45000; font-weight: bold; }
        .status-present     { color: #666; }
        .status-not-present { color: #aaa; }
        .section-break { page-break-before: always; }
        .approval-box {
            border: 1px solid #1a3560;
            padding: 12pt;
            margin-top: 24pt;
            background: #f5f7fa;
        }
        .signature-line {
            border-bottom: 1px solid #333;
            margin-top: 36pt;
            width: 200pt;
            display: inline-block;
        }
        """
