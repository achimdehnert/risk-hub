"""
GBU PDF-Generierung (Phase 2D).

Erzeugt GBU-Dokument (TRGS 400) und Betriebsanweisung (TRGS 555)
als PDF via WeasyPrint aus Django-Templates.

Beide Funktionen geben rohe PDF-Bytes zurück und sind
seiteneffektfrei — Persistenz liegt in den aufrufenden Schichten.
"""

import logging
from uuid import UUID

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def render_gbu_pdf(activity_id: UUID, tenant_id: UUID) -> bytes:
    """
    GBU-Gefährdungsbeurteilung (TRGS 400) als PDF-Bytes.

    Args:
        activity_id: UUID der HazardAssessmentActivity
        tenant_id: Tenant-Isolation

    Returns:
        PDF-Bytes (application/pdf)

    Raises:
        HazardAssessmentActivity.DoesNotExist: wenn nicht gefunden
        RuntimeError: wenn WeasyPrint nicht installiert
    """
    from gbu.models.activity import HazardAssessmentActivity

    activity = (
        HazardAssessmentActivity.objects.select_related(
            "site", "sds_revision", "sds_revision__substance"
        )
        .prefetch_related("derived_hazard_categories", "measures")
        .get(id=activity_id, tenant_id=tenant_id)
    )

    html = render_to_string(
        "gbu/pdf/gbu_document.html",
        {"activity": activity},
    )
    return _html_to_pdf(html)


def render_ba_pdf(activity_id: UUID, tenant_id: UUID) -> bytes:
    """
    Betriebsanweisung (TRGS 555) als PDF-Bytes.

    Args:
        activity_id: UUID der HazardAssessmentActivity
        tenant_id: Tenant-Isolation

    Returns:
        PDF-Bytes (application/pdf)
    """
    from gbu.models.activity import HazardAssessmentActivity

    activity = (
        HazardAssessmentActivity.objects.select_related(
            "site", "sds_revision", "sds_revision__substance"
        )
        .prefetch_related("derived_hazard_categories", "measures")
        .get(id=activity_id, tenant_id=tenant_id)
    )

    html = render_to_string(
        "gbu/pdf/ba_document.html",
        {"activity": activity},
    )
    return _html_to_pdf(html)


def _html_to_pdf(html: str) -> bytes:
    """
    HTML-String → PDF-Bytes via WeasyPrint.

    Raises RuntimeError wenn WeasyPrint nicht importiert werden kann.
    """
    try:
        from weasyprint import HTML  # type: ignore[import]
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint nicht installiert. Bitte 'pip install weasyprint' ausführen."
        ) from exc

    return HTML(string=html).write_pdf()
