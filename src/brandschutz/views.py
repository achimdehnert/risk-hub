"""Brandschutz views — concept list, detail, sections, extinguishers, escape routes."""

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
from .services import (
    build_filled_template_form,
    create_filled_template,
    export_filled_template_pdf,
    prefill_filled_template_field,
    promote_to_template,
    retrigger_doc_analysis,
    save_filled_template_values,
    update_measure_status,
    upload_and_analyze_document,
    validate_upload,
)


class ConceptListView(LoginRequiredMixin, View):
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


class ConceptDetailView(LoginRequiredMixin, View):
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
        documents = Document.objects.filter(
            tenant_id=request.tenant_id,
            concept_ref_id=concept.pk,
            scope="brandschutz",
        ).order_by("-created_at")
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


class ConceptCreateView(LoginRequiredMixin, View):
    """Brandschutzkonzept erstellen."""

    template_name = "brandschutz/concept_form.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        form = FireProtectionConceptForm(tenant_id=request.tenant_id)
        return render(
            request, self.template_name, {"form": form, "title": "Neues Brandschutzkonzept"}
        )

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
        return render(
            request, self.template_name, {"form": form, "title": "Neues Brandschutzkonzept"}
        )


class ConceptEditView(LoginRequiredMixin, View):
    """Brandschutzkonzept bearbeiten."""

    template_name = "brandschutz/concept_form.html"

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(FireProtectionConcept, pk=pk, tenant_id=request.tenant_id)
        form = FireProtectionConceptForm(instance=concept, tenant_id=request.tenant_id)
        return render(
            request, self.template_name, {"form": form, "title": concept.title, "concept": concept}
        )

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(FireProtectionConcept, pk=pk, tenant_id=request.tenant_id)
        form = FireProtectionConceptForm(
            request.POST, instance=concept, tenant_id=request.tenant_id
        )
        if form.is_valid():
            from common.services import save_form

            save_form(form, request.tenant_id, is_create=False)
            messages.success(request, f"Brandschutzkonzept '{concept.title}' aktualisiert.")
            return redirect("brandschutz:concept-detail", pk=concept.pk)
        return render(
            request, self.template_name, {"form": form, "title": concept.title, "concept": concept}
        )


class ExtinguisherListView(LoginRequiredMixin, View):
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


class EscapeRouteListView(LoginRequiredMixin, View):
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


class MeasureUpdateView(LoginRequiredMixin, View):
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
        if update_measure_status(measure, new_status):
            messages.success(request, f"Maßnahme '{measure.title}' aktualisiert.")

        if request.headers.get("HX-Request"):
            return render(
                request,
                "brandschutz/partials/measure_row.html",
                {"measure": measure},
            )
        return redirect("brandschutz:concept-detail", pk=measure.concept_id)


class SectionCreateView(LoginRequiredMixin, View):
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
            return redirect("brandschutz:concept-detail", pk=concept.pk)
        return render(
            request,
            self.template_name,
            {"form": form, "concept": concept},
        )


class DocumentUploadView(LoginRequiredMixin, View):
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
            return redirect("brandschutz:document-upload", concept_pk=concept.pk)

        validation_error = validate_upload(uploaded_file)
        if validation_error:
            messages.error(request, validation_error)
            return redirect("brandschutz:document-upload", concept_pk=concept.pk)

        if not title:
            title = uploaded_file.name

        success, msg = upload_and_analyze_document(
            tenant_id=request.tenant_id,
            concept=concept,
            uploaded_file=uploaded_file,
            title=title,
            category=category,
        )
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

        return redirect("brandschutz:concept-detail", pk=concept.pk)


class ConceptDocAnalyzeView(LoginRequiredMixin, View):
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
        retrigger_doc_analysis(concept_doc)
        messages.info(request, f"Analyse für '{concept_doc.title}' gestartet.")
        return redirect(
            "brandschutz:concept-detail",
            pk=concept_doc.concept_id,
        )


# ── Phase E: Template-Auswahl, Formular, Speichern ─────────────


class TemplateSelectView(LoginRequiredMixin, View):
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

        return render(
            request,
            self.template_name,
            {
                "concept": concept,
                "templates": templates,
                "analyzed_docs": analyzed_docs,
                "filled_templates": filled,
            },
        )

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
            cdoc = get_object_or_404(
                ConceptDocument,
                pk=doc_id,
                tenant_id=request.tenant_id,
                status="analyzed",
            )
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

        filled = create_filled_template(
            tenant_id=request.tenant_id,
            concept=concept,
            template=tmpl,
        )
        return redirect(
            "brandschutz:filled-template-edit",
            pk=filled.pk,
        )


class FilledTemplateEditView(LoginRequiredMixin, View):
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

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        filled, err = self._get_filled(request, pk)
        if err:
            return err
        form, ct = build_filled_template_form(filled)

        from concept_templates.contrib.django.form_generator import (
            get_sections_with_fields,
        )

        sections = get_sections_with_fields(form)
        return render(
            request,
            self.template_name,
            {
                "filled": filled,
                "concept": filled.concept,
                "form": form,
                "sections": sections,
                "template_name_display": ct.name,
            },
        )

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        filled, err = self._get_filled(request, pk)
        if err:
            return err
        form, ct = build_filled_template_form(filled, data=request.POST)

        if form.is_valid():
            save_filled_template_values(filled, form)
            messages.success(request, "Werte gespeichert.")
            return redirect(
                "brandschutz:filled-template-edit",
                pk=filled.pk,
            )

        from concept_templates.contrib.django.form_generator import (
            get_sections_with_fields,
        )

        sections = get_sections_with_fields(form)
        return render(
            request,
            self.template_name,
            {
                "filled": filled,
                "concept": filled.concept,
                "form": form,
                "sections": sections,
                "template_name_display": ct.name,
            },
        )


class FilledTemplateLLMPrefillView(LoginRequiredMixin, View):
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

        value = prefill_filled_template_field(
            filled=filled,
            field_key=field_key,
            llm_hint=llm_hint,
        )

        return HttpResponse(
            f'<input type="text" name="{field_key}" value="{value}" '
            f'class="w-full px-3 py-2 border border-green-300 rounded-lg '
            f'bg-green-50 focus:ring-2 focus:ring-violet-500" />',
        )


class FilledTemplatePDFView(LoginRequiredMixin, View):
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

        pdf_bytes = export_filled_template_pdf(filled)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        safe_name = filled.name.replace(" ", "_")[:80]
        response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
        return response
