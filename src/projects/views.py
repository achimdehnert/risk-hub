"""Project views (ADR-041).

Views handle HTTP only — business logic in services.py.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from common.tenant import require_tenant as _require_tenant
from projects.models import (
    DocumentSection,
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

    if request.method == "POST":
        kind = request.POST.get("kind", "")
        title = request.POST.get("title", "").strip()

        if not kind or not title:
            return render(
                request,
                "projects/output_document_create.html",
                {
                    "project": project,
                    "kinds": DOCUMENT_KIND_META,
                    "error": "Typ und Titel sind Pflichtfelder.",
                    "form_data": request.POST,
                },
            )

        doc = OutputDocument.objects.create(
            tenant_id=request.tenant_id,
            project=project,
            kind=kind,
            title=title,
            created_by=request.user,
        )

        # Create default sections
        meta = DOCUMENT_KIND_META.get(kind, {})
        for idx, (key, sec_title) in enumerate(
            meta.get("default_sections", []),
        ):
            DocumentSection.objects.create(
                document=doc,
                section_key=key,
                title=sec_title,
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
        section.save(update_fields=["content", "is_ai_generated", "updated_at"])

    return render(
        request,
        "projects/partials/_section_card.html",
        {"section": section, "project": section.document.project, "doc": section.document},
    )
