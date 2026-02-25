from django.shortcuts import render

def assessment_list(request):
    """Liste aller Gefährdungsbeurteilungen."""
    return render(request, "risk/assessment_list.html", {"assessments": []})
