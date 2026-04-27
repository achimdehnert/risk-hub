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
from projects.constants import DOCUMENT_KIND_META
from projects.models import (
    DocumentSection,
    DocumentTemplate,
    Project,
    ProjectDocument,
)
from projects.services import (
    CreateProjectCmd,
    create_output_document,
    create_project,
    create_template,
    delete_document_section,
    delete_project_document,
    delete_template,
    export_document_pdf,
    generate_section_content,
    get_active_document_templates,
    get_document_templates,
    get_or_create_site,
    get_output_documents,
    get_project_module_details,
    get_projects,
    get_subscribed_modules,
    get_tenant_sites,
    recommend_modules_from_description,
    save_section_values,
    update_template,
    upload_project_document,
)

logger = logging.getLogger(__name__)


@login_required
def project_list(request: HttpRequest) -> HttpResponse:
    """List all projects for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    projects = (
        get_projects(request.tenant_id)
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

    sites = get_tenant_sites(request.tenant_id)
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
                description,
                subscribed,
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
        org = (
            request.user.tenancy_memberships.filter(
                tenant_id=request.tenant_id,
            )
            .first()
            .organization
        )
        site, created = get_or_create_site(
            request.tenant_id,
            site_name,
            org,
        )

        # Build recommendations for storage
        recommendations = recommend_modules_from_description(
            description,
            subscribed,
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
        "",
        subscribed,
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
        description,
        subscribed,
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
        get_projects(request.tenant_id).prefetch_related("modules"),
        pk=pk,
    )

    module_details = get_project_module_details(project)
    declined = project.modules.filter(status="declined")
    documents = project.documents.all()[:20]
    output_docs = project.output_documents.all()[:20]
    explosion_concepts = project.explosion_concepts.all()[:10]

    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "module_details": module_details,
            "declined_modules": declined,
            "documents": documents,
            "output_docs": output_docs,
            "explosion_concepts": explosion_concepts,
        },
    )


@login_required
def document_upload(request: HttpRequest, pk: int) -> HttpResponse:
    """Upload a document to a project."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project,
        pk=pk,
        tenant_id=request.tenant_id,
    )

    if request.method == "POST":
        files = request.FILES.getlist("files")
        doc_type = request.POST.get("doc_type", "other")

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
    request: HttpRequest,
    pk: int,
    doc_pk: int,
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
        delete_project_document(doc)
    return redirect("projects:project-detail", pk=pk)


# --- OutputDocument (Dokument erstellen) ---


@login_required
def output_document_create(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """Create a new output document for a project."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project,
        pk=pk,
        tenant_id=request.tenant_id,
    )
    templates = get_active_document_templates(request.tenant_id)

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

        from django.apps import apps as _apps
        _DocTemplate = _apps.get_model("doc_templates", "DocumentTemplate")
        tmpl = get_object_or_404(
            _DocTemplate,
            pk=template_id,
            tenant_id=request.tenant_id,
        )

        # PDF import (optional)
        pdf_file = request.FILES.get("pdf_file")
        imported_values = {}
        if pdf_file:
            from projects.pdf_utils import extract_pdf_text, import_text_into_template

            text = extract_pdf_text(pdf_file)
            if text:
                try:
                    structure = json.loads(tmpl.structure_json)
                except (json.JSONDecodeError, TypeError):
                    structure = {"sections": []}
                imported_values = import_text_into_template(
                    text,
                    structure,
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
    request: HttpRequest,
    pk: int,
    doc_pk: int,
) -> HttpResponse:
    """Edit an output document's sections."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    project = get_object_or_404(
        Project,
        pk=pk,
        tenant_id=request.tenant_id,
    )
    doc = get_object_or_404(
        get_output_documents(request.tenant_id).prefetch_related("sections"),
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
    request: HttpRequest,
    pk: int,
    doc_pk: int,
    sec_pk: int,
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
        save_section_values(section, request.POST)

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
    request: HttpRequest,
    pk: int,
    doc_pk: int,
    sec_pk: int,
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

    generated = generate_section_content(
        section=section,
        field_key=field_key,
        llm_hint=llm_hint,
    )

    # Return textarea partial with generated content
    form_key = f"{section.section_key}__{field_key}" if field_key else "content"
    return HttpResponse(
        f'<textarea name="{form_key}" rows="6" '
        f'class="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm '
        f'focus:ring-orange-500 focus:border-orange-500 resize-y">'
        f"{generated}</textarea>",
        content_type="text/html",
    )


@login_required
def section_delete(
    request: HttpRequest,
    pk: int,
    doc_pk: int,
    sec_pk: int,
) -> HttpResponse:
    """HTMX: Delete a section and return empty string to remove it from DOM."""
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
        delete_document_section(section)
        return HttpResponse("", status=200)

    return redirect("projects:output-document-edit", pk=pk, doc_pk=doc_pk)


# ─── PDF Export ──────────────────────────────────────────────


@login_required
def output_document_pdf(
    request: HttpRequest,
    pk: int,
    doc_pk: int,
) -> HttpResponse:
    """Generate PDF for an output document via WeasyPrint."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    doc = get_object_or_404(
        get_output_documents(request.tenant_id).prefetch_related("sections"),
        pk=doc_pk,
        project__pk=pk,
    )

    pdf_bytes = export_document_pdf(doc)
    if pdf_bytes:
        response = HttpResponse(
            pdf_bytes,
            content_type="application/pdf",
        )
        safe_title = doc.title.replace('"', "'")
        response["Content-Disposition"] = f'attachment; filename="{safe_title}.pdf"'
        return response

    messages.error(
        request,
        "PDF-Export nicht verfügbar (WeasyPrint nicht installiert).",
    )
    return redirect(
        "projects:output-document-edit",
        pk=pk,
        doc_pk=doc_pk,
    )


# ─── DocumentTemplate CRUD ──────────────────────────────────


@login_required
def template_list(request: HttpRequest) -> HttpResponse:
    """List all document templates for current tenant."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    templates = get_active_document_templates(request.tenant_id).order_by("-updated_at")

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
                    "fields": [
                        {
                            "key": "inhalt",
                            "label": "Inhalt",
                            "type": "textarea",
                            "required": False,
                        }
                    ],
                },
            ],
        }

        tmpl = create_template(
            tenant_id=request.tenant_id,
            name=name,
            kind=kind,
            description=desc,
            structure=structure,
        )
        messages.success(request, f"Vorlage '{name}' erstellt.")
        return redirect(
            "projects:template-edit",
            tmpl_pk=tmpl.pk,
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
                "_",
                " ",
            )
        kind = request.POST.get("kind", "").strip()

        from projects.pdf_utils import extract_pdf_text, text_to_structure

        text = extract_pdf_text(pdf_file)
        if not text:
            messages.warning(
                request,
                "Kein Text aus PDF extrahiert. Leere Vorlage erstellt.",
            )

        structure = text_to_structure(text) if text else {"sections": []}

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
            f"Vorlage '{name}' aus PDF erstellt ({tmpl.section_count} Abschnitte).",
        )
        return redirect(
            "projects:template-edit",
            tmpl_pk=tmpl.pk,
        )

    return render(
        request,
        "projects/templates/template_upload.html",
    )


@login_required
def template_edit(
    request: HttpRequest,
    tmpl_pk: int,
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

        update_template(
            tmpl,
            structure=structure,
            name=request.POST.get("name", tmpl.name),
            description=request.POST.get(
                "description",
                tmpl.description,
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
                structure,
                ensure_ascii=False,
                indent=2,
            ),
        },
    )


@login_required
def template_delete(
    request: HttpRequest,
    tmpl_pk: int,
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
        delete_template(tmpl)
        messages.success(request, "Vorlage gelöscht.")
    return redirect("projects:template-list")
