from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def home(request: HttpRequest) -> HttpResponse:
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is not None:
        return redirect("dashboard:home")

    return render(request, "landing.html")
