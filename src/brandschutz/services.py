"""Brandschutz service layer (ADR-041).

Write operations for fire protection concepts, sections, documents,
and templates. Views must not call .save() / .delete() / .create()
directly — always go through this module.
"""

import logging
from uuid import UUID

from common.services import save_form  # noqa: F401

logger = logging.getLogger(__name__)


def create_concept_document(
    tenant_id: UUID,
    concept,
    title: str,
    scope: str = "brandschutz",
    source_filename: str = "",
    content_type: str = "",
):
    """Create a ConceptDocument and trigger async analysis."""
    from brandschutz.models import ConceptDocument

    concept_doc = ConceptDocument.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        title=title,
        scope=scope,
        source_filename=source_filename,
        content_type=content_type,
    )
    return concept_doc


def promote_to_template(
    tenant_id: UUID,
    concept_doc,
):
    """Promote an analyzed ConceptDocument to a stored template."""
    from brandschutz.models import ConceptTemplateStore

    tmpl = ConceptTemplateStore.objects.create(
        tenant_id=tenant_id,
        name=f"Aus Analyse: {concept_doc.title}",
        scope=concept_doc.scope or "brandschutz",
        source="analyzed",
        source_document=concept_doc,
        template_json=concept_doc.template_json,
    )
    return tmpl


def create_filled_template(
    tenant_id: UUID,
    concept,
    template,
):
    """Create a FilledTemplate from a concept + template."""
    from brandschutz.models import FilledTemplate

    filled = FilledTemplate.objects.create(
        tenant_id=tenant_id,
        concept=concept,
        template=template,
        name=f"{concept.name} — {template.name}",
    )
    return filled


# -----------------------------------------------------------------------
# Measure status
# -----------------------------------------------------------------------

ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".doc",
        ".dxf",
        ".dwg",
        ".jpg",
        ".jpeg",
        ".png",
        ".tiff",
        ".xlsx",
        ".xls",
        ".txt",
        ".csv",
    }
)
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


def update_measure_status(measure, new_status: str) -> bool:
    """Update a FireProtectionMeasure's status.

    Sets completed_at when status becomes IMPLEMENTED.
    Returns True if status was valid and updated.
    """
    from brandschutz.models import FireProtectionMeasure

    if new_status not in dict(FireProtectionMeasure.Status.choices):
        return False

    measure.status = new_status
    if new_status == FireProtectionMeasure.Status.IMPLEMENTED:
        from django.utils import timezone

        measure.completed_at = timezone.now()
    measure.save(update_fields=["status", "completed_at", "updated_at"])
    return True


# -----------------------------------------------------------------------
# Document upload + analysis
# -----------------------------------------------------------------------


def validate_upload(uploaded_file) -> str | None:
    """Validate file extension and size. Returns error message or None."""
    import os

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Dateityp '{ext}' nicht erlaubt."
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return "Datei zu groß (max. 50 MB)."
    return None


def upload_and_analyze_document(
    *,
    tenant_id: UUID,
    concept,
    uploaded_file,
    title: str,
    category: str,
) -> tuple[bool, str]:
    """Upload a document, link to concept, and trigger analysis for PDFs.

    Returns (success, message) tuple.
    """
    import os

    from documents.services import upload_document

    ext = os.path.splitext(uploaded_file.name)[1].lower()

    try:
        upload_document(
            title=title,
            category=category,
            file=uploaded_file,
            tenant_id=tenant_id,
        )
        # Update the document with concept reference
        from documents.models import Document

        doc = Document.objects.filter(
            tenant_id=tenant_id,
            title=title,
        ).first()
        if doc:
            doc.concept_ref_id = concept.pk
            doc.scope = "brandschutz"
            doc.save(update_fields=["concept_ref_id", "scope"])

        # Create ConceptDocument + trigger async analysis for PDFs
        if ext == ".pdf":
            concept_doc = create_concept_document(
                tenant_id=tenant_id,
                concept=concept,
                title=title,
                source_filename=uploaded_file.name,
                content_type=uploaded_file.content_type or "",
            )
            from brandschutz.tasks import extract_and_analyze_task

            extract_and_analyze_task.delay(
                str(concept_doc.id),
                str(tenant_id),
            )

        return True, f"Unterlage '{title}' hochgeladen."
    except Exception as exc:
        logger.warning("Document upload failed: %s", exc)
        return False, f"Upload fehlgeschlagen: {exc}"


# -----------------------------------------------------------------------
# Re-trigger analysis
# -----------------------------------------------------------------------


def retrigger_doc_analysis(concept_doc) -> None:
    """Reset a ConceptDocument and re-trigger async analysis."""
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

    from brandschutz.tasks import extract_and_analyze_task

    extract_and_analyze_task.delay(
        str(concept_doc.id),
        str(concept_doc.tenant_id),
    )


# -----------------------------------------------------------------------
# Filled template form + values
# -----------------------------------------------------------------------


def build_filled_template_form(filled, data=None):
    """Build a dynamic form from a FilledTemplate's concept template.

    Returns (form_instance, ConceptTemplate).
    """
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


def save_filled_template_values(filled, form) -> None:
    """Extract values from a validated form and save to FilledTemplate."""
    import json

    from concept_templates.contrib.django.form_generator import (
        extract_values,
    )

    values = extract_values(form)
    filled.values_json = json.dumps(values, ensure_ascii=False)
    filled.save(update_fields=["values_json", "updated_at"])


# -----------------------------------------------------------------------
# LLM prefill
# -----------------------------------------------------------------------


def prefill_filled_template_field(
    *,
    filled,
    field_key: str,
    llm_hint: str,
) -> str:
    """AI-prefill a single field on a FilledTemplate.

    Uses concept_templates.prefill + ai_analysis.llm_client.
    """
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
            action_code="concept_prefill",
        )

    return prefill_field(
        field_key=field_key,
        llm_hint=llm_hint,
        llm_fn=_llm_fn,
        context_values=context_values,
        extracted_texts=extracted_texts,
        scope=filled.template.scope or "brandschutz",
    )


# -----------------------------------------------------------------------
# PDF export
# -----------------------------------------------------------------------


def export_filled_template_pdf(filled) -> bytes:
    """Render a filled template to PDF bytes."""
    import json

    from concept_templates.document_renderer import render_pdf
    from concept_templates.schemas import ConceptTemplate

    template_data = json.loads(filled.template.template_json)
    ct = ConceptTemplate(**template_data)
    values = json.loads(filled.values_json) if filled.values_json else {}

    return render_pdf(
        template=ct,
        values=values,
        title=filled.name,
    )
