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
    Project,
    ProjectDocument,
)
from projects.services import (
    CreateProjectCmd,
    create_output_document,
    create_project,
    delete_document_section,
    delete_project_document,
    export_document_pdf,
    generate_section_content,
    generate_section_hints,
    prefill_sections_from_documents,
    get_active_document_templates,
    get_or_create_site,
    get_output_documents,
    get_project_module_details,
    get_projects,
    get_subscribed_modules,
    get_tenant_sites,
    recommend_modules_from_description,
    save_section_values,
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
        generate_section_hints(doc)
        prefill_sections_from_documents(doc)

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
    documents = list(project.documents.all())

    sections = list(doc.sections.all())
    all_docs_with_text = [d for d in documents if d.extracted_text]

    for section in sections:
        matched = []
        hint = section.ai_context_hint or ""
        if hint and all_docs_with_text:
            keywords = [k.strip().lower() for k in hint.replace(",", " ").split() if len(k.strip()) > 2]
            for d in all_docs_with_text:
                text_lower = d.extracted_text.lower()
                score = sum(text_lower.count(kw) for kw in keywords)
                if score:
                    matched.append({
                        "title": d.title,
                        "doc_type_label": d.get_doc_type_display(),
                        "score": score,
                    })
            matched.sort(key=lambda x: -x["score"])
        section.matched_docs = matched[:4]

    return render(
        request,
        "projects/output_document_edit.html",
        {
            "project": project,
            "doc": doc,
            "sections": sections,
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
def document_prefill_from_docs(
    request: HttpRequest,
    pk: int,
    doc_pk: int,
) -> HttpResponse:
    """POST: Fill empty sections from extracted text of uploaded project documents."""
    tenant_response = _require_tenant(request)
    if tenant_response is not None:
        return tenant_response

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    doc = get_object_or_404(
        get_output_documents(request.tenant_id).prefetch_related("sections"),
        pk=doc_pk,
        project__pk=pk,
        project__tenant_id=request.tenant_id,
    )
    # Reset hints so they are regenerated fresh for all sections
    doc.sections.all().update(ai_context_hint="", ai_prompt="")
    generate_section_hints(doc)
    filled = prefill_sections_from_documents(doc, force=True)
    messages.success(request, f"{filled} Abschnitt(e) aus Unterlagen befüllt (mit frischen KI-Hinweisen).")
    return redirect("projects:output-document-edit", pk=pk, doc_pk=doc_pk)


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



