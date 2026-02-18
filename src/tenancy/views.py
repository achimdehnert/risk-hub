"""Tenancy views — Organization + User/Membership management."""

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from identity.models import User
from permissions.models import Assignment, Role, Scope
from tenancy.forms import (
    InviteUserForm,
    MembershipRoleForm,
    OrganizationForm,
)
from tenancy.models import Membership, Organization


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

    qs = Organization.objects.all().order_by("name")
    member_counts = dict(
        Membership.objects.values_list("tenant_id")
        .annotate(cnt=Count("id"))
        .values_list("tenant_id", "cnt")
    )
    for org in qs:
        org.member_count = member_counts.get(org.tenant_id, 0)
    return render(request, "tenancy/org_list.html", {"rows": qs})


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
    return render(request, "tenancy/org_form.html", {
        "form": form,
        "title": "Neuen Mandanten anlegen",
    })


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
    return render(request, "tenancy/org_form.html", {
        "form": form,
        "title": f"Mandant bearbeiten: {org.name}",
        "object": org,
    })


@login_required
def org_detail(request: HttpRequest, pk) -> HttpResponse:
    """Organization detail with members and roles."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=pk)
    memberships = (
        Membership.objects.filter(tenant_id=org.tenant_id)
        .select_related("user")
        .order_by("role", "user__username")
    )
    roles = Role.objects.filter(
        tenant_id__in=[org.tenant_id, None],
    ).order_by("-is_system", "name")
    sites = org.sites.all().order_by("name")

    return render(request, "tenancy/org_detail.html", {
        "org": org,
        "memberships": memberships,
        "roles": roles,
        "sites": sites,
    })


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
    return render(request, "tenancy/org_confirm_delete.html", {
        "org": org,
    })


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
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name", ""),
                last_name=form.cleaned_data.get("last_name", ""),
                tenant_id=org.tenant_id,
            )
            Membership.objects.create(
                tenant_id=org.tenant_id,
                user=user,
                role=form.cleaned_data["role"],
                invited_by=request.user,
                invited_at=timezone.now(),
                accepted_at=timezone.now(),
            )
            _ensure_role_assignment(
                user, org, form.cleaned_data["role"],
            )
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = InviteUserForm()
    return render(request, "tenancy/member_invite.html", {
        "form": form,
        "org": org,
        "title": f"Benutzer einladen — {org.name}",
    })


@login_required
def member_role(request: HttpRequest, org_pk, membership_pk) -> HttpResponse:
    """Change a member's role."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    membership = get_object_or_404(
        Membership, pk=membership_pk, tenant_id=org.tenant_id,
    )
    if request.method == "POST":
        form = MembershipRoleForm(request.POST)
        if form.is_valid():
            membership.role = form.cleaned_data["role"]
            membership.save()
            _ensure_role_assignment(
                membership.user, org, membership.role,
            )
            return redirect("tenancy:org-detail", pk=org.pk)
    else:
        form = MembershipRoleForm(initial={"role": membership.role})
    return render(request, "tenancy/member_role.html", {
        "form": form,
        "org": org,
        "membership": membership,
        "title": f"Rolle ändern — {membership.user.username}",
    })


@login_required
def member_remove(request: HttpRequest, org_pk, membership_pk) -> HttpResponse:
    """Remove a member from the organization."""
    if not _require_staff(request):
        return render(request, "403.html", status=403)

    org = get_object_or_404(Organization, pk=org_pk)
    membership = get_object_or_404(
        Membership, pk=membership_pk, tenant_id=org.tenant_id,
    )
    if request.method == "POST":
        Assignment.objects.filter(
            tenant_id=org.tenant_id,
            user_id=membership.user_id,
        ).delete()
        membership.delete()
        return redirect("tenancy:org-detail", pk=org.pk)
    return render(request, "tenancy/member_confirm_remove.html", {
        "org": org,
        "membership": membership,
    })


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _ensure_role_assignment(
    user: User, org: Organization, membership_role: str,
) -> None:
    """Map membership role to permissions.Role assignment."""
    role_map = {
        Membership.Role.OWNER: "admin",
        Membership.Role.ADMIN: "admin",
        Membership.Role.MEMBER: "member",
        Membership.Role.VIEWER: "viewer",
        Membership.Role.EXTERNAL: "viewer",
    }
    system_role_name = role_map.get(membership_role, "viewer")
    role = Role.objects.filter(
        name=system_role_name, is_system=True,
    ).first()
    if not role:
        return

    Assignment.objects.filter(
        tenant_id=org.tenant_id,
        user_id=user.pk,
    ).delete()

    scope, _ = Scope.objects.get_or_create(
        tenant_id=org.tenant_id,
        scope_type=Scope.SCOPE_TENANT,
    )
    Assignment.objects.create(
        tenant_id=org.tenant_id,
        user_id=user.pk,
        role=role,
        scope=scope,
        created_by_user_id=user.pk,
    )
