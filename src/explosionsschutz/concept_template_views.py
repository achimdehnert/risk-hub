# src/explosionsschutz/concept_template_views.py
"""
Concept-Template Views für Explosionsschutz (ADR-147).

Analog zu brandschutz/views.py Phase E:
- DocumentUploadView: PDF hochladen + Analyse starten
- ConceptDocAnalyzeView: Re-Analyse triggern
- TemplateSelectView: Template auswählen / aus Analyse erstellen
- FilledTemplateEditView: Ausgefülltes Template bearbeiten
- FilledTemplateLLMPrefillView: KI-Vorausfüllung einzelner Felder
- FilledTemplatePDFView: PDF-Export
"""

import logging
from uuid import UUID

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .models import (
    ExConceptDocument,
    ExConceptTemplateStore,
    ExFilledTemplate,
    ExplosionConcept,
)

logger = logging.getLogger(__name__)

SCOPE = "explosionsschutz"


def _require_tenant(request):
    if not getattr(request, "tenant_id", None):
        return HttpResponse("Tenant required", status=403)
    return None


# ── Document Upload + Analyse ────────────────────────────────────


class ExDocumentUploadView(LoginRequiredMixin, View):
    """Upload PDF for concept + trigger async analysis."""

    def post(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            ExplosionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            messages.error(request, "Keine Datei ausgewählt.")
            return redirect(
                "explosionsschutz:concept-detail-html",
                pk=concept.pk,
            )

        import os

        title = request.POST.get("title", "") or uploaded_file.name
        ext = os.path.splitext(uploaded_file.name)[1].lower()

        try:
            from documents.services import upload_document

            doc = upload_document(
                tenant_id=request.tenant_id,
                uploaded_file=uploaded_file,
                title=title,
                uploaded_by=request.user,
            )
            if doc:
                doc.concept_ref_id = concept.pk
                doc.scope = SCOPE
                doc.save(update_fields=["concept_ref_id", "scope"])

            if ext == ".pdf":
                concept_doc = ExConceptDocument.objects.create(
                    tenant_id=request.tenant_id,
                    concept=concept,
                    title=title,
                    scope=SCOPE,
                    source_filename=uploaded_file.name,
                    content_type=uploaded_file.content_type or "",
                )
                from explosionsschutz.tasks import extract_and_analyze_task

                extract_and_analyze_task.delay(
                    str(concept_doc.id),
                    str(request.tenant_id),
                )

            messages.success(request, f"Unterlage '{title}' hochgeladen.")
        except Exception as exc:
            logger.warning("Document upload failed: %s", exc)
            messages.error(request, f"Upload fehlgeschlagen: {exc}")

        return redirect(
            "explosionsschutz:concept-detail-html",
            pk=concept.pk,
        )


class ExConceptDocAnalyzeView(LoginRequiredMixin, View):
    """Re-trigger analysis for an ExConceptDocument."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept_doc = get_object_or_404(
            ExConceptDocument,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        concept_doc.status = "uploaded"
        concept_doc.template_json = ""
        concept_doc.analysis_confidence = None
        concept_doc.error_message = ""
        concept_doc.save(
            update_fields=[
                "status",
                "template_json",
                "analysis_confidence",
                "error_message",
            ]
        )

        from explosionsschutz.tasks import extract_and_analyze_task

        extract_and_analyze_task.delay(
            str(concept_doc.id),
            str(request.tenant_id),
        )
        messages.info(
            request,
            f"Analyse für '{concept_doc.title}' gestartet.",
        )
        return redirect(
            "explosionsschutz:concept-detail-html",
            pk=concept_doc.concept_id,
        )


# ── Template-Auswahl ────────────────────────────────────────────


class ExTemplateSelectView(LoginRequiredMixin, View):
    """Choose or create a template for a concept."""

    template_name = "explosionsschutz/concepts/template_select.html"

    def get(self, request: HttpRequest, concept_pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        concept = get_object_or_404(
            ExplosionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )
        templates = ExConceptTemplateStore.objects.filter(
            tenant_id=request.tenant_id,
            scope=SCOPE,
        )
        analyzed_docs = concept.concept_documents.filter(
            status="analyzed",
            deleted_at__isnull=True,
        )
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
            ExplosionConcept,
            pk=concept_pk,
            tenant_id=request.tenant_id,
        )

        template_id = request.POST.get("template_id")
        doc_id = request.POST.get("doc_id")

        if template_id:
            tmpl = get_object_or_404(
                ExConceptTemplateStore,
                pk=template_id,
                tenant_id=request.tenant_id,
            )
        elif doc_id:
            cdoc = get_object_or_404(
                ExConceptDocument,
                pk=doc_id,
                tenant_id=request.tenant_id,
                status="analyzed",
            )
            tmpl = ExConceptTemplateStore.objects.create(
                tenant_id=request.tenant_id,
                name=f"Aus Analyse: {cdoc.title}",
                scope=cdoc.scope or SCOPE,
                source="analyzed",
                source_document=cdoc,
                template_json=cdoc.template_json,
            )
        else:
            messages.error(request, "Kein Template ausgewählt.")
            return redirect(
                "explosionsschutz:ex-template-select",
                concept_pk=concept.pk,
            )

        filled = ExFilledTemplate.objects.create(
            tenant_id=request.tenant_id,
            concept=concept,
            template=tmpl,
            name=f"{concept.title} — {tmpl.name}",
        )
        return redirect(
            "explosionsschutz:ex-filled-template-edit",
            pk=filled.pk,
        )


# ── Filled Template Edit ─────────────────────────────────────────


class ExFilledTemplateEditView(LoginRequiredMixin, View):
    """Edit a filled template with dynamic form."""

    template_name = "explosionsschutz/concepts/filled_template_edit.html"

    def _get_filled(self, request, pk):
        err = _require_tenant(request)
        if err:
            return None, err
        filled = get_object_or_404(
            ExFilledTemplate,
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
                "explosionsschutz:ex-filled-template-edit",
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


# ── LLM Prefill ──────────────────────────────────────────────────


class ExFilledTemplateLLMPrefillView(LoginRequiredMixin, View):
    """HTMX endpoint: AI-prefill a single field."""

    def post(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return HttpResponse("Unauthorized", status=401)
        filled = get_object_or_404(
            ExFilledTemplate,
            pk=pk,
            tenant_id=request.tenant_id,
        )
        field_key = request.POST.get("field_key", "")
        llm_hint = request.POST.get("llm_hint", "")

        if not field_key or not llm_hint:
            return HttpResponse("Missing field_key or llm_hint", status=400)

        import json

        from concept_templates.prefill import prefill_field

        context_values = None
        if filled.values_json and filled.values_json != "{}":
            context_values = json.loads(filled.values_json)

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
                action_code="concept_analysis",
                temperature=0.3,
                max_tokens=500,
            )

        value = prefill_field(
            field_key=field_key,
            llm_hint=llm_hint,
            llm_fn=_llm_fn,
            context_values=context_values,
            extracted_texts=extracted_texts,
            scope=filled.template.scope or SCOPE,
        )

        return HttpResponse(
            f'<input type="text" name="{field_key}" value="{value}" '
            f'class="w-full px-3 py-2 border border-green-300 rounded-lg '
            f'bg-green-50 focus:ring-2 focus:ring-violet-500" />',
        )


# ── PDF Export ────────────────────────────────────────────────────


class ExFilledTemplatePDFView(LoginRequiredMixin, View):
    """Generate and download PDF from a filled template."""

    def get(self, request: HttpRequest, pk: UUID) -> HttpResponse:
        err = _require_tenant(request)
        if err:
            return err
        filled = get_object_or_404(
            ExFilledTemplate,
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
        response["Content-Disposition"] = f'attachment; filename="{safe_name}.pdf"'
        return response
