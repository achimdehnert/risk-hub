"""Risk assessment views (UC-008)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from common.tenant import require_tenant as _require_tenant
from risk.forms import (
    AssessmentForm,
    HazardForm,
    ProtectiveMeasureForm,
    SubstitutionCheckForm,
)
from risk.models import Assessment, Hazard, ProtectiveMeasure, SubstitutionCheck

ITEMS_PER_PAGE = 25


def _tenant(request):
    """Return tenant_id or redirect."""
    resp = _require_tenant(request)
    if resp is not None:
        return None, resp
    return request.tenant_id, None


# =========================================================================
# Dashboard
# =========================================================================


@login_required
def risk_dashboard(request: HttpRequest) -> HttpResponse:
    """Risk module dashboard with KPIs."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    today = timezone.now().date()
    assessments = Assessment.objects.filter(tenant_id=tenant_id)
    hazards = Hazard.objects.filter(tenant_id=tenant_id)
    measures = ProtectiveMeasure.objects.filter(tenant_id=tenant_id)

    ctx = {
        "total_assessments": assessments.count(),
        "draft_count": assessments.filter(status="draft").count(),
        "approved_count": assessments.filter(status="approved").count(),
        "total_hazards": hazards.count(),
        "open_hazards": hazards.filter(mitigation_status="open").count(),
        "overdue_hazards": hazards.filter(
            mitigation_status__in=["open", "in_progress"],
            due_date__lt=today,
        ).count(),
        "measures_open": measures.filter(status="open").count(),
        "measures_implemented": measures.filter(status="implemented").count(),
        "recent_assessments": assessments.order_by("-updated_at")[:5],
        "overdue_items": hazards.filter(
            mitigation_status__in=["open", "in_progress"],
            due_date__lt=today,
        ).select_related("assessment").order_by("due_date")[:10],
    }
    return render(request, "risk/dashboard.html", ctx)


# =========================================================================
# Assessment CRUD
# =========================================================================


@login_required
def assessment_list(request: HttpRequest) -> HttpResponse:
    """List all assessments for current tenant."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    qs = (
        Assessment.objects.filter(tenant_id=tenant_id)
        .annotate(
            hazard_count=Count("hazards"),
            open_count=Count("hazards", filter=Q(hazards__mitigation_status="open")),
        )
        .order_by("-created_at")
    )

    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category=category_filter)

    paginator = Paginator(qs, ITEMS_PER_PAGE)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "risk/assessment_list.html", {
        "assessments": page,
        "page_obj": page,
        "filters": {"status": status_filter, "category": category_filter},
        "status_choices": Assessment.Status.choices,
        "category_choices": Assessment.Category.choices,
    })


@login_required
def assessment_create(request: HttpRequest) -> HttpResponse:
    """Create a new assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method == "POST":
        form = AssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.tenant_id = tenant_id
            assessment.created_by_id = getattr(request.user, "pk", None)
            assessment.save()
            messages.success(request, f"Bewertung '{assessment.title}' erstellt.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = AssessmentForm()

    return render(request, "risk/assessment_form.html", {
        "form": form,
        "title": "Neue Gefährdungsbeurteilung",
    })


@login_required
def assessment_detail(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """View assessment details with hazards and measures."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    hazards = assessment.hazards.order_by("-severity", "-probability")
    measures = ProtectiveMeasure.objects.filter(
        tenant_id=tenant_id, assessment=assessment,
    ).order_by("measure_type", "-created_at")
    substitution_checks = SubstitutionCheck.objects.filter(
        tenant_id=tenant_id, assessment=assessment,
    ).select_related("current_product", "alternative_product").order_by("-checked_at")

    return render(request, "risk/assessment_detail.html", {
        "assessment": assessment,
        "hazards": hazards,
        "measures": measures,
        "substitution_checks": substitution_checks,
        "stop_types": ProtectiveMeasure.MeasureType,
    })


@login_required
def assessment_edit(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Edit assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)

    if request.method == "POST":
        form = AssessmentForm(request.POST, instance=assessment)
        if form.is_valid():
            form.save()
            messages.success(request, "Bewertung aktualisiert.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = AssessmentForm(instance=assessment)

    return render(request, "risk/assessment_form.html", {
        "form": form,
        "assessment": assessment,
        "title": f"Bewertung bearbeiten: {assessment.title}",
    })


@login_required
def assessment_approve(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Approve an assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    assessment.status = "approved"
    assessment.approved_by_id = getattr(request.user, "pk", None)
    assessment.approved_at = timezone.now()
    assessment.save(update_fields=["status", "approved_by_id", "approved_at", "updated_at"])
    messages.success(request, f"Bewertung '{assessment.title}' freigegeben.")
    return redirect("risk:assessment_detail", assessment_id=assessment.pk)


@login_required
def assessment_delete(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Delete (archive) an assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    title = assessment.title
    assessment.delete()
    messages.success(request, f"Bewertung '{title}' gelöscht.")
    return redirect("risk:assessment_list")


# =========================================================================
# Hazard CRUD
# =========================================================================


@login_required
def hazard_create(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Add a hazard to an assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)

    if request.method == "POST":
        form = HazardForm(request.POST)
        if form.is_valid():
            hazard = form.save(commit=False)
            hazard.tenant_id = tenant_id
            hazard.assessment = assessment
            hazard.save()
            messages.success(request, f"Gefährdung '{hazard.title}' hinzugefügt.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = HazardForm()

    return render(request, "risk/hazard_form.html", {
        "form": form,
        "assessment": assessment,
        "title": "Neue Gefährdung",
    })


@login_required
def hazard_edit(request: HttpRequest, assessment_id: int, hazard_id: int) -> HttpResponse:
    """Edit a hazard."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    hazard = get_object_or_404(Hazard, id=hazard_id, tenant_id=tenant_id, assessment=assessment)

    if request.method == "POST":
        form = HazardForm(request.POST, instance=hazard)
        if form.is_valid():
            form.save()
            messages.success(request, "Gefährdung aktualisiert.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = HazardForm(instance=hazard)

    return render(request, "risk/hazard_form.html", {
        "form": form,
        "assessment": assessment,
        "hazard": hazard,
        "title": f"Gefährdung bearbeiten: {hazard.title}",
    })


@login_required
def hazard_delete(request: HttpRequest, assessment_id: int, hazard_id: int) -> HttpResponse:
    """Delete a hazard."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    hazard = get_object_or_404(Hazard, id=hazard_id, tenant_id=tenant_id, assessment=assessment)

    if request.method == "POST":
        hazard.delete()
        messages.success(request, "Gefährdung gelöscht.")
    return redirect("risk:assessment_detail", assessment_id=assessment.pk)


# =========================================================================
# Protective Measures (STOP Hierarchy, UC-008)
# =========================================================================


@login_required
def measure_create(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Add a protective measure (STOP) to an assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    hazard_id = request.GET.get("hazard")

    if request.method == "POST":
        form = ProtectiveMeasureForm(request.POST)
        if form.is_valid():
            measure = form.save(commit=False)
            measure.tenant_id = tenant_id
            measure.assessment = assessment
            if request.POST.get("hazard"):
                measure.hazard_id = int(request.POST["hazard"])
            measure.responsible_user_id = getattr(request.user, "pk", None)
            measure.save()
            messages.success(request, "Schutzmaßnahme hinzugefügt.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        initial = {}
        if request.GET.get("type"):
            initial["measure_type"] = request.GET["type"]
        form = ProtectiveMeasureForm(initial=initial)

    hazards = assessment.hazards.all()
    return render(request, "risk/measure_form.html", {
        "form": form,
        "assessment": assessment,
        "hazards": hazards,
        "selected_hazard": int(hazard_id) if hazard_id else None,
        "title": "Neue Schutzmaßnahme (STOP)",
    })


@login_required
def measure_edit(request: HttpRequest, assessment_id: int, measure_id: int) -> HttpResponse:
    """Edit a protective measure."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    measure = get_object_or_404(ProtectiveMeasure, id=measure_id, tenant_id=tenant_id, assessment=assessment)

    if request.method == "POST":
        form = ProtectiveMeasureForm(request.POST, instance=measure)
        if form.is_valid():
            form.save()
            messages.success(request, "Schutzmaßnahme aktualisiert.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = ProtectiveMeasureForm(instance=measure)

    return render(request, "risk/measure_form.html", {
        "form": form,
        "assessment": assessment,
        "measure": measure,
        "hazards": assessment.hazards.all(),
        "title": "Schutzmaßnahme bearbeiten",
    })


@login_required
def measure_complete(request: HttpRequest, assessment_id: int, measure_id: int) -> HttpResponse:
    """Mark a measure as implemented."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    measure = get_object_or_404(
        ProtectiveMeasure, id=measure_id, tenant_id=tenant_id, assessment_id=assessment_id,
    )
    measure.status = "implemented"
    measure.effectiveness_checked_at = timezone.now()
    measure.save(update_fields=["status", "effectiveness_checked_at", "updated_at"])
    messages.success(request, "Maßnahme als umgesetzt markiert.")
    return redirect("risk:assessment_detail", assessment_id=assessment_id)


@login_required
def measure_delete(request: HttpRequest, assessment_id: int, measure_id: int) -> HttpResponse:
    """Delete a protective measure."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    measure = get_object_or_404(
        ProtectiveMeasure, id=measure_id, tenant_id=tenant_id, assessment_id=assessment_id,
    )
    measure.delete()
    messages.success(request, "Schutzmaßnahme gelöscht.")
    return redirect("risk:assessment_detail", assessment_id=assessment_id)


# =========================================================================
# Substitution Check (UC-008)
# =========================================================================


@login_required
def substitution_create(request: HttpRequest, assessment_id: int) -> HttpResponse:
    """Create a substitution check for an assessment."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)

    if request.method == "POST":
        form = SubstitutionCheckForm(request.POST)
        if form.is_valid():
            check = form.save(commit=False)
            check.tenant_id = tenant_id
            check.assessment = assessment
            check.checked_by = getattr(request.user, "pk", None)
            check.checked_at = timezone.now()
            if request.POST.get("current_product"):
                check.current_product_id = int(request.POST["current_product"])
            if request.POST.get("substance_usage"):
                check.substance_usage_id = int(request.POST["substance_usage"])
            check.save()
            messages.success(request, "Substitutionsprüfung dokumentiert.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = SubstitutionCheckForm()

    from substances.models import Product

    products = Product.objects.filter(tenant_id=tenant_id, status="active").order_by("trade_name")

    return render(request, "risk/substitution_form.html", {
        "form": form,
        "assessment": assessment,
        "products": products,
        "title": "Substitutionsprüfung",
    })


@login_required
def substitution_edit(request: HttpRequest, assessment_id: int, check_id: int) -> HttpResponse:
    """Edit a substitution check."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    assessment = get_object_or_404(Assessment, id=assessment_id, tenant_id=tenant_id)
    check = get_object_or_404(SubstitutionCheck, id=check_id, tenant_id=tenant_id, assessment=assessment)

    if request.method == "POST":
        form = SubstitutionCheckForm(request.POST, instance=check)
        if form.is_valid():
            form.save()
            messages.success(request, "Substitutionsprüfung aktualisiert.")
            return redirect("risk:assessment_detail", assessment_id=assessment.pk)
    else:
        form = SubstitutionCheckForm(instance=check)

    from substances.models import Product

    products = Product.objects.filter(tenant_id=tenant_id, status="active").order_by("trade_name")

    return render(request, "risk/substitution_form.html", {
        "form": form,
        "assessment": assessment,
        "check": check,
        "products": products,
        "title": "Substitutionsprüfung bearbeiten",
    })


@login_required
def substitution_delete(request: HttpRequest, assessment_id: int, check_id: int) -> HttpResponse:
    """Delete a substitution check."""
    tenant_id, err = _tenant(request)
    if err:
        return err

    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    check = get_object_or_404(
        SubstitutionCheck, id=check_id, tenant_id=tenant_id, assessment_id=assessment_id,
    )
    check.delete()
    messages.success(request, "Substitutionsprüfung gelöscht.")
    return redirect("risk:assessment_detail", assessment_id=assessment_id)
