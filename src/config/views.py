from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def home(request: HttpRequest) -> HttpResponse:
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is not None:
        return redirect("dashboard:home")

    host = request.get_host().split(":")[0].lower()
    if host == "dsb.iil.pet":
        return render(request, "dsb/landing.html")

    return render(request, "landing.html")


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    """User profile / settings page."""
    return render(request, "accounts/profile.html")
