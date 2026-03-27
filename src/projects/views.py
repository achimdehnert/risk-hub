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
        site, created = Site.objects.get_or_create(
            tenant_id=request.tenant_id,
            name=site_name,
            defaults={
                "organization": request.user.tenancy_memberships.filter(
                    tenant_id=request.tenant_id,
                ).first().organization,
            },
        )
        if created:
            logger.info(
                "Auto-created Site '%s' for tenant %s",
                site_name,
                request.tenant_id,
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

        for f in files:
            title = f.name.rsplit(".", 1)[0] if "." in f.name else f.name
            ProjectDocument.objects.create(
                tenant_id=request.tenant_id,
                project=project,
                title=title,
                doc_type=doc_type,
                file=f,
                uploaded_by=request.user,
            )
            logger.info(
                "Uploaded document '%s' to project %s",
                f.name,
                project.name,
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
        doc.file.delete(save=False)
        doc.delete()
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
        status=DocumentTemplate.Status.ACCEPTED,
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

        doc = OutputDocument.objects.create(
            tenant_id=request.tenant_id,
            project=project,
            template=tmpl,
            kind=tmpl.kind or "custom",
            title=title,
            created_by=request.user,
        )

        # Create sections from template structure
        for idx, section in enumerate(tmpl.get_sections()):
            DocumentSection.objects.create(
                document=doc,
                section_key=section.get("key", f"s_{idx}"),
                title=section.get("label", f"Abschnitt {idx + 1}"),
                order=idx,
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
        section.save(
            update_fields=["content", "is_ai_generated", "updated_at"],
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

        tmpl = DocumentTemplate.objects.create(
            tenant_id=request.tenant_id,
            name=name,
            kind=kind,
            description=desc,
            structure_json=json.dumps(
                structure, ensure_ascii=False,
            ),
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

        tmpl = DocumentTemplate.objects.create(
            tenant_id=request.tenant_id,
            name=name,
            kind=kind,
            description=request.POST.get("description", ""),
            structure_json=json.dumps(
                structure, ensure_ascii=False,
            ),
            source_filename=pdf_file.name,
            source_text=text[:50000],
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

        tmpl.structure_json = json.dumps(
            structure, ensure_ascii=False,
        )
        tmpl.name = request.POST.get("name", tmpl.name)
        tmpl.description = request.POST.get(
            "description", tmpl.description,
        )
        new_status = request.POST.get("status", tmpl.status)
        if new_status in dict(DocumentTemplate.Status.choices):
            tmpl.status = new_status
        tmpl.save()

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
        tmpl.delete()
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


def _text_to_structure(text: str) -> dict:
    """Convert extracted PDF text to template structure."""
    import re

    sections = []
    num_pat = re.compile(
        r"^(\d+(?:\.\d+)*\.?)\s+(.+)$", re.MULTILINE,
    )

    matches = list(num_pat.finditer(text))
    for i, m in enumerate(matches):
        num = m.group(1).rstrip(".")
        title = m.group(2).strip()
        # Filter false headings
        try:
            top = int(num.split(".")[0])
            if top > 30:
                continue
        except ValueError:
            continue
        if sum(1 for c in title if c.isalpha()) < 2:
            continue

        key = f"section_{num.replace('.', '_')}"
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()[:3000]

        fields = [{
            "key": "inhalt",
            "label": "Inhalt",
            "type": "textarea",
            "required": False,
        }]
        if content:
            fields[0]["default"] = content

        sections.append({
            "key": key,
            "label": f"{num}. {title}",
            "fields": fields,
        })

    if not sections:
        sections = [{
            "key": "section_1",
            "label": "1. Dokumentinhalt",
            "fields": [{
                "key": "inhalt",
                "label": "Inhalt",
                "type": "textarea",
                "required": False,
                "default": text[:5000],
            }],
        }]

    return {"sections": sections}
