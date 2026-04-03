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
