# src/global_sds/views_partials.py
"""
HTMX-Partials für SDS Datacard (ADR-017 §8).

Liefert eine read-only Gefahrstoff-Info-Karte als HTML-Fragment.
Pattern: Views → Models (read-only, kein Service nötig).
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from global_sds.models import GlobalSdsRevision

logger = logging.getLogger(__name__)


@login_required
@require_GET
def sds_datacard_partial(
    request: HttpRequest,
    pk: int,
) -> HttpResponse:
    """
    HTMX-Partial: SDS Datacard für eine GlobalSdsRevision.

    GET /sds/datacard/<pk>/
    Liefert read-only Gefahrstoff-Info als HTML-Fragment.
    Verwendet in GBU Step 1 und Ex-Konzept Step 1.
    """
    tenant_id = str(getattr(request, "tenant_id", ""))

    try:
        revision = (
            GlobalSdsRevision.objects.visible_for_tenant(tenant_id)
            .select_related("substance")
            .prefetch_related("hazard_statements")
            .get(pk=pk)
        )
    except GlobalSdsRevision.DoesNotExist as exc:
        raise Http404("SDS-Revision nicht gefunden") from exc

    return render(
        request,
        "components/_sds_datacard.html",
        {"revision": revision},
    )
