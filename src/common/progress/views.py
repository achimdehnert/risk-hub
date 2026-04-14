# common/progress/views.py
"""
Shared Progress Rail View — HTMX-Partial für DocumentProgress (ADR-017 §8).

Rendert den Progress Rail für GBU-Tätigkeiten und Ex-Schutzkonzepte.
Pattern: View → ProgressService → Template (kein ORM in View).
HTMX-Detection: request.headers.get("HX-Request") (raw headers, kein django_htmx).
"""

import logging
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)

# Registry: doc_type → (model_class_path, progress_service_class_path)
_PROGRESS_REGISTRY: dict[str, tuple[str, str]] = {
    "gbu": (
        "gbu.models.activity.HazardAssessmentActivity",
        "gbu.services.progress.GbuProgressService",
    ),
    "ex": (
        "explosionsschutz.models.ExplosionConcept",
        "explosionsschutz.services.progress.ExProgressService",
    ),
}


def _import_class(dotted_path: str):
    """Import class from dotted module path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


@login_required
@require_GET
def progress_rail_partial(
    request: HttpRequest,
    doc_type: str,
    doc_id: str,
) -> HttpResponse:
    """
    HTMX-Partial: Progress Rail für beliebigen Dokumenttyp.

    GET /progress/<doc_type>/<doc_id>/
    Liefert den aktuellen Progress-State als HTML-Fragment.
    Auto-refresh via hx-trigger="stepChanged from:body".
    """
    if doc_type not in _PROGRESS_REGISTRY:
        raise Http404(f"Unknown doc_type: {doc_type}")

    model_path, service_path = _PROGRESS_REGISTRY[doc_type]

    try:
        model_cls = _import_class(model_path)
        service_cls = _import_class(service_path)
    except (ImportError, AttributeError) as exc:
        logger.warning("Progress registry import error: %s", exc)
        raise Http404(f"Module not available: {doc_type}") from exc

    tenant_id = str(getattr(request, "tenant_id", ""))

    try:
        document = model_cls.objects.get(
            id=UUID(doc_id),
            tenant_id=tenant_id,
        )
    except (model_cls.DoesNotExist, ValueError) as exc:
        raise Http404(f"Document not found: {doc_id}") from exc

    service = service_cls()
    progress = service.get_progress(document)

    return render(
        request,
        "components/_progress_rail.html",
        {
            "progress": progress,
            "doc_type": doc_type,
            "doc_id": str(doc_id),
        },
    )
