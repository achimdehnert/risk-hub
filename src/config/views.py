from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def home(request: HttpRequest) -> HttpResponse:
    tenant_slug = getattr(request, "tenant_slug", None)
    tenant_id = getattr(request, "tenant_id", None)

    if tenant_id is not None:
        # Route to module dashboard based on subdomain slug
        if tenant_slug and tenant_slug.startswith("dsb"):
            return redirect("/dsb/")
        return redirect("dashboard:home")

    # No tenant — check raw host for legacy/landing pages
    host = request.get_host().split(":")[0].lower()
    if host == "dsb.iil.pet" or host.startswith("dsb."):
        return render(request, "dsb/landing.html")

    return render(request, "landing.html")


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    """User profile / settings page."""
    return render(request, "accounts/profile.html")
