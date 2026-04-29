from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from tenancy.models import Facility
from .models import IntakeUpload
from .registry import all_handlers
from . import services

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def intake_new(request: HttpRequest) -> HttpResponse:
    facilities = Facility.objects.filter(is_active=True).order_by("name")
    return render(request, "intake/new.html", {"facilities": facilities})


@login_required
@require_http_methods(["POST"])
def intake_upload(request: HttpRequest) -> HttpResponse:
    facility_id = request.POST.get("facility")
    uploaded_file = request.FILES.get("file")

    if not facility_id or not uploaded_file:
        return HttpResponse("Betrieb und Datei sind Pflichtfelder.", status=400)

    facility = get_object_or_404(Facility, pk=facility_id)
    upload = IntakeUpload.objects.create(
        facility=facility,
        original_filename=uploaded_file.name,
        file=uploaded_file,
    )

    services.ingest_file(upload)

    handlers = all_handlers()
    return render(request, "intake/partials/_target_selection.html", {
        "upload": upload,
        "handlers": handlers,
    })


@login_required
@require_http_methods(["POST"])
def intake_route(request: HttpRequest, pk: int) -> HttpResponse:
    upload = get_object_or_404(IntakeUpload, pk=pk)
    selected = request.POST.getlist("targets")
    upload.selected_targets = selected
    upload.save(update_fields=["selected_targets", "updated_at"])

    results = services.route(upload)

    return render(request, "intake/partials/_results.html", {
        "upload": upload,
        "results": results,
        "handlers": {h.target_code: h for h in all_handlers()},
    })
