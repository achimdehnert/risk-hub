"""Brandschutz views — concept list, detail, sections, extinguishers, escape routes."""

from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from common.tenant import require_tenant as _require_tenant
from documents.models import Document

from .forms import FireProtectionConceptForm, FireSectionForm
from .models import (
    ConceptDocument,
    ConceptTemplateStore,
    EscapeRoute,
    FilledTemplate,
    FireExtinguisher,
    FireProtectionConcept,
    FireProtectionMeasure,
)

ALLOWED_EXTENSIONS = frozenset({
    ".pdf", ".docx", ".doc", ".dxf", ".dwg",
    ".jpg", ".jpeg", ".png", ".tiff", ".xlsx", ".xls",
    ".txt", ".csv",
})
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


class ConceptListView(View):
    template_name = "brandschutz/concept_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concepts = (
            FireProtectionConcept.objects.filter(tenant_id=request.tenant_id)
            .select_related("site")
            .order_by("-created_at")
        )
        return render(request, self.template_name, {"concepts": concepts})


class ConceptDetailView(View):
    template_name = "brandschutz/concept_detail.html"

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept.objects.select_related("site"),
            pk=pk,
            tenant_id=request.tenant_id,
        )
        sections = concept.sections.prefetch_related(
            "escape_routes", "fire_extinguishers", "measures"
        )
        measures = concept.measures.filter(section__isnull=True)
        documents = (
            Document.objects.filter(
                tenant_id=request.tenant_id,
                concept_ref_id=concept.pk,
                scope="brandschutz",
            )
            .order_by("-created_at")
        )
        concept_docs = concept.concept_documents.filter(
            deleted_at__isnull=True,
        ).order_by("-created_at")
        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "sections": sections,
                "measures": measures,
                "documents": documents,
                "concept_docs": concept_docs,
                "doc_categories": Document.Category.choices,
            },
        )


class ConceptCreateView(View):
    """Brandschutzkonzept erstellen."""

    template_name = "brandschutz/concept_form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        form = FireProtectionConceptForm(tenant_id=request.tenant_id)
        return render(request, self.template_name, {"form": form, "title": "Neues Brandschutzkonzept"})

    def post(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        form = FireProtectionConceptForm(request.POST, tenant_id=request.tenant_id)
        if form.is_valid():
            from common.services import save_form
            user_id = request.user.pk if request.user.is_authenticated else None
            concept = save_form(form, request.tenant_id, user_id, is_create=True)
            messages.success(request, f"Brandschutzkonzept '{concept.title}' angelegt.")
            return redirect("brandschutz:concept-detail", pk=concept.pk)
        return render(request, self.template_name, {"form": form, "title": "Neues Brandschutzkonzept"})


class ConceptEditView(View):
    """Brandschutzkonzept bearbeiten."""

    template_name = "brandschutz/concept_form.html"

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(FireProtectionConcept, pk=pk, tenant_id=request.tenant_id)
        form = FireProtectionConceptForm(instance=concept, tenant_id=request.tenant_id)
        return render(request, self.template_name, {"form": form, "title": concept.title, "concept": concept})

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(FireProtectionConcept, pk=pk, tenant_id=request.tenant_id)
        form = FireProtectionConceptForm(request.POST, instance=concept, tenant_id=request.tenant_id)
        if form.is_valid():
            from common.services import save_form
            save_form(form, request.tenant_id, is_create=False)
            messages.success(request, f"Brandschutzkonzept '{concept.title}' aktualisiert.")
            return redirect("brandschutz:concept-detail", pk=concept.pk)
        return render(request, self.template_name, {"form": form, "title": concept.title, "concept": concept})


class ExtinguisherListView(View):
    """Alle Feuerlöscher eines Tenants — Übersicht / Prüfkalender."""

    template_name = "brandschutz/extinguisher_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        extinguishers = (
            FireExtinguisher.objects.filter(tenant_id=request.tenant_id)
            .select_related("section__concept")
            .order_by("next_inspection_date", "section")
        )
        status_filter = request.GET.get("status")
        if status_filter:
            extinguishers = extinguishers.filter(status=status_filter)
        return render(
            request,
            self.template_name,
            {
                "extinguishers": extinguishers,
                "status_choices": FireExtinguisher.Status.choices,
                "current_status": status_filter,
            },
        )


class EscapeRouteListView(View):
    """Alle Fluchtwege eines Tenants — Übersicht / Mängelstatus."""

    template_name = "brandschutz/escape_route_list.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        routes = (
            EscapeRoute.objects.filter(tenant_id=request.tenant_id)
            .select_related("section__concept")
            .order_by("status", "section")
        )
        status_filter = request.GET.get("status")
        if status_filter:
            routes = routes.filter(status=status_filter)
        return render(
            request,
            self.template_name,
            {
                "routes": routes,
                "status_choices": EscapeRoute.Status.choices,
                "current_status": status_filter,
            },
        )


class MeasureUpdateView(View):
    """HTMX-partial: Maßnahmenstatus aktualisieren."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        measure = get_object_or_404(
            FireProtectionMeasure,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        new_status = request.POST.get("status")
        if new_status in dict(FireProtectionMeasure.Status.choices):
            measure.status = new_status
            if new_status == FireProtectionMeasure.Status.IMPLEMENTED:
                from django.utils import timezone

                measure.completed_at = timezone.now()
            measure.save(update_fields=["status", "completed_at", "updated_at"])
            messages.success(request, f"Maßnahme '{measure.title}' aktualisiert.")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "brandschutz/partials/measure_row.html",
                {"measure": measure},
            )
        return redirect("brandschutz:concept-detail", pk=measure.concept_id)


class SectionCreateView(View):
    """Brandabschnitt zu einem Konzept hinzufügen."""

    template_name = "brandschutz/section_form.html"

    def get(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        form = FireSectionForm()
        return render(
            request,
            self.template_name,
            {"form": form, "concept": concept},
        )

    def post(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        form = FireSectionForm(request.POST)
        if form.is_valid():
            from common.services import save_form
            section = save_form(form, request.tenant_id, is_create=True)
            section.concept = concept
            section.save(update_fields=["concept_id"])
            messages.success(
                request,
                f"Brandabschnitt '{section.name}' angelegt.",
            )
            return redirect(
                "brandschutz:concept-detail", pk=concept.pk
            )
        return render(
            request,
            self.template_name,
            {"form": form, "concept": concept},
        )


class DocumentUploadView(View):
    """Unterlage zu einem Brandschutzkonzept hochladen (ADR-147 Phase A)."""

    template_name = "brandschutz/document_upload.html"

    def get(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "categories": Document.Category.choices,
            },
        )

    def post(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )

        uploaded_file = request.FILES.get("file")
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", Document.Category.GENERAL)

        if not uploaded_file:
            messages.error(request, "Bitte eine Datei auswählen.")
            return redirect(
                "brandschutz:document-upload", concept_pk=concept.pk
            )

        # Validate extension
        import os

        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            messages.error(
                request,
                f"Dateityp '{ext}' nicht erlaubt.",
            )
            return redirect(
                "brandschutz:document-upload", concept_pk=concept.pk
            )

        # Validate size
        if uploaded_file.size > MAX_UPLOAD_SIZE:
            messages.error(request, "Datei zu groß (max. 50 MB).")
            return redirect(
                "brandschutz:document-upload", concept_pk=concept.pk
            )

        if not title:
            title = uploaded_file.name

        # Create document via documents service
        from documents.services import upload_document

        try:
            upload_document(
                title=title,
                category=category,
                file=uploaded_file,
                tenant_id=request.tenant_id,
            )
            # Update the document with concept reference
            doc = Document.objects.filter(
                tenant_id=request.tenant_id,
                title=title,
            ).first()
            if doc:
                doc.concept_ref_id = concept.pk
                doc.scope = "brandschutz"
                doc.save(update_fields=["concept_ref_id", "scope"])

            # Create ConceptDocument + trigger async analysis for PDFs
            if ext == ".pdf":
                from brandschutz.services import create_concept_document
                concept_doc = create_concept_document(
                    tenant_id=request.tenant_id,
                    concept=concept,
                    title=title,
                    source_filename=uploaded_file.name,
                    content_type=uploaded_file.content_type or "",
                )
                from brandschutz.tasks import extract_and_analyze_task

                extract_and_analyze_task.delay(
                    str(concept_doc.id),
                    str(request.tenant_id),
                )

            messages.success(
                request,
                f"Unterlage '{title}' hochgeladen.",
            )
        except Exception as exc:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning("Document upload failed: %s", exc)
            messages.error(
                request,
                f"Upload fehlgeschlagen: {exc}",
            )

        return redirect("brandschutz:concept-detail", pk=concept.pk)


class ConceptDocAnalyzeView(View):
    """Re-trigger analysis for a ConceptDocument (ADR-147 Phase C)."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept_doc = get_object_or_404(
            ConceptDocument,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        # Reset for re-analysis
        concept_doc.status = "uploaded"
        concept_doc.template_json = ""
        concept_doc.analysis_confidence = None
        concept_doc.error_message = ""
        concept_doc.save(update_fields=[
            "status", "template_json",
            "analysis_confidence", "error_message",
        ])

        from brandschutz.tasks import extract_and_analyze_task

        extract_and_analyze_task.delay(
            str(concept_doc.id),
            str(request.tenant_id),
        )
        messages.info(request, f"Analyse für '{concept_doc.title}' gestartet.")
        return redirect(
            "brandschutz:concept-detail",
            pk=concept_doc.concept_id,
        )


# ── Phase E: Template-Auswahl, Formular, Speichern ─────────────


class TemplateSelectView(View):
    """Choose or create a template for a concept (ADR-147 Phase E)."""

    template_name = "brandschutz/template_select.html"

    def get(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        # Available templates: tenant-specific + analyzed from docs
        templates = ConceptTemplateStore.objects.filter(
            tenant_id=request.tenant_id,
            scope="brandschutz",
        )
        # Analyzed docs that could become templates
        analyzed_docs = concept.concept_documents.filter(
            status="analyzed",
            deleted_at__isnull=True,
        )
        # Existing filled templates for this concept
        filled = concept.filled_templates.order_by("-updated_at")

        return render(request, self.template_name, {
            "concept": concept,
            "templates": templates,
            "analyzed_docs": analyzed_docs,
            "filled_templates": filled,
        })

    def post(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        """Create a FilledTemplate from selected template or analyzed doc."""
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            FireProtectionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )

        template_id = request.POST.get("template_id")
        doc_id = request.POST.get("doc_id")

        if template_id:
            tmpl = get_object_or_404(
                ConceptTemplateStore,
                pk=template_id,
                tenant_id=request.tenant_id,
            )
        elif doc_id:
            # Promote analyzed ConceptDocument to a stored template
            cdoc = get_object_or_404(
                ConceptDocument,
                pk=doc_id,
                tenant_id=request.tenant_id,
                status="analyzed",
            )
            from brandschutz.services import promote_to_template
            tmpl = promote_to_template(
                tenant_id=request.tenant_id,
                concept_doc=cdoc,
            )
        else:
            messages.error(request, "Kein Template ausgewählt.")
            return redirect(
                "brandschutz:template-select",
                concept_pk=concept.pk,
            )

        from brandschutz.services import create_filled_template
        filled = create_filled_template(
            tenant_id=request.tenant_id,
            concept=concept,
            template=tmpl,
        )
        return redirect(
            "brandschutz:filled-template-edit",
            pk=filled.pk,
        )


class FilledTemplateEditView(View):
    """Edit a filled template with dynamic form (ADR-147 Phase E)."""

    template_name = "brandschutz/filled_template_edit.html"

    def _get_filled(self, request, pk):
        err = _require_tenant(request)
        if err:
            return None, err
        filled = get_object_or_404(
            FilledTemplate,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        return filled, None

    def _build_form(self, filled, data=None):
        import json

        from concept_templates.contrib.django.form_generator import (
            build_template_form,
        )
        from concept_templates.schemas import ConceptTemplate

        template_data = json.loads(filled.template.template_json)
        ct = ConceptTemplate(**template_data)
        FormClass = build_template_form(ct)

        # Load existing values as initial
        initial = {}
        if filled.values_json and filled.values_json != "{}":
            values = json.loads(filled.values_json)
            for section_name, fields in values.items():
                for field_name, value in fields.items():
                    initial[f"{section_name}__{field_name}"] = value

        if data is not None:
            return FormClass(data), ct
        return FormClass(initial=initial), ct

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        filled, err = self._get_filled(request, pk)
        if err:
            return err
        form, ct = self._build_form(filled)

        from concept_templates.contrib.django.form_generator import (
            get_sections_with_fields,
        )

        sections = get_sections_with_fields(form)
        return render(request, self.template_name, {
            "filled": filled,
            "concept": filled.concept,
            "form": form,
            "sections": sections,
            "template_name_display": ct.name,
        })

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        filled, err = self._get_filled(request, pk)
        if err:
            return err
        form, ct = self._build_form(filled, data=request.POST)

        if form.is_valid():
            import json

            from concept_templates.contrib.django.form_generator import (
                extract_values,
            )

            values = extract_values(form)
            filled.values_json = json.dumps(values, ensure_ascii=False)
            filled.save(update_fields=["values_json", "updated_at"])
            messages.success(request, "Werte gespeichert.")
            return redirect(
                "brandschutz:filled-template-edit",
                pk=filled.pk,
            )

        from concept_templates.contrib.django.form_generator import (
            get_sections_with_fields,
        )

        sections = get_sections_with_fields(form)
        return render(request, self.template_name, {
            "filled": filled,
            "concept": filled.concept,
            "form": form,
            "sections": sections,
            "template_name_display": ct.name,
        })


class FilledTemplateLLMPrefillView(View):
    """HTMX endpoint: AI-prefill a single field (ADR-147 Phase E)."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return HttpResponse("Unauthorized", status=401)
        filled = get_object_or_404(
            FilledTemplate,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        field_key = request.POST.get("field_key", "")
        llm_hint = request.POST.get("llm_hint", "")

        if not field_key or not llm_hint:
            return HttpResponse("Missing field_key or llm_hint", status=400)

        import json

        from concept_templates.prefill import prefill_field

        # Existing values
        context_values = None
        if filled.values_json and filled.values_json != "{}":
            context_values = json.loads(filled.values_json)

        # Extracted texts from analyzed documents
        extracted_texts = list(
            filled.concept.concept_documents.filter(
                status="analyzed",
                deleted_at__isnull=True,
            ).values_list("extracted_text", flat=True)[:2]
        )

        def _llm_fn(system: str, user: str) -> str:
            from ai_analysis.llm_client import llm_complete_sync
            return llm_complete_sync(
                prompt=user,
                system=system,
                action_code="concept_prefill",
            )

        value = prefill_field(
            field_key=field_key,
            llm_hint=llm_hint,
            llm_fn=_llm_fn,
            context_values=context_values,
            extracted_texts=extracted_texts,
            scope=filled.template.scope or "brandschutz",
        )

        return HttpResponse(
            f'<input type="text" name="{field_key}" value="{value}" '
            f'class="w-full px-3 py-2 border border-green-300 rounded-lg '
            f'bg-green-50 focus:ring-2 focus:ring-violet-500" />',
        )


class FilledTemplatePDFView(View):
    """Generate and download PDF from a filled template (ADR-147 Phase E)."""

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        filled = get_object_or_404(
            FilledTemplate,
            pk=pk,
            tenant_id=request.tenant_id,
        )

        import json

        from concept_templates.document_renderer import render_pdf
        from concept_templates.schemas import ConceptTemplate

        template_data = json.loads(filled.template.template_json)
        ct = ConceptTemplate(**template_data)
        values = json.loads(filled.values_json) if filled.values_json else {}

        pdf_bytes = render_pdf(
            template=ct,
            values=values,
            title=filled.name,
        )

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        safe_name = filled.name.replace(" ", "_")[:80]
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_name}.pdf"'
        )
        return response
