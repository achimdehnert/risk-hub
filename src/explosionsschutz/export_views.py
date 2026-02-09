"""Export views for Explosionsschutz documents (DOCX + PDF)."""

import io
import logging

from django.db.models import Q
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from .document_generator import ExSchutzDocumentGenerator
from .models import ExplosionConcept

logger = logging.getLogger(__name__)


class ConceptExportDocxView(View):
    """Download Ex-Schutz-Dokument as DOCX."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter)
            .select_related("area"),
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
                "application/vnd.openxmlformats-"
                "officedocument.wordprocessingml.document"
            ),
        )


class ConceptExportPdfView(View):
    """Download Ex-Schutz-Dokument as PDF via WeasyPrint."""

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        tenant_id = getattr(request, "tenant_id", None)
        base_filter = Q(tenant_id=tenant_id) if tenant_id else Q()

        concept = get_object_or_404(
            ExplosionConcept.objects.filter(base_filter)
            .select_related("area"),
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
            ExplosionConcept.objects.filter(base_filter)
            .select_related("area"),
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
