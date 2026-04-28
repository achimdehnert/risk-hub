"""Tenancy views — Organization + User/Membership management."""

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django_tenancy.module_models import ModuleMembership, ModuleSubscription

from tenancy.forms import (
    InviteUserForm,
    MembershipRoleForm,
    ModuleMembershipGrantForm,
    ModuleMembershipRoleForm,
    ModuleSubscriptionForm,
    OrganizationForm,
)
from tenancy.models import Membership, Organization
from tenancy.services import (
    add_module_subscription,
    ensure_role_assignment,
    get_all_organizations,
    get_module_memberships,
    get_module_subscription_stats,
    get_org_member_counts,
    get_org_memberships,
    get_org_module_counts,
    get_org_roles,
    get_org_subscriptions,
    get_organization_by_tenant,
    grant_module_membership,
    invite_user_to_org,
    remove_member_from_org,
    subscription_exists,
)

_ALL_MODULES = ["risk", "dsb", "ex", "substances", "gbu", "documents", "actions", "brandschutz"]


def _require_staff(request: HttpRequest) -> bool:
    return request.user.is_staff or request.user.is_superuser


# -----------------------------------------------------------------------
# Organization CRUD
# -----------------------------------------------------------------------


@login_required
def org_list(request: HttpRequest) -> HttpResponse:
    """List all organizations (staff only)."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    qs = get_all_organizations()
    member_counts = get_org_member_counts()
    module_counts = get_org_module_counts()
    for org in qs:
        org.member_count = member_counts.get(org.tenant_id, 0)
        org.module_count = module_counts.get(org.tenant_id, 0)

    total = qs.count()
    mod_stats = get_module_subscription_stats()
    stats = {
        "total": total,
        "active": qs.filter(status="active").count(),
        "trial": qs.filter(status="trial").count(),
        "suspended": qs.filter(status="suspended").count(),
        **mod_stats,
    }
    return render(request, "tenancy/org_list.html", {"rows": qs, "stats": stats})


@login_required
def org_create(request: HttpRequest) -> HttpResponse:
    """Create a new organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save(commit=False)
            org.status = Organization.Status.ACTIVE
            org.save()
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = OrganizationForm()
    return render(
        request,
        "tenancy/org_form.html",
        {
            "form": form,
            "title": "Neuen Mandanten anlegen",
        },
    )


@login_required
def org_edit(request: HttpRequest, pk) -> HttpResponse:
    """Edit an existing organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = OrganizationForm(instance=org)
    return render(
        request,
        "tenancy/org_form.html",
        {
            "form": form,
            "title": f"Mandant bearbeiten: {org.name}",
            "object": org,
        },
    )


@login_required
def org_detail(request: HttpRequest, pk) -> HttpResponse:
    """Organization detail with members and roles."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=pk)
    memberships = get_org_memberships(org.tenant_id).order_by("role", "user__username")
    roles = get_org_roles(org.tenant_id).order_by("-is_system", "name")
    sites = org.sites.all().order_by("name")
    subscriptions = get_org_subscriptions(org.tenant_id)
    subscribed_modules = {s.module for s in subscriptions}
    missing_modules = [m for m in _ALL_MODULES if m not in subscribed_modules]

    return render(
        request,
        "tenancy/org_detail.html",
        {
            "org": org,
            "memberships": memberships,
            "roles": roles,
            "sites": sites,
            "subscriptions": subscriptions,
            "missing_modules": missing_modules,
        },
    )


@login_required
def org_delete(request: HttpRequest, pk) -> HttpResponse:
    """Delete (soft) an organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=pk)
    if request.method == "POST":
        org.status = Organization.Status.DELETED
        org.deleted_at = timezone.now()
        org.save()
        return redirect("tenancy:org-list")
    return render(
        request,
        "tenancy/org_confirm_delete.html",
        {
            "org": org,
        },
    )


# -----------------------------------------------------------------------
# Member Management
# -----------------------------------------------------------------------


@login_required
def member_invite(request: HttpRequest, org_pk) -> HttpResponse:
    """Invite (create) a new user and add to organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    if request.method == "POST":
        form = InviteUserForm(request.POST)
        if form.is_valid():
            user, _membership = invite_user_to_org(org, form.cleaned_data, invited_by=request.user)
            ensure_role_assignment(user, org, form.cleaned_data["role"])
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = InviteUserForm()
    return render(
        request,
        "tenancy/member_invite.html",
        {
            "form": form,
            "org": org,
            "title": f"Benutzer einladen — {org.name}",
        },
    )


@login_required
def member_role(request: HttpRequest, org_pk, membership_pk) -> HttpResponse:
    """Change a member's role."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    membership = get_object_or_404(
        Membership,
        pk=membership_pk,
        tenant_id=org.tenant_id,
    )
    if request.method == "POST":
        form = MembershipRoleForm(request.POST)
        if form.is_valid():
            membership.role = form.cleaned_data["role"]
            membership.save()
            ensure_role_assignment(membership.user, org, membership.role)
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = MembershipRoleForm(initial={"role": membership.role})
    return render(
        request,
        "tenancy/member_role.html",
        {
            "form": form,
            "org": org,
            "membership": membership,
            "title": f"Rolle ändern — {membership.user.username}",
        },
    )


@login_required
def member_remove(request: HttpRequest, org_pk, membership_pk) -> HttpResponse:
    """Remove a member from the organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    membership = get_object_or_404(
        Membership,
        pk=membership_pk,
        tenant_id=org.tenant_id,
    )
    if request.method == "POST":
        remove_member_from_org(org, membership)
        return redirect("tenancy:org-detail", pk=org.pk)
    return render(
        request,
        "tenancy/member_confirm_remove.html",
        {
            "org": org,
            "membership": membership,
        },
    )


# -----------------------------------------------------------------------
# Module Subscription Management
# -----------------------------------------------------------------------


@login_required
def module_subscription_toggle(
    request: HttpRequest,
    org_pk,
    module: str,
) -> HttpResponse:
    """Activate or suspend a module subscription (POST only)."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)
    if request.method != "POST":
        return redirect("tenancy:org-detail", pk=org_pk)

    org = get_object_or_404(Organization, pk=org_pk)
    sub = get_object_or_404(
        ModuleSubscription,
        tenant_id=org.tenant_id,
        module=module,
    )
    action = request.POST.get("action", "")
    if action == "activate":
        sub.status = ModuleSubscription.Status.ACTIVE
        sub.activated_at = sub.activated_at or timezone.now()
    elif action == "suspend":
        sub.status = ModuleSubscription.Status.SUSPENDED
    sub.save()
    return redirect("tenancy:org-detail", pk=org.pk)


@login_required
def module_subscription_add(
    request: HttpRequest,
    org_pk,
    module: str,
) -> HttpResponse:
    """Add a new module subscription to an organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    if subscription_exists(org.tenant_id, module):
        return redirect("tenancy:org-detail", pk=org.pk)

    add_module_subscription(org, module)
    return redirect("tenancy:org-detail", pk=org.pk)


@login_required
def module_subscription_edit(
    request: HttpRequest,
    org_pk,
    module: str,
) -> HttpResponse:
    """Edit module subscription details (status, plan, dates)."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    sub = get_object_or_404(
        ModuleSubscription,
        tenant_id=org.tenant_id,
        module=module,
    )
    if request.method == "POST":
        form = ModuleSubscriptionForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = ModuleSubscriptionForm(instance=sub)
    return render(
        request,
        "tenancy/module_subscription_edit.html",
        {
            "form": form,
            "org": org,
            "sub": sub,
            "module": module,
        },
    )


# -----------------------------------------------------------------------
# Module Membership Management
# -----------------------------------------------------------------------


@login_required
def module_membership_manage(
    request: HttpRequest,
    org_pk,
    module: str,
) -> HttpResponse:
    """List + grant module memberships for a specific module."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    sub = get_object_or_404(
        ModuleSubscription,
        tenant_id=org.tenant_id,
        module=module,
    )
    memberships = (
        get_module_memberships(org.tenant_id, module)
        .select_related("user", "granted_by")
        .order_by("role", "user__username")
    )
    if request.method == "POST":
        form = ModuleMembershipGrantForm(
            request.POST,
            org=org,
            module=module,
        )
        if form.is_valid():
            grant_module_membership(
                org,
                user=form.cleaned_data["user"],
                module=module,
                role=form.cleaned_data["role"],
                granted_by=request.user,
                expires_at=form.cleaned_data.get("expires_at"),
            )
            return redirect(
                "tenancy:module-membership-manage",
                org_pk=org.pk,
                module=module,
            )
    else:
        form = ModuleMembershipGrantForm(org=org, module=module)

    return render(
        request,
        "tenancy/module_membership_manage.html",
        {
            "org": org,
            "sub": sub,
            "module": module,
            "memberships": memberships,
            "form": form,
        },
    )


@login_required
def module_membership_role(
    request: HttpRequest,
    org_pk,
    module: str,
    membership_pk,
) -> HttpResponse:
    """Change a user's role within a module."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    mm = get_object_or_404(
        ModuleMembership,
        pk=membership_pk,
        tenant_id=org.tenant_id,
        module=module,
    )
    if request.method == "POST":
        form = ModuleMembershipRoleForm(request.POST)
        if form.is_valid():
            mm.role = form.cleaned_data["role"]
            mm.save()
            return redirect(
                "tenancy:module-membership-manage",
                org_pk=org.pk,
                module=module,
            )
    else:
        form = ModuleMembershipRoleForm(initial={"role": mm.role})
    return render(
        request,
        "tenancy/module_membership_role.html",
        {
            "form": form,
            "org": org,
            "mm": mm,
            "module": module,
        },
    )


@login_required
def module_membership_revoke(
    request: HttpRequest,
    org_pk,
    module: str,
    membership_pk,
) -> HttpResponse:
    """Revoke a user's module membership (POST only)."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)
    if request.method != "POST":
        return redirect("tenancy:org-detail", pk=org_pk)

    org = get_object_or_404(Organization, pk=org_pk)
    mm = get_object_or_404(
        ModuleMembership,
        pk=membership_pk,
        tenant_id=org.tenant_id,
        module=module,
    )
    mm.delete()
    return redirect(
        "tenancy:module-membership-manage",
        org_pk=org.pk,
        module=module,
    )


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


# -----------------------------------------------------------------------
# Site CRUD
# -----------------------------------------------------------------------


@login_required
def site_list(request: HttpRequest) -> HttpResponse:
    """List all sites for the current tenant."""
    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return render(request, "403.html", status=403)

    from tenancy.models import Site

    org = get_organization_by_tenant(tenant_id)
    sites = Site.objects.filter(tenant_id=tenant_id).order_by("name")
    return render(
        request,
        "tenancy/site_list.html",
        {
            "sites": sites,
            "org": org,
        },
    )


@login_required
def site_create(request: HttpRequest) -> HttpResponse:
    """Create a new site for the current tenant."""
    from tenancy.forms import SiteForm

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return render(request, "403.html", status=403)

    org = get_organization_by_tenant(tenant_id)

    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save(commit=False)
            site.tenant_id = tenant_id
            site.organization = org
            site.save()
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            return redirect("tenancy:site-list")
    else:
        form = SiteForm()

    return render(
        request,
        "tenancy/site_form.html",
        {
            "form": form,
            "title": "Neuen Standort anlegen",
            "org": org,
        },
    )


@login_required
def site_edit(request: HttpRequest, pk: int) -> HttpResponse:
    """Edit an existing site."""
    from tenancy.forms import SiteForm
    from tenancy.models import Site

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return render(request, "403.html", status=403)

    site = get_object_or_404(Site, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        form = SiteForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            return redirect("tenancy:site-list")
    else:
        form = SiteForm(instance=site)

    return render(
        request,
        "tenancy/site_form.html",
        {
            "form": form,
            "title": f"Standort bearbeiten: {site.name}",
            "site": site,
            "org": get_organization_by_tenant(tenant_id),
        },
    )


@login_required
def site_delete(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a site (POST only)."""
    from tenancy.models import Site

    tenant_id = getattr(request, "tenant_id", None)
    if not tenant_id:
        return render(request, "403.html", status=403)

    site = get_object_or_404(Site, pk=pk, tenant_id=tenant_id)

    if request.method == "POST":
        site.delete()
        return redirect("tenancy:site-list")

    return render(
        request,
        "tenancy/site_confirm_delete.html",
        {"site": site},
    )
