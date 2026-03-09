import json
import urllib.parse
import urllib.request

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


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

    host = request.get_host().split(":")[0]
    is_staging = host.startswith("staging.")
    template = "landing_staging.html" if is_staging else "landing.html"
    return render(request, template)


@require_POST
def trial_request(request: HttpRequest) -> JsonResponse:
    """Receive trial lead from Konfigurator and send notification email."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"ok": False, "error": "Ungültige Anfrage"}, status=400)

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    company = data.get("company", "").strip()
    phone = data.get("phone", "").strip()
    plan = data.get("plan", "").strip()
    modules = data.get("modules", "").strip()

    if not name or not email:
        return JsonResponse({"ok": False, "error": "Name und E-Mail sind pflicht"}, status=400)

    subject = f"[Schutztat] Trial-Anfrage: {plan.upper()} — {name}"
    body = (
        f"Neue Trial-Anfrage über den Konfigurator:\n\n"
        f"Name:     {name}\n"
        f"E-Mail:   {email}\n"
        f"Firma:    {company or '—'}\n"
        f"Telefon:  {phone or '—'}\n\n"
        f"Plan:     {plan.upper()}\n"
        f"Module:   {modules}\n\n"
        f"--- Automatisch generiert von staging.schutztat.de ---"
    )

    from django.conf import settings
    api_token = getattr(settings, "FORWARDEMAIL_API_TOKEN", "")
    if not api_token:
        import os
        api_token = os.environ.get("FORWARDEMAIL_API_TOKEN", "")

    try:
        payload = urllib.parse.urlencode({
            "from": "noreply@schutztat.de",
            "to": "info@schutztat.de",
            "subject": subject,
            "text": body,
        }).encode()
        credentials = (
            api_token + ":"
        ).encode()
        import base64
        auth = base64.b64encode(credentials).decode()
        req = urllib.request.Request(
            "https://api.forwardemail.net/v1/emails",
            data=payload,
            headers={"Authorization": f"Basic {auth}"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    return JsonResponse({"ok": True})


def register(request: HttpRequest) -> HttpResponse:
    """Self-service registration — only exposed on staging."""
    host = request.get_host().split(":")[0]
    is_staging = host.startswith("staging.") or host in ("localhost", "127.0.0.1")
    if not is_staging:
        return redirect("/")

    plan = request.GET.get("plan", "")
    modules = request.GET.get("modules", "")
    error = None

    if request.method == "POST":
        from django.contrib.auth import get_user_model

        User = get_user_model()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        plan = request.POST.get("plan", "")
        modules = request.POST.get("modules", "")

        if not username:
            error = "Benutzername ist erforderlich."
        elif User.objects.filter(username=username).exists():
            error = "Dieser Benutzername ist bereits vergeben."
        elif email and User.objects.filter(email=email).exists():
            error = "Diese E-Mail-Adresse ist bereits registriert."
        elif password1 != password2:
            error = "Die Passwörter stimmen nicht überein."
        else:
            try:
                validate_password(password1)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                )
                login(request, user)
                next_url = "/dashboard/"
                if plan or modules:
                    from urllib.parse import urlencode

                    params = {k: v for k, v in [("plan", plan), ("modules", modules)] if v}
                    next_url = "/dashboard/?" + urlencode(params)
                return redirect(next_url)
            except ValidationError as e:
                error = " ".join(e.messages)

    return render(
        request,
        "registration/register.html",
        {"error": error, "plan": plan, "modules": modules},
    )


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
