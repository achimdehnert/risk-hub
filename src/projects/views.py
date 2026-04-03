"""Project views (ADR-041).

Views handle HTTP only — business logic in services.py.
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from projects.models import (
    DocumentSection,
    DocumentTemplate,
    OutputDocument,
    Project,
    ProjectDocument,
)
from projects.services import (
    CreateProjectCmd,
    create_project,
    get_subscribed_modules,
    recommend_modules_from_description,
)

logger = logging.getLogger(__name__)


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """List all projects for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    projects = (
        Project.objects.filter(tenant_id=request.tenant_id)
        .prefetch_related("modules")
        .order_by("-created_at")[:100]
    )
    return render(
        request,
        "projects/project_list.html",
        {"projects": projects},
    )


@login_required
def project_create(request: HttpRequest) -> HttpResponse:
    """Create a new project with KI module recommendation."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    from tenancy.models import Site

    sites = Site.objects.filter(tenant_id=request.tenant_id)
    subscribed = get_subscribed_modules(request.tenant_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        site_name = request.POST.get("site_name", "").strip()
        description = request.POST.get("description", "")
        project_number = request.POST.get("project_number", "")
        client_name = request.POST.get("client_name", "")
        selected = request.POST.getlist("modules")
        declined = request.POST.getlist("declined_modules")

        if not name or not site_name:
            recommendations = recommend_modules_from_description(
                description, subscribed,
            )
            return render(
                request,
                "projects/project_create.html",
                {
                    "sites": sites,
                    "recommendations": recommendations,
                    "subscribed_modules": subscribed,
                    "error": "Name und Standort sind Pflichtfelder.",
                    "form_data": request.POST,
                },
            )

        # Resolve or auto-create Site
        from projects.services import get_or_create_site
        org = request.user.tenancy_memberships.filter(
            tenant_id=request.tenant_id,
        ).first().organization
        site, created = get_or_create_site(
            request.tenant_id, site_name, org,
        )

        # Build recommendations for storage
        recommendations = recommend_modules_from_description(
            description, subscribed,
        )

        project = create_project(
            CreateProjectCmd(
                tenant_id=str(request.tenant_id),
                site_id=str(site.pk),
                name=name,
                description=description,
                project_number=project_number,
                client_name=client_name,
                created_by_id=request.user.pk,
                selected_modules=selected,
                declined_modules=declined,
                module_recommendations=recommendations,
            )
        )
        return redirect("projects:project-detail", pk=project.pk)

    # GET: empty form
    recommendations = recommend_modules_from_description(
        "", subscribed,
    )
    return render(
        request,
        "projects/project_create.html",
        {
            "sites": sites,
            "recommendations": recommendations,
            "subscribed_modules": subscribed,
        },
    )


@login_required
def project_recommend_modules(
    request: HttpRequest,
) -> HttpResponse:
    """HTMX endpoint: return module recommendations for description."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    description = request.POST.get("description", "")
    subscribed = get_subscribed_modules(request.tenant_id)
    recommendations = recommend_modules_from_description(
        description, subscribed,
    )
    return render(
        request,
        "projects/partials/_module_recommendations.html",
        {
            "recommendations": recommendations,
            "subscribed_modules": subscribed,
        },
    )


@login_required
def project_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Project detail / dashboard view."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project.objects.prefetch_related("modules"),
        pk=pk,
        tenant_id=request.tenant_id,
    )

    from projects.services import AVAILABLE_MODULES

    active_modules = project.modules.filter(status="active")
    module_details = []
    for pm in active_modules:
        meta = AVAILABLE_MODULES.get(pm.module, {})
        module_details.append({
            "code": pm.module,
            "label": meta.get("label", pm.module),
            "icon": meta.get("icon", "box"),
            "description": meta.get("description", ""),
        })

    declined = project.modules.filter(status="declined")
    documents = project.documents.all()[:20]
    output_docs = project.output_documents.all()[:20]

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "module_details": module_details,
            "declined_modules": declined,
            "documents": documents,
            "output_docs": output_docs,
        },
    )


@login_required
def document_upload(request: HttpRequest, pk: int) -> HttpResponse:
    """Upload a document to a project."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project, pk=pk, tenant_id=request.tenant_id,
    )

    if request.method == "POST":
        files = request.FILES.getlist("files")
        doc_type = request.POST.get("doc_type", "other")

        from projects.services import upload_project_document
        for f in files:
            upload_project_document(
                tenant_id=request.tenant_id,
                project=project,
                file=f,
                doc_type=doc_type,
                uploaded_by=request.user,
            )

        return redirect("projects:project-detail", pk=pk)

    return render(
        request,
        "projects/document_upload.html",
        {
            "project": project,
            "doc_types": ProjectDocument.DocType.choices,
        },
    )


@login_required
def document_delete(
    request: HttpRequest, pk: int, doc_pk: int,
) -> HttpResponse:
    """Delete a project document."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    doc = get_object_or_404(
        ProjectDocument,
        pk=doc_pk,
        project__pk=pk,
        tenant_id=request.tenant_id,
    )
    if request.method == "POST":
        from projects.services import delete_project_document
        delete_project_document(doc)
    return redirect("projects:project-detail", pk=pk)


# --- OutputDocument (Dokument erstellen) ---

DOCUMENT_KIND_META = {
    "ex_schutz": {
        "label": "Explosionsschutzdokument",
        "icon": "zap",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_betrieb", "2. Beschreibung des Betriebs"),
            ("3_stoffe", "3. Verwendete Gefahrstoffe"),
            ("4_zonen", "4. Zoneneinteilung"),
            ("5_zuendquellen", "5. Zündquellenanalyse"),
            ("6_massnahmen", "6. Schutzmaßnahmen"),
            ("7_betriebsmittel", "7. Betriebsmittel"),
            ("8_pruefung", "8. Prüfung und Wartung"),
            ("9_unterweisung", "9. Unterweisung"),
            ("10_zusammenfassung", "10. Zusammenfassung"),
        ],
    },
    "gbu": {
        "label": "Gefährdungsbeurteilung",
        "icon": "clipboard-check",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_taetigkeit", "2. Tätigkeit / Arbeitsplatz"),
            ("3_gefaehrdungen", "3. Gefährdungen"),
            ("4_massnahmen", "4. Schutzmaßnahmen"),
            ("5_bewertung", "5. Risikobewertung"),
            ("6_ergebnis", "6. Ergebnis"),
        ],
    },
    "brandschutz": {
        "label": "Brandschutznachweis",
        "icon": "flame",
        "default_sections": [
            ("1_allgemeines", "1. Allgemeines"),
            ("2_baulich", "2. Baulicher Brandschutz"),
            ("3_anlagentechnisch", "3. Anlagentechnischer Brandschutz"),
            ("4_organisatorisch", "4. Organisatorischer Brandschutz"),
            ("5_flucht", "5. Flucht- und Rettungswege"),
            ("6_ergebnis", "6. Ergebnis"),
        ],
    },
}


@login_required
def output_document_create(
    request: HttpRequest, pk: int,
) -> HttpResponse:
    """Create a new output document for a project."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project, pk=pk, tenant_id=request.tenant_id,
    )
    templates = DocumentTemplate.objects.filter(
        tenant_id=request.tenant_id,
    ).exclude(
        status=DocumentTemplate.Status.ARCHIVED,
    ).order_by("kind", "name")

    if request.method == "POST":
        template_id = request.POST.get("template_id", "")
        title = request.POST.get("title", "").strip()

        if not template_id or not title:
            return render(
                request,
                "projects/output_document_create.html",
                {
                    "project": project,
                    "templates": templates,
                    "kinds": DOCUMENT_KIND_META,
                    "error": "Vorlage und Titel sind Pflichtfelder.",
                    "form_data": request.POST,
                },
            )

        tmpl = get_object_or_404(
            DocumentTemplate,
            pk=template_id,
            tenant_id=request.tenant_id,
        )

        # PDF import (optional)
        pdf_file = request.FILES.get("pdf_file")
        imported_values = {}
        if pdf_file:
            text = _extract_pdf_text(pdf_file)
            if text:
                try:
                    structure = json.loads(tmpl.structure_json)
                except (json.JSONDecodeError, TypeError):
                    structure = {"sections": []}
                imported_values = _import_text_into_template(
                    text, structure,
                )
                messages.info(
                    request,
                    f"Inhalte aus '{pdf_file.name}' importiert.",
                )
            else:
                messages.warning(
                    request,
                    "Kein Text aus PDF extrahiert.",
                )

        from projects.services import create_output_document
        doc = create_output_document(
            tenant_id=request.tenant_id,
            project=project,
            template=tmpl,
            title=title,
            created_by=request.user,
            imported_values=imported_values,
        )

        return redirect(
            "projects:output-document-edit",
            pk=pk,
            doc_pk=doc.pk,
        )

    return render(
        request,
        "projects/output_document_create.html",
        {
            "project": project,
            "templates": templates,
            "kinds": DOCUMENT_KIND_META,
        },
    )


@login_required
def output_document_edit(
    request: HttpRequest, pk: int, doc_pk: int,
) -> HttpResponse:
    """Edit an output document's sections."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project, pk=pk, tenant_id=request.tenant_id,
    )
    doc = get_object_or_404(
        OutputDocument.objects.prefetch_related("sections"),
        pk=doc_pk,
        project=project,
    )
    documents = project.documents.all()

    return render(
        request,
        "projects/output_document_edit.html",
        {
            "project": project,
            "doc": doc,
            "sections": doc.sections.all(),
            "documents": documents,
        },
    )


@login_required
def section_save(
    request: HttpRequest, pk: int, doc_pk: int, sec_pk: int,
) -> HttpResponse:
    """HTMX: Save a single section's content."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    section = get_object_or_404(
        DocumentSection,
        pk=sec_pk,
        document__pk=doc_pk,
        document__project__pk=pk,
        document__tenant_id=request.tenant_id,
    )

    if request.method == "POST":
        section.content = request.POST.get("content", "")
        section.is_ai_generated = False

        # Collect structured field values
        try:
            fields = json.loads(section.fields_json or "[]")
        except (json.JSONDecodeError, TypeError):
            fields = []

        values = {}
        for field in fields:
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            form_key = f"{section.section_key}__{fkey}"

            if ftype == "table":
                # Collect table rows
                columns = field.get("columns", [])
                rows = []
                row_idx = 0
                while True:
                    row = []
                    found = False
                    for ci in range(len(columns)):
                        cell_key = f"{form_key}__row_{row_idx}__col_{ci}"
                        val = request.POST.get(cell_key, "")
                        if val:
                            found = True
                        row.append(val)
                    if not found:
                        break
                    rows.append(row)
                    row_idx += 1
                values[fkey] = rows
            elif ftype == "boolean":
                values[fkey] = request.POST.get(form_key, "false")
            else:
                val = request.POST.get(form_key, "")
                values[fkey] = val
                if ftype == "textarea" and val and not section.content:
                    section.content = val

        section.values_json = json.dumps(
            values, ensure_ascii=False,
        )
        section.save(
            update_fields=[
                "content", "values_json",
                "is_ai_generated", "updated_at",
            ],
        )

    return render(
        request,
        "projects/partials/_section_card.html",
        {
            "section": section,
            "project": section.document.project,
            "doc": section.document,
        },
    )


# ─── LLM Prefill ─────────────────────────────────────────────


@login_required
def section_llm_prefill(
    request: HttpRequest, pk: int, doc_pk: int, sec_pk: int,
) -> HttpResponse:
    """HTMX: Generate AI content for a section field."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    section = get_object_or_404(
        DocumentSection,
        pk=sec_pk,
        document__pk=doc_pk,
        document__project__pk=pk,
        document__tenant_id=request.tenant_id,
    )

    field_key = request.POST.get("field_key", "")
    llm_hint = request.POST.get("llm_hint", "")

    # Build prompt from document context
    doc = section.document
    project = doc.project
    prompt = (
        f"Du bist ein Experte für {doc.kind or 'Arbeitsschutz'}-Dokumentation. "
        f"Projekt: {project.name}. "
        f"Dokument: {doc.title}. "
        f"Abschnitt: {section.title}. "
        f"Aufgabe: {llm_hint or section.title}. "
        f"Schreibe einen fachlich korrekten, professionellen Text "
        f"für diesen Abschnitt auf Deutsch."
    )

    generated = ""
    try:
        from aifw.service import sync_completion
        result = sync_completion(
            messages=[{"role": "user", "content": prompt}],
            model="groq/llama-3.3-70b-versatile",
            max_tokens=2000,
        )
        generated = result.get("content", "")
    except ImportError:
        logger.warning("aifw not available for LLM prefill")
        generated = f"[KI nicht verfügbar — bitte manuell ausfüllen: {section.title}]"
    except Exception as exc:
        logger.exception("LLM prefill failed: %s", exc)
        generated = f"[Fehler bei KI-Generierung: {exc}]"

    # Return textarea partial with generated content
    form_key = f"{section.section_key}__{field_key}" if field_key else "content"
    return HttpResponse(
        f'<textarea name="{form_key}" rows="6" '
        f'class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm '
        f'focus:ring-orange-500 focus:border-orange-500 resize-y">'
        f"{generated}</textarea>",
        content_type="text/html",
    )


# ─── PDF Export ──────────────────────────────────────────────


@login_required
def output_document_pdf(
    request: HttpRequest, pk: int, doc_pk: int,
) -> HttpResponse:
    """Generate PDF for an output document via WeasyPrint."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    doc = get_object_or_404(
        OutputDocument.objects.prefetch_related("sections"),
        pk=doc_pk,
        project__pk=pk,
        tenant_id=request.tenant_id,
    )
    sections = doc.sections.all()

    # Render HTML for PDF
    html_parts = [
        f"<h1>{doc.title}</h1>",
        f"<p><small>Version {doc.version} · "
        f"{doc.get_status_display()} · "
        f"{doc.updated_at.strftime('%d.%m.%Y')}</small></p>",
    ]

    for section in sections:
        html_parts.append(f"<h2>{section.title}</h2>")

        try:
            fields = json.loads(section.fields_json or "[]")
            values = json.loads(section.values_json or "{}")
        except (json.JSONDecodeError, TypeError):
            fields = []
            values = {}

        if fields:
            for field in fields:
                fkey = field["key"]
                ftype = field.get("type", "textarea")
                val = values.get(fkey, "")

                if ftype == "table" and isinstance(val, list):
                    cols = field.get("columns", [])
                    if cols and val:
                        html_parts.append(
                            "<table border='1' cellpadding='4' "
                            "cellspacing='0' style='border-collapse:"
                            "collapse; width:100%; font-size:10pt;'>"
                        )
                        html_parts.append("<thead><tr>")
                        for c in cols:
                            html_parts.append(
                                f"<th style='background:#f0f0f0'>"
                                f"{c}</th>"
                            )
                        html_parts.append("</tr></thead><tbody>")
                        for row in val:
                            html_parts.append("<tr>")
                            for cell in row:
                                html_parts.append(f"<td>{cell}</td>")
                            html_parts.append("</tr>")
                        html_parts.append("</tbody></table>")
                elif val:
                    html_parts.append(
                        f"<p>{str(val).replace(chr(10), '<br>')}</p>"
                    )
        elif section.content:
            html_parts.append(
                f"<p>{section.content.replace(chr(10), '<br>')}</p>"
            )

    full_html = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<style>"
        "body{font-family:Arial,sans-serif;font-size:11pt;"
        "line-height:1.5;margin:2cm;}"
        "h1{font-size:18pt;color:#1a1a1a;}"
        "h2{font-size:14pt;color:#333;margin-top:1.5em;border-bottom:"
        "1px solid #ddd;padding-bottom:4px;}"
        "table{margin:0.5em 0;}"
        "</style></head><body>"
        + "\n".join(html_parts)
        + "</body></html>"
    )

    try:
        import weasyprint
        pdf_bytes = weasyprint.HTML(
            string=full_html,
        ).write_pdf()
        response = HttpResponse(
            pdf_bytes, content_type="application/pdf",
        )
        safe_title = doc.title.replace('"', "'")
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_title}.pdf"'
        )
        return response
    except (ImportError, OSError) as exc:
        logger.warning("WeasyPrint not available: %s", exc)
        messages.error(
            request,
            "PDF-Export nicht verfügbar "
            "(WeasyPrint nicht installiert).",
        )
        return redirect(
            "projects:output-document-edit",
            pk=pk, doc_pk=doc_pk,
        )


# ─── DocumentTemplate CRUD ──────────────────────────────────


@login_required
def template_list(request: HttpRequest) -> HttpResponse:
    """List all document templates for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    templates = DocumentTemplate.objects.filter(
        tenant_id=request.tenant_id,
    ).order_by("-updated_at")

    return render(
        request,
        "projects/templates/template_list.html",
        {"templates": templates},
    )


@login_required
def template_create(request: HttpRequest) -> HttpResponse:
    """Create a new empty document template."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        kind = request.POST.get("kind", "").strip()
        desc = request.POST.get("description", "").strip()

        if not name:
            messages.error(request, "Name ist Pflichtfeld.")
            return render(
                request,
                "projects/templates/template_create.html",
                {"form_data": request.POST},
            )

        structure = {
            "sections": [
                {
                    "key": "section_1",
                    "label": "1. Allgemeines",
                    "fields": [{
                        "key": "inhalt",
                        "label": "Inhalt",
                        "type": "textarea",
                        "required": False,
                    }],
                },
            ],
        }

        from projects.services import create_template
        tmpl = create_template(
            tenant_id=request.tenant_id,
            name=name,
            kind=kind,
            description=desc,
            structure=structure,
        )
        messages.success(request, f"Vorlage '{name}' erstellt.")
        return redirect(
            "projects:template-edit", tmpl_pk=tmpl.pk,
        )

    return render(
        request,
        "projects/templates/template_create.html",
    )


@login_required
def template_upload(request: HttpRequest) -> HttpResponse:
    """Upload PDF to create a document template."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    if request.method == "POST":
        pdf_file = request.FILES.get("pdf_file")
        if not pdf_file:
            messages.error(request, "Keine Datei ausgewählt.")
            return render(
                request,
                "projects/templates/template_upload.html",
            )

        name = request.POST.get("name", "").strip()
        if not name:
            name = pdf_file.name.replace(".pdf", "").replace(
                "_", " ",
            )
        kind = request.POST.get("kind", "").strip()

        text = _extract_pdf_text(pdf_file)
        if not text:
            messages.warning(
                request,
                "Kein Text aus PDF extrahiert. "
                "Leere Vorlage erstellt.",
            )

        structure = (
            _text_to_structure(text)
            if text
            else {"sections": []}
        )

        from projects.services import create_template
        tmpl = create_template(
            tenant_id=request.tenant_id,
            name=name,
            kind=kind,
            description=request.POST.get("description", ""),
            structure=structure,
            source_filename=pdf_file.name,
            source_text=text or "",
        )
        messages.success(
            request,
            f"Vorlage '{name}' aus PDF erstellt "
            f"({tmpl.section_count} Abschnitte).",
        )
        return redirect(
            "projects:template-edit", tmpl_pk=tmpl.pk,
        )

    return render(
        request,
        "projects/templates/template_upload.html",
    )


@login_required
def template_edit(
    request: HttpRequest, tmpl_pk: int,
) -> HttpResponse:
    """Edit a document template's structure."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    tmpl = get_object_or_404(
        DocumentTemplate,
        pk=tmpl_pk,
        tenant_id=request.tenant_id,
    )

    if request.method == "POST":
        raw_json = request.POST.get("structure_json", "")
        try:
            structure = json.loads(raw_json)
            if "sections" not in structure:
                raise ValueError("Missing 'sections' key")
        except (json.JSONDecodeError, ValueError) as exc:
            messages.error(request, f"Ungültiges JSON: {exc}")
            return render(
                request,
                "projects/templates/template_edit.html",
                {
                    "tmpl": tmpl,
                    "structure": {"sections": []},
                    "structure_json": raw_json,
                },
            )

        from projects.services import update_template
        update_template(
            tmpl,
            structure=structure,
            name=request.POST.get("name", tmpl.name),
            description=request.POST.get(
                "description", tmpl.description,
            ),
            status=request.POST.get("status", tmpl.status),
        )

        messages.success(request, "Vorlage gespeichert.")
        return redirect("projects:template-list")

    try:
        structure = json.loads(tmpl.structure_json)
    except (json.JSONDecodeError, TypeError):
        structure = {"sections": []}

    return render(
        request,
        "projects/templates/template_edit.html",
        {
            "tmpl": tmpl,
            "structure": structure,
            "structure_json": json.dumps(
                structure, ensure_ascii=False, indent=2,
            ),
        },
    )


@login_required
def template_delete(
    request: HttpRequest, tmpl_pk: int,
) -> HttpResponse:
    """Delete a document template."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    tmpl = get_object_or_404(
        DocumentTemplate,
        pk=tmpl_pk,
        tenant_id=request.tenant_id,
    )
    if request.method == "POST":
        from projects.services import delete_template
        delete_template(tmpl)
        messages.success(request, "Vorlage gelöscht.")
    return redirect("projects:template-list")


# ─── PDF extraction helpers (from explosionsschutz) ─────────


def _extract_pdf_text(pdf_file) -> str:
    """Extract text from PDF file."""
    try:
        import pdfplumber
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        parts = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pdfplumber failed: %s", exc)

    try:
        import PyPDF2
        if hasattr(pdf_file, "seek"):
            pdf_file.seek(0)
        reader = PyPDF2.PdfReader(pdf_file)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("PyPDF2 failed: %s", exc)

    return ""


def _clean_toc(title: str) -> str:
    """Remove TOC dots and page numbers."""
    import re
    title = re.sub(r"\s*[.·…]{2,}\s*\d*\s*$", "", title)
    title = re.sub(r"\s+\d{1,4}\s*$", "", title)
    return title.strip()


def _split_cols(line: str) -> list[str]:
    """Split a line by tab or multi-space."""
    import re
    if "\t" in line:
        parts = [c.strip() for c in line.split("\t")]
    else:
        parts = [c.strip() for c in re.split(r"\s{2,}", line)]
    return [p for p in parts if p]


def _is_valid_heading(num: str, title: str, line: str) -> bool:
    """Filter false positives: table rows, PLZ, measurements."""
    import re
    top = int(num.split(".")[0])
    if top > 30:
        return False
    if sum(1 for c in title if c.isalpha()) < 2:
        return False
    if len(_split_cols(line)) >= 3:
        return False
    if re.match(
        r"^(m[²³]?/[hs]|kg|cm|mm|l/|bar|°C|kW)\b",
        title, re.IGNORECASE,
    ):
        return False
    return True


def _detect_table(content: str) -> list[str] | None:
    """Detect table columns in section content.

    Strategies:
    1. Tab-separated or multi-space lines (classic)
    2. Pipe-separated (|col1|col2|)
    3. Known German table headers (Nr., Zone, etc.)
    4. Header-like first line followed by data rows
    """
    import re
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return None

    # Strategy 1: tab / multi-space structured lines
    structured = [
        ln for ln in lines
        if "\t" in ln or ln.count("  ") >= 2
    ]
    if len(structured) >= 2:
        cols = _split_cols(structured[0])
        if 2 <= len(cols) <= 10:
            return cols

    # Strategy 2: pipe-separated table
    pipe_lines = [
        ln for ln in lines if ln.count("|") >= 2
    ]
    if len(pipe_lines) >= 2:
        cols = [
            c.strip() for c in pipe_lines[0].split("|")
            if c.strip()
        ]
        if 2 <= len(cols) <= 10:
            return cols

    # Strategy 3: known German table header patterns
    header_pat = re.compile(
        r"(Nr\.?|Nummer|Zone|Bereich|Anlagenteil|"
        r"Bemerkung|Schutzma[sß]nahm|Ma[sß]nahm|"
        r"Beschreibung|Bezeichnung|Menge|Einheit|"
        r"Ergebnis|Bewertung|Kategorie|Status|"
        r"Gefährdung|Risiko|Häufigkeit|Typ)",
        re.IGNORECASE,
    )
    for i, line in enumerate(lines[:10]):
        stripped = line.strip()
        matches = header_pat.findall(stripped)
        if len(matches) >= 2:
            cols = _split_cols(stripped)
            if len(cols) < 2:
                # Try splitting by known separators
                cols = [
                    c.strip()
                    for c in re.split(r"\s{2,}|\t", stripped)
                    if c.strip()
                ]
            if 2 <= len(cols) <= 10:
                return cols
            # Fallback: use the matched keywords as cols
            if 2 <= len(matches) <= 10:
                return matches

    # Strategy 4: short first line (potential header)
    # followed by lines with similar structure
    first = lines[0].strip()
    if len(first) < 120:
        first_cols = _split_cols(first)
        if 2 <= len(first_cols) <= 10:
            # Check if following lines have similar col count
            similar = 0
            for ln in lines[1:min(6, len(lines))]:
                lcols = _split_cols(ln.strip())
                if lcols and abs(
                    len(lcols) - len(first_cols)
                ) <= 1:
                    similar += 1
            if similar >= 1:
                return first_cols

    return None


def _detect_toc_entries(text: str) -> list[tuple[str, str]] | None:
    """Detect TOC (Inhaltsverzeichnis) and return entries."""
    import re
    toc_match = re.search(
        r"^(Inhaltsverzeichnis|Inhalt|Table of Contents)\s*$",
        text, re.MULTILINE | re.IGNORECASE,
    )
    if not toc_match:
        return None

    lines = text[toc_match.end():].split("\n")
    toc_lines = []
    non_toc = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            non_toc += 1
            if non_toc >= 3:
                break
            continue
        is_toc = bool(
            re.search(r"[.·…]{2,}", stripped)
            or re.match(r"^[A-Z]\.\s+\S", stripped)
            or re.match(r"^\d+(?:\.\d+)*\.?\s+\S", stripped)
        )
        if is_toc:
            toc_lines.append(stripped)
            non_toc = 0
        else:
            non_toc += 1
            if non_toc >= 3:
                break

    if len(toc_lines) < 2:
        return None

    toc_text = "\n".join(toc_lines)
    entries = []
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE,
    )
    letter_pat = re.compile(
        r"^([A-Z])\.\s+(.+)$", re.MULTILINE,
    )
    for m in num_pat.finditer(toc_text):
        num = m.group(1).rstrip(".")
        title = _clean_toc(m.group(2).strip())
        if title:
            entries.append((num, title, m.start()))
    for m in letter_pat.finditer(toc_text):
        title = _clean_toc(m.group(2).strip())
        if title:
            entries.append((m.group(1), title, m.start()))
    entries.sort(key=lambda x: x[2])
    if len(entries) < 2:
        return None
    return [(eid, et) for eid, et, _ in entries]


def _content_to_fields(content: str) -> list[dict]:
    """Split section content into typed fields.

    Detects tables and separates text before/after them.
    Returns a list of field dicts for template structure.
    """
    if not content.strip():
        return [{
            "key": "inhalt", "label": "Inhalt",
            "type": "textarea", "required": False,
        }]

    table_cols = _detect_table(content)

    if not table_cols:
        return [{
            "key": "inhalt", "label": "Inhalt",
            "type": "textarea", "required": False,
            "default": content[:3000],
        }]

    # Table detected — split text before table from table
    fields = []
    lines = content.split("\n")

    # Find where table starts (first structured line)
    table_start_idx = 0
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        cols = _split_cols(stripped)
        if len(cols) >= len(table_cols) - 1:
            # Check if this looks like the header
            match_count = sum(
                1 for c in cols
                if any(
                    tc.lower() in c.lower()
                    for tc in table_cols
                )
            )
            if match_count >= 1:
                table_start_idx = i
                break

    # Text before table
    text_before = "\n".join(
        lines[:table_start_idx],
    ).strip()
    if text_before:
        fields.append({
            "key": "beschreibung",
            "label": "Beschreibung",
            "type": "textarea", "required": False,
            "default": text_before[:2000],
        })

    # Table field
    fields.append({
        "key": "tabelle", "label": "Tabelle",
        "type": "table", "required": False,
        "columns": table_cols,
    })

    # Text after table (if any significant text)
    text_after = "\n".join(
        lines[table_start_idx + len(table_cols) + 5:],
    ).strip()
    if len(text_after) > 50:
        fields.append({
            "key": "inhalt", "label": "Inhalt",
            "type": "textarea", "required": False,
            "default": text_after[:2000],
        })

    # If only table, add empty inhalt for notes
    if not text_before and len(text_after) <= 50:
        fields.append({
            "key": "inhalt", "label": "Anmerkungen",
            "type": "textarea", "required": False,
        })

    return fields


def _extract_toc_first(
    text: str, toc_entries: list[tuple[str, str]],
) -> list[dict]:
    """Use TOC as structure, map body content to each entry."""
    import re
    toc_end = len(text) // 5
    body_pos = []
    for eid, etitle in toc_entries:
        prefix = re.escape(etitle[:20])
        if eid.isalpha():
            pat = re.compile(
                rf"^{re.escape(eid)}\.\s+{prefix}",
                re.MULTILINE,
            )
        else:
            pat = re.compile(
                rf"^{re.escape(eid)}\.?\s+{prefix}",
                re.MULTILINE,
            )
        m = pat.search(text, toc_end)
        if m:
            lend = text.find("\n", m.start())
            if lend == -1:
                lend = len(text)
            body_pos.append((m.start(), lend, eid, etitle))

    if not body_pos:
        return []

    body_pos.sort(key=lambda x: x[0])
    pos_map = {}
    for start, end, eid, etitle in body_pos:
        if eid not in pos_map:
            pos_map[eid] = (start, end, etitle)

    sections = []
    for eid, etitle in toc_entries:
        if eid.isalpha():
            key = f"section_{eid.lower()}"
        else:
            key = f"section_{eid.replace('.', '_')}"
        label = f"{eid}. {etitle}"

        if eid not in pos_map:
            sections.append({
                "key": key, "label": label,
                "fields": [{
                    "key": "inhalt", "label": "Inhalt",
                    "type": "textarea", "required": False,
                }],
            })
            continue

        hstart, hend, _ = pos_map[eid]
        next_start = len(text)
        for ostart, _, _, _ in body_pos:
            if ostart > hstart:
                next_start = ostart
                break
        content = text[hend:next_start].strip()

        fields = _content_to_fields(content)
        sections.append({
            "key": key, "label": label, "fields": fields,
        })
    return sections


def _text_to_structure(text: str) -> dict:
    """Convert extracted PDF text to template structure.

    Strategy 1: TOC-first (Inhaltsverzeichnis detection).
    Strategy 2: Heading detection with filters.
    Fallback: Single section with full text.
    """
    import re

    # Try concept_templates package first
    try:
        from concept_templates.pdf_structure_extractor import (
            extract_structure_from_text as _pkg_extract,
        )
        ct = _pkg_extract(text)
        sections = []
        for s in ct.sections:
            fields = []
            for f in s.fields:
                fd = {
                    "key": f.name, "label": f.label,
                    "type": str(f.field_type.value),
                    "required": f.required,
                }
                if f.default:
                    fd["default"] = f.default
                if f.columns:
                    fd["columns"] = f.columns
                fields.append(fd)
            sections.append({
                "key": s.name, "label": s.title,
                "fields": fields,
            })
        return {"sections": sections}
    except ImportError:
        pass

    # Strategy 1: TOC-first
    toc = _detect_toc_entries(text)
    if toc:
        sections = _extract_toc_first(text, toc)
        if sections:
            return {"sections": sections}

    # Strategy 2: Heading detection with filters
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE,
    )
    candidates = []
    for m in num_pat.finditer(text):
        num = m.group(1).rstrip(".")
        title = _clean_toc(m.group(2).strip())
        if not title:
            continue
        try:
            if not _is_valid_heading(num, title, m.group(0)):
                continue
        except (ValueError, IndexError):
            continue
        candidates.append((m, num, title))

    sections = []
    for i, (m, num, title) in enumerate(candidates):
        key = f"section_{num.replace('.', '_')}"
        start = m.end()
        end = (
            candidates[i + 1][0].start()
            if i + 1 < len(candidates)
            else len(text)
        )
        content = text[start:end].strip()[:3000]
        fields = _content_to_fields(content)

        sections.append({
            "key": key, "label": f"{num}. {title}",
            "fields": fields,
        })

    if sections:
        return {"sections": sections}

    # Fallback
    return {"sections": [{
        "key": "section_1",
        "label": "1. Dokumentinhalt",
        "fields": [{
            "key": "inhalt", "label": "Inhalt",
            "type": "textarea", "required": False,
            "default": text[:5000],
        }],
    }]}


def _import_text_into_template(
    text: str, structure: dict,
) -> dict:
    """Import text from PDF into template field values.

    Splits text by section labels and assigns to fields.
    """
    import re
    values = {}
    sections = structure.get("sections", [])

    for i, section in enumerate(sections):
        skey = section["key"]
        fields = section.get("fields", [])

        content = ""
        label = section.get("label", "")
        num_match = re.match(r"(\d+(?:\.\d+)*)", label)
        if num_match:
            num = num_match.group(1)
            pat = re.compile(
                rf"^{re.escape(num)}\.?\s+",
                re.MULTILINE,
            )
            match = pat.search(text)
            if match:
                start = match.end()
                next_section = (
                    sections[i + 1]
                    if i + 1 < len(sections)
                    else None
                )
                if next_section:
                    next_label = next_section.get("label", "")
                    next_num = re.match(
                        r"(\d+(?:\.\d+)*)", next_label,
                    )
                    if next_num:
                        next_pat = re.compile(
                            rf"^{re.escape(next_num.group(1))}\.?\s+",
                            re.MULTILINE,
                        )
                        next_m = next_pat.search(text, start)
                        end = (
                            next_m.start() if next_m
                            else len(text)
                        )
                    else:
                        end = len(text)
                else:
                    end = len(text)
                content = text[start:end].strip()

        values[skey] = {}
        for field in fields:
            fkey = field["key"]
            ftype = field.get("type", "textarea")
            if ftype == "table":
                values[skey][fkey] = []
            else:
                values[skey][fkey] = content[:5000]

    return values
