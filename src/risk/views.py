"""Risk assessment views."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest

from risk.models import Assessment
from risk.services import create_assessment, approve_assessment, CreateAssessmentCmd, ApproveAssessmentCmd


def assessment_list(request):
    """List all assessments for current tenant."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "general")
        
        if not title:
            return HttpResponseBadRequest("Title required")
        
        create_assessment(CreateAssessmentCmd(title=title, category=category))
        return redirect("risk:assessment_list")
    
    assessments = Assessment.objects.order_by("-created_at")[:100]
    return render(request, "risk/assessment_list.html", {"assessments": assessments})


def assessment_detail(request, assessment_id):
    """View assessment details."""
    assessment = get_object_or_404(Assessment, id=assessment_id)
    return render(request, "risk/assessment_detail.html", {"assessment": assessment})


def assessment_approve(request, assessment_id):
    """Approve an assessment."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    
    approve_assessment(ApproveAssessmentCmd(assessment_id=assessment_id))
    return redirect("risk:assessment_list")
