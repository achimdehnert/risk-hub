"""Export views for Explosionsschutz documents (DOCX + PDF + GAEB)."""

import io
import logging
from decimal import Decimal

from django.db.models import Q
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .document_generator import ExSchutzDocumentGenerator
from .models import Equipment, ExplosionConcept, ProtectionMeasure

logger = logging.getLogger(__name__)


class ConceptExportDocxView(View):
    """Download Ex-Schutz-Dokument as DOCX."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk,
        )

        generator = ExSchutzDocumentGenerator(concept)
        generator.create_document()
        buf = generator.save_to_buffer()
        filename = generator.get_filename()

        return FileResponse(
            buf,
            as_attachment=True,
            filename=filename,
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )


class ConceptExportPdfView(View):
    """Download Ex-Schutz-Dokument as PDF via WeasyPrint."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk,
        )

        generator = ExSchutzDocumentGenerator(concept)
        html_content = generator.get_html_preview()

        # Wrap in full HTML document for WeasyPrint
        full_html = _wrap_html(
            html_content,
            title=f"Ex-Schutz-Dokument: {concept.title}",
        )

        try:
            from weasyprint import HTML

            pdf_bytes = HTML(string=full_html).write_pdf()
        except ImportError:
            logger.warning("WeasyPrint not installed, returning HTML")
            return HttpResponse(
                full_html,
                content_type="text/html",
            )

        filename = generator.get_filename().replace(".docx", ".pdf")
        buf = io.BytesIO(pdf_bytes)

        return FileResponse(
            buf,
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )


class ConceptPreviewView(View):
    """HTML preview of the Ex-Schutz-Dokument."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk,
        )

        generator = ExSchutzDocumentGenerator(concept)
        html_preview = generator.get_html_preview()

        return render(
            request,
            "explosionsschutz/concepts/export_preview.html",
            {
                "concept": concept,
                "html_preview": html_preview,
            },
        )


class ZoneMapView(View):
    """Interactive SVG zone map for a concept."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk,
        )

        zones = concept.zones.all().order_by("zone_type")
        equipment = Equipment.objects.filter(
            zone__concept=concept,
            status="active",
        ).select_related("equipment_type", "zone")

        # Assign default positions for SVG rendering
        zone_data = _assign_zone_positions(zones)

        return render(
            request,
            "explosionsschutz/concepts/zone_map.html",
            {
                "concept": concept,
                "zones": zone_data,
                "equipment": equipment,
            },
        )


class ConceptExportGAEBView(View):
    """GAEB X84 Export der Schutzmaßnahmen eines Explosionsschutzkonzepts."""

    _CATEGORY_MAP = {
        ProtectionMeasure.Category.PRIMARY: ("01", "Primäre Maßnahmen (Vermeidung)"),
        ProtectionMeasure.Category.SECONDARY: ("02", "Sekundäre Maßnahmen (Zündquellenvermeidung)"),
        ProtectionMeasure.Category.TERTIARY: ("03", "Tertiäre Maßnahmen (Auswirkungsbegrenzung)"),
        ProtectionMeasure.Category.ORGANIZATIONAL: ("04", "Organisatorische Maßnahmen"),
    }

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        from nl2cad.gaeb.generator import GAEBGenerator
        from nl2cad.gaeb.models import (
            GAEBPhase,
            Leistungsverzeichnis,
            LosGruppe,
            Position,
        )

        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter).select_related("area"),
            pk=pk,
        )

        format_type = request.GET.get("format", "excel")

        lv = Leistungsverzeichnis(
            projekt_name=(f"Ex-Schutz: {concept.title} — {concept.area.name}"),
            projekt_nummer=str(concept.pk)[:8],
            phase=GAEBPhase.X84,
        )

        measures_qs = ProtectionMeasure.objects.filter(base_filter, concept=concept).order_by(
            "category", "title"
        )

        # Gruppiere Maßnahmen nach Kategorie in Lose
        by_category: dict[str, list[ProtectionMeasure]] = {}
        for measure in measures_qs:
            by_category.setdefault(measure.category, []).append(measure)

        for cat_value, (los_oz, los_bezeichnung) in self._CATEGORY_MAP.items():
            measures_in_cat = by_category.get(cat_value, [])
            if not measures_in_cat:
                continue
            positionen = [
                Position(
                    oz=f"{los_oz}.{i + 1:03d}",
                    kurztext=m.title,
                    langtext=m.description or "",
                    menge=Decimal("1"),
                    einheit="Stk",
                )
                for i, m in enumerate(measures_in_cat)
            ]
            lv.lose.append(
                LosGruppe(
                    oz=los_oz,
                    bezeichnung=los_bezeichnung,
                    positionen=positionen,
                )
            )

        generator = GAEBGenerator()
        safe_name = concept.title.replace(" ", "_")[:40]

        if format_type == "xml":
            output = generator.generate_xml(lv)
            content_type = "application/xml"
            filename = f"LV_{safe_name}_v{concept.version}.x84"
        else:
            output = generator.generate_excel(lv)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"LV_{safe_name}_v{concept.version}.xlsx"

        response = HttpResponse(output.read(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _assign_zone_positions(zones):
    """Assign SVG positions to zones for concentric rendering."""
    zone_list = list(zones)
    cx, cy = 400, 300
    radii = {"0": 60, "20": 60, "1": 120, "21": 120, "2": 180, "22": 180}

    for zone in zone_list:
        zone.cx = cx
        zone.cy = cy
        zone.radius = radii.get(zone.zone_type, 100)
        zone.text_y = cy - zone.radius + 15

    # Sort so outer zones render first (largest radius first)
    zone_list.sort(key=lambda z: z.radius, reverse=True)
    return zone_list


def _wrap_html(content: str, title: str = "") -> str:
    """Wrap HTML content in a full document for PDF rendering."""
    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-center {{
                content: "Seite " counter(page) " von " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}
        body {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #333;
        }}
        h1 {{ font-size: 18pt; color: #c2410c; }}
        h2 {{ font-size: 14pt; color: #333; margin-top: 24pt; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
            font-size: 10pt;
        }}
        td, th {{
            border: 1px solid #ccc;
            padding: 6pt 8pt;
            text-align: left;
        }}
        th {{ background: #f3f4f6; font-weight: bold; }}
        .cover {{
            text-align: center;
            padding: 60pt 0 40pt;
            page-break-after: always;
        }}
        .cover h1 {{
            font-size: 24pt;
            margin-bottom: 8pt;
        }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
