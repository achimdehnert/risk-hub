"""
HTMX Views für das Explosionsschutz-Modul.

Wizard-Flow (5 Schritte):
  Step 1: Grunddaten (Bereich, Stoff, Verfahren, Substitutionsprüfung)
  Step 2: Freisetzungsquellen + automatischer Zonenvorschlag
  Step 3: Zündquellenbewertung (13 Quellen nach EN 1127-1)
  Step 4: Schutzmaßnahmen (Primär/Sekundär/Konstruktiv/Organisatorisch)
  Step 5: Überprüfung + Freigabe-Workflow

Ergänzend: Equipment CRUD, Inspection Recording, Verification Documents.
"""
from __future__ import annotations

import uuid

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.request_context import get_context
from apps.permissions.decorators import require_permission

from .forms import (
    ConceptBasicForm,
    ConceptReleaseForm,
    InspectionForm,
    MeasureForm,
    ZoneForm,
)
from .models import (
    Area,
    Equipment,
    ExplosionConcept,
    IgnitionSource,
    ZoneDefinition,
)
from .services import (
    ApproveConceptCmd,
    ArchiveConceptCmd,
    AssessIgnitionSourceCmd,
    ConceptService,
    CreateConceptCmd,
    CreateMeasureCmd,
    CreateZoneCmd,
    EquipmentService,
    MeasureService,
    RecordInspectionCmd,
    SubmitForReviewCmd,
    UpdateConceptCmd,
    ZoneService,
)
from .services.zone_classification import ZoneClassificationEngine

# ============================================================================
# Dashboard + Übersichtsseiten
# ============================================================================


@login_required
@require_permission("explosionsschutz.view_concept")
def concept_list(request: HttpRequest) -> HttpResponse:
    ctx = get_context()
    concepts = (
        ExplosionConcept.objects.filter(tenant_id=ctx.tenant_id, is_current=True)
        .select_related("area")
        .order_by("area__code", "-created_at")
    )
    if request.htmx:
        return render(
            request,
            "explosionsschutz/partials/concept_table.html",
            {"concepts": concepts},
        )
    return TemplateResponse(
        request,
        "explosionsschutz/concept_list.html",
        {"concepts": concepts},
    )


@login_required
@require_permission("explosionsschutz.view_concept")
def concept_detail(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    concept = get_object_or_404(
        ExplosionConcept.objects.select_related("area")
        .prefetch_related(
            "zones__ignition_assessments",
            "measures__safety_function",
            "verification_documents__document",
        ),
        pk=pk,
        tenant_id=ctx.tenant_id,
    )
    return TemplateResponse(
        request,
        "explosionsschutz/concept_detail.html",
        {
            "concept": concept,
            "measures_by_category": _group_measures(concept),
            "zone_completion": _zone_completion_map(concept),
        },
    )


# ============================================================================
# Wizard
# ============================================================================


@login_required
@require_permission("explosionsschutz.add_concept")
def wizard_create(request: HttpRequest) -> HttpResponse:
    """Startet einen neuen Wizard – Schritt 1."""
    ctx = get_context()
    areas = Area.objects.filter(tenant_id=ctx.tenant_id, is_active=True)

    if request.method == "POST":
        form = ConceptBasicForm(request.POST)
        if form.is_valid():
            cmd = CreateConceptCmd(
                area_id=form.cleaned_data["area_id"],
                title=form.cleaned_data["title"],
                substance_id=form.cleaned_data.get("substance_id"),
                atmosphere_type=form.cleaned_data["atmosphere_type"],
                process_description=form.cleaned_data.get("process_description", ""),
                document_number=form.cleaned_data.get("document_number", ""),
            )
            concept = ConceptService.create_concept(
                cmd=cmd,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                author_name=request.user.get_full_name(),
            )
            return redirect("explosionsschutz:wizard-step2", pk=concept.pk)
    else:
        form = ConceptBasicForm()

    return TemplateResponse(
        request,
        "explosionsschutz/wizard/step1_basic.html",
        {"form": form, "areas": areas, "step": 1},
    )


@login_required
@require_permission("explosionsschutz.change_concept")
def wizard_step2(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Schritt 2: Freisetzungsquellen + automatischer Zonenvorschlag."""
    ctx = get_context()
    concept = get_object_or_404(
        ExplosionConcept, pk=pk, tenant_id=ctx.tenant_id
    )

    engine = ZoneClassificationEngine()

    if request.method == "POST":
        form = ConceptReleaseForm(request.POST, instance=concept)
        if form.is_valid():
            cmd = UpdateConceptCmd(
                concept_id=concept.id,
                substitute_check_status=form.cleaned_data["substitute_check_status"],
                substitute_check_notes=form.cleaned_data.get("substitute_check_notes", ""),
                release_source_type=form.cleaned_data["release_source_type"],
                release_grade=form.cleaned_data["release_grade"],
                release_description=form.cleaned_data.get("release_description", ""),
            )
            ConceptService.update_concept(cmd, ctx.tenant_id, ctx.user_id)
            return redirect("explosionsschutz:wizard-step3", pk=pk)
    else:
        form = ConceptReleaseForm(instance=concept)

    # Zonenvorschlag berechnen (für Anzeige)
    zone_proposal = None
    if concept.release_grade and concept.atmosphere_type:
        zone_proposal = engine.propose(
            release_grade=concept.release_grade,
            ventilation_type="natural",  # Default; wird in Zonenformular verfeinert
            atmosphere_type=concept.atmosphere_type,
        )

    return TemplateResponse(
        request,
        "explosionsschutz/wizard/step2_release.html",
        {"form": form, "concept": concept, "zone_proposal": zone_proposal, "step": 2},
    )


@login_required
@require_permission("explosionsschutz.change_concept")
def wizard_step3(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Schritt 3: Zonen definieren + Zündquellenbewertung."""
    ctx = get_context()
    concept = get_object_or_404(
        ExplosionConcept.objects.prefetch_related("zones__ignition_assessments"),
        pk=pk,
        tenant_id=ctx.tenant_id,
    )
    return TemplateResponse(
        request,
        "explosionsschutz/wizard/step3_zones.html",
        {
            "concept": concept,
            "zones": concept.zones.all(),
            "zone_form": ZoneForm(initial={
                "ventilation_type": "natural",
            }),
            "ignition_sources": list(IgnitionSource),
            "step": 3,
        },
    )


@login_required
@require_permission("explosionsschutz.change_concept")
def wizard_step4(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Schritt 4: Schutzmaßnahmen."""
    ctx = get_context()
    concept = get_object_or_404(
        ExplosionConcept.objects.prefetch_related("measures"),
        pk=pk,
        tenant_id=ctx.tenant_id,
    )
    return TemplateResponse(
        request,
        "explosionsschutz/wizard/step4_measures.html",
        {
            "concept": concept,
            "measures": concept.measures.all(),
            "measure_form": MeasureForm(),
            "categories": [
                ("primary", "Primär (Vermeidung ex. Atmosphäre)"),
                ("secondary", "Sekundär (Zündquellenvermeidung)"),
                ("constructive", "Konstruktiv (Schadensminimierung)"),
                ("organisational", "Organisatorisch"),
            ],
            "step": 4,
        },
    )


@login_required
@require_permission("explosionsschutz.change_concept")
def wizard_step5(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """Schritt 5: Überprüfung + Einreichen zur Freigabe."""
    ctx = get_context()
    concept = get_object_or_404(
        ExplosionConcept.objects.select_related("area").prefetch_related(
            "zones", "measures", "verification_documents"
        ),
        pk=pk,
        tenant_id=ctx.tenant_id,
    )

    if request.method == "POST":
        cmd = SubmitForReviewCmd(
            concept_id=concept.id,
            notes=request.POST.get("notes", ""),
        )
        try:
            ConceptService.submit_for_review(cmd, ctx.tenant_id, ctx.user_id)
            return redirect("explosionsschutz:concept-detail", pk=pk)
        except Exception as exc:
            return TemplateResponse(
                request,
                "explosionsschutz/wizard/step5_review.html",
                {"concept": concept, "error": str(exc), "step": 5},
            )

    return TemplateResponse(
        request,
        "explosionsschutz/wizard/step5_review.html",
        {"concept": concept, "step": 5},
    )


# ============================================================================
# HTMX Partials: Zonen
# ============================================================================


@login_required
@require_http_methods(["POST"])
def zone_add(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """HTMX: Zone zum Konzept hinzufügen."""
    ctx = get_context()
    form = ZoneForm(request.POST)

    if form.is_valid():
        engine = ZoneClassificationEngine()
        ventilation = form.cleaned_data.get("ventilation_type", "natural")
        concept = get_object_or_404(
            ExplosionConcept, pk=pk, tenant_id=ctx.tenant_id
        )

        proposal = engine.propose(
            release_grade=concept.release_grade or "secondary",
            ventilation_type=ventilation,
            atmosphere_type=concept.atmosphere_type,
        )

        cmd = CreateZoneCmd(
            concept_id=pk,
            zone_type=form.cleaned_data.get("zone_type") or proposal.zone_type,
            name=form.cleaned_data["name"],
            justification=form.cleaned_data.get("justification") or proposal.justification,
            location_in_area=form.cleaned_data.get("location_in_area", ""),
            extent_shape=form.cleaned_data.get("extent_shape", "custom"),
            extent_description=form.cleaned_data.get("extent_description", ""),
            ventilation_type=ventilation,
        )
        zone = ZoneService.create_zone(cmd, ctx.tenant_id, ctx.user_id)
        return TemplateResponse(
            request,
            "explosionsschutz/partials/zone_row.html",
            {"zone": zone, "concept": concept},
        )

    return TemplateResponse(
        request,
        "explosionsschutz/partials/zone_form_errors.html",
        {"form": form},
        status=422,
    )


@login_required
@require_http_methods(["GET"])
def zone_proposal_htmx(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """HTMX: Zonenvorschlag berechnen (live, ohne Speichern)."""
    ctx = get_context()
    concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=ctx.tenant_id)

    engine = ZoneClassificationEngine()
    release_grade = request.GET.get("release_grade") or concept.release_grade or "secondary"
    ventilation = request.GET.get("ventilation_type", "natural")

    proposal = engine.propose(
        release_grade=release_grade,
        ventilation_type=ventilation,
        atmosphere_type=concept.atmosphere_type,
    )
    return TemplateResponse(
        request,
        "explosionsschutz/partials/zone_proposal.html",
        {"proposal": proposal, "concept": concept},
    )


# ============================================================================
# HTMX Partials: Zündquellen
# ============================================================================


@login_required
@require_http_methods(["GET", "POST"])
def ignition_assessment(request: HttpRequest, zone_pk: uuid.UUID) -> HttpResponse:
    """HTMX: Alle 13 Zündquellen einer Zone auf einmal bewerten."""
    ctx = get_context()
    zone = get_object_or_404(ZoneDefinition, pk=zone_pk, tenant_id=ctx.tenant_id)

    assessments = {
        a.ignition_source: a
        for a in zone.ignition_assessments.all()
    }

    if request.method == "POST":
        for source in IgnitionSource:
            key = source.value
            cmd = AssessIgnitionSourceCmd(
                zone_id=zone_pk,
                ignition_source=key,
                is_present=request.POST.get(f"present_{key}") == "on",
                is_effective=request.POST.get(f"effective_{key}") == "on",
                mitigation=request.POST.get(f"mitigation_{key}", ""),
                residual_risk_acceptable=request.POST.get(f"risk_ok_{key}") != "off",
            )
            ZoneService.assess_ignition_source(cmd, ctx.tenant_id, ctx.user_id)

        # Aktualisierte Assessments laden
        assessments = {
            a.ignition_source: a
            for a in zone.ignition_assessments.all()
        }
        return TemplateResponse(
            request,
            "explosionsschutz/partials/ignition_table.html",
            {
                "zone": zone,
                "assessments": assessments,
                "ignition_sources": list(IgnitionSource),
                "saved": True,
            },
        )

    return TemplateResponse(
        request,
        "explosionsschutz/partials/ignition_assessment_form.html",
        {
            "zone": zone,
            "assessments": assessments,
            "ignition_sources": list(IgnitionSource),
        },
    )


# ============================================================================
# HTMX Partials: Maßnahmen
# ============================================================================


@login_required
@require_http_methods(["POST"])
def measure_add(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    """HTMX: Schutzmaßnahme hinzufügen."""
    ctx = get_context()
    form = MeasureForm(request.POST)

    if form.is_valid():
        cmd = CreateMeasureCmd(
            concept_id=pk,
            category=form.cleaned_data["category"],
            title=form.cleaned_data["title"],
            description=form.cleaned_data["description"],
            justification=form.cleaned_data.get("justification", ""),
            status=form.cleaned_data.get("status", "done"),
        )
        measure = MeasureService.create_measure(cmd, ctx.tenant_id, ctx.user_id)
        concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=ctx.tenant_id)
        return TemplateResponse(
            request,
            "explosionsschutz/partials/measure_row.html",
            {"measure": measure, "concept": concept},
        )

    return TemplateResponse(
        request,
        "explosionsschutz/partials/measure_form_errors.html",
        {"form": form},
        status=422,
    )


# ============================================================================
# Freigabe-Workflow
# ============================================================================


@login_required
@require_POST
@require_permission("explosionsschutz.approve_concept")
def concept_approve(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    cmd = ApproveConceptCmd(
        concept_id=pk,
        approver_id=ctx.user_id,
        approver_name=request.user.get_full_name(),
        notes=request.POST.get("notes", ""),
    )
    ConceptService.approve_concept(cmd, ctx.tenant_id, ctx.user_id)
    return redirect("explosionsschutz:concept-detail", pk=pk)


@login_required
@require_POST
@require_permission("explosionsschutz.archive_concept")
def concept_archive(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    cmd = ArchiveConceptCmd(
        concept_id=pk,
        reason=request.POST.get("reason", ""),
    )
    ConceptService.archive_concept(cmd, ctx.tenant_id, ctx.user_id)
    return redirect("explosionsschutz:concept-list")


# ============================================================================
# Equipment + Inspections
# ============================================================================


@login_required
@require_permission("explosionsschutz.view_equipment")
def equipment_list(request: HttpRequest) -> HttpResponse:
    ctx = get_context()
    equipment = (
        Equipment.objects.filter(tenant_id=ctx.tenant_id, is_active=True)
        .select_related("area", "equipment_type")
        .order_by("area__code", "name")
    )
    overdue = [e for e in equipment if e.inspection_status.value == "overdue"]
    due_soon = [e for e in equipment if e.inspection_status.value == "due_soon"]

    return TemplateResponse(
        request,
        "explosionsschutz/equipment_list.html",
        {"equipment": equipment, "overdue": overdue, "due_soon": due_soon},
    )


@login_required
@require_permission("explosionsschutz.view_equipment")
def equipment_detail(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    equipment = get_object_or_404(
        Equipment.objects.select_related("area", "equipment_type").prefetch_related(
            "inspections", "zones"
        ),
        pk=pk,
        tenant_id=ctx.tenant_id,
    )
    return TemplateResponse(
        request,
        "explosionsschutz/equipment_detail.html",
        {
            "equipment": equipment,
            "inspection_form": InspectionForm(),
            "inspections": equipment.inspections.all()[:20],
        },
    )


@login_required
@require_POST
@require_permission("explosionsschutz.add_inspection")
def inspection_record(request: HttpRequest, equipment_pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    form = InspectionForm(request.POST)

    if form.is_valid():
        cmd = RecordInspectionCmd(
            equipment_id=equipment_pk,
            inspection_type=form.cleaned_data["inspection_type"],
            scheduled_date=form.cleaned_data["scheduled_date"],
            performed_date=form.cleaned_data.get("performed_date"),
            performed_by_id=ctx.user_id,
            performed_by_name=request.user.get_full_name(),
            external_inspector=form.cleaned_data.get("external_inspector", ""),
            result=form.cleaned_data.get("result"),
            findings=form.cleaned_data.get("findings", ""),
            corrective_actions=form.cleaned_data.get("corrective_actions", ""),
            next_inspection_date=form.cleaned_data.get("next_inspection_date"),
        )
        inspection = EquipmentService.record_inspection(cmd, ctx.tenant_id, ctx.user_id)
        if request.htmx:
            return TemplateResponse(
                request,
                "explosionsschutz/partials/inspection_row.html",
                {"inspection": inspection},
            )
        return redirect("explosionsschutz:equipment-detail", pk=equipment_pk)

    if request.htmx:
        return TemplateResponse(
            request,
            "explosionsschutz/partials/inspection_form_errors.html",
            {"form": form},
            status=422,
        )
    return redirect("explosionsschutz:equipment-detail", pk=equipment_pk)


# ============================================================================
# Fortschritts-Partial (HTMX Polling)
# ============================================================================


@login_required
def concept_progress(request: HttpRequest, pk: uuid.UUID) -> HttpResponse:
    ctx = get_context()
    concept = get_object_or_404(ExplosionConcept, pk=pk, tenant_id=ctx.tenant_id)
    return TemplateResponse(
        request,
        "explosionsschutz/partials/progress_bar.html",
        {"concept": concept, "pct": concept.completion_percentage},
    )


# ============================================================================
# Helpers
# ============================================================================


def _group_measures(concept: ExplosionConcept) -> dict:
    groups: dict = {
        "primary": [],
        "secondary": [],
        "constructive": [],
        "organisational": [],
    }
    for measure in concept.measures.all():
        groups.setdefault(measure.category, []).append(measure)
    return groups


def _zone_completion_map(concept: ExplosionConcept) -> dict[str, bool]:
    return {
        str(zone.id): zone.ignition_assessment_complete
        for zone in concept.zones.all()
    }
