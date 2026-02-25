from django.conf import settings as django_settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render


def home(request: HttpRequest) -> HttpResponse:
    tenant_slug = getattr(request, "tenant_slug", None)
    tenant_id = getattr(request, "tenant_id", None)

    if tenant_id is not None:
        if not request.user.is_authenticated:
            return redirect("/accounts/login/")
        if tenant_slug and tenant_slug.startswith("dsb"):
            return redirect("/dsb/")
        return redirect("dashboard:home")

    # No tenant — check raw host for legacy/landing pages
    host = request.get_host().split(":")[0].lower()
    if host == "dsb.iil.pet" or host.startswith("dsb."):
        return render(request, "dsb/landing.html")

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
    from django_tenancy.models import Membership, Organization

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
    """After successful login: resolve tenant and redirect."""
    from django_tenancy.models import Membership

    tenant_id = getattr(request, "tenant_id", None)

    # Already on a tenant subdomain → go straight to dashboard
    if tenant_id is not None:
        tenant_slug = getattr(request, "tenant_slug", None)
        if tenant_slug and tenant_slug.startswith("dsb"):
            return redirect("/dsb/")
        return redirect("/dashboard/")

    # On base domain → look up memberships
    memberships = (
        Membership.objects.filter(user=request.user)
        .select_related("organization")
        .order_by("organization__name")
    )
    active = [m for m in memberships if m.organization.is_active]

    if not active:
        # Staff/superuser without membership → go to /tenants/
        if request.user.is_staff:
            return redirect("/tenants/")
        return redirect("/dashboard/")

    if len(active) == 1:
        slug = active[0].organization.slug
        return _build_tenant_redirect(request, slug)

    # Multiple tenants → show picker (rendered inline)
    return render(request, "registration/tenant_picker.html", {
        "memberships": active,
    })


def _build_tenant_redirect(request: HttpRequest, slug: str) -> HttpResponse:
    """Build redirect URL for tenant subdomain."""
    base_domains = list(getattr(django_settings, "TENANT_BASE_DOMAINS", []))
    base_domain = base_domains[0] if base_domains else getattr(
        django_settings, "TENANT_BASE_DOMAIN", "localhost"
    )
    host = request.get_host()
    # Dev: keep same host:port, just prepend slug as path hint via header
    # Prod: redirect to <slug>.<base_domain>/dashboard/
    if "localhost" in host or "127.0.0.1" in host:
        # In dev we can't do subdomain redirect easily — go to dashboard directly
        return redirect("/dashboard/")
    return redirect(f"https://{slug}.{base_domain}/dashboard/")


@login_required
def tenant_pick(request: HttpRequest, slug: str) -> HttpResponse:
    """Redirect authenticated user to chosen tenant subdomain."""
    return _build_tenant_redirect(request, slug)


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    """User profile / settings page."""
    return render(request, "accounts/profile.html")
