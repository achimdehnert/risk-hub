from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def custom_403(request: HttpRequest, exception=None) -> HttpResponse:
    """Custom 403 Forbidden handler."""
    ctx = {}
    if exception:
        ctx["error_message"] = str(exception)
    return render(request, "errors/403.html", ctx, status=403)


def custom_404(request: HttpRequest, exception=None) -> HttpResponse:
    """Custom 404 Not Found handler."""
    return render(request, "errors/404.html", {}, status=404)


def custom_500(request: HttpRequest) -> HttpResponse:
    """Custom 500 Server Error handler."""
    return render(request, "errors/500.html", {}, status=500)


def home(request: HttpRequest) -> HttpResponse:
    tenant_id = getattr(request, "tenant_id", None)

    if tenant_id is not None:
        if not request.user.is_authenticated:
            return redirect("/accounts/login/")
        return redirect("dashboard:home")

    return render(request, "landing.html")


def tenant_login(request: HttpRequest) -> HttpResponse:
    """Login view that resolves tenant via Membership and redirects to correct subdomain.

    Flow:
      1. Authenticate user (username + password)
      2. Look up Membership → get Organization.slug
      3. If on correct subdomain already → redirect to /dashboard/
      4. If on base domain (schutztat.de) → redirect to <slug>.schutztat.de/dashboard/
      5. If multiple tenants → let user pick (future: show picker)
    """
    if request.user.is_authenticated:
        return _redirect_to_tenant_dashboard(request)

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return _redirect_to_tenant_dashboard(request)
        error = "Benutzername oder Passwort ist ungültig."

    return render(request, "registration/login.html", {"error": error})


def _redirect_to_tenant_dashboard(request: HttpRequest) -> HttpResponse:
    """After successful login: always redirect to /dashboard/ on current domain.

    Tenant context is resolved via user.tenant_id in middleware — no subdomain
    redirect needed. Modules are freely selectable per user, not per subdomain.
    """
    from django_tenancy.models import Membership

    # If tenant already set (subdomain or header) → go to dashboard
    tenant_id = getattr(request, "tenant_id", None)
    if tenant_id is not None:
        return redirect("/dashboard/")

    # No tenant context yet → look up via membership and set on request
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("organization")
        .order_by("organization__name")
    )
    active = [m for m in memberships if m.organization.is_active]

    if not active:
        if request.user.is_staff:
            return redirect("/tenants/")
        return redirect("/dashboard/")

    if len(active) == 1:
        # Set tenant on request so middleware picks it up for this request
        org = active[0].organization
        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = org.slug
        from common.context import set_db_tenant, set_tenant

        set_tenant(org.tenant_id, org.slug)
        set_db_tenant(org.tenant_id)
        return redirect("/dashboard/")

    # Multiple orgs → let user pick
    return render(
        request,
        "registration/tenant_picker.html",
        {"memberships": active},
    )


@login_required
def tenant_pick(request: HttpRequest, slug: str) -> HttpResponse:
    """Set tenant context to chosen org and redirect to dashboard."""
    from tenancy.models import Organization
    from common.context import set_db_tenant, set_tenant

    try:
        org = Organization.objects.get(slug=slug)
        request.tenant = org
        request.tenant_id = org.tenant_id
        request.tenant_slug = org.slug
        set_tenant(org.tenant_id, org.slug)
        set_db_tenant(org.tenant_id)
    except Organization.DoesNotExist:
        pass
    return redirect("/dashboard/")


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    """User profile / settings page."""
    return render(request, "accounts/profile.html")
