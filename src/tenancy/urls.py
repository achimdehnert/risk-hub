"""URL configuration für Tenancy (Mandantenverwaltung)."""

from django.urls import path

from tenancy import views

app_name = "tenancy"

urlpatterns = [
    # Organization CRUD
    path("", views.org_list, name="org-list"),
    path("new/", views.org_create, name="org-create"),
    path("<uuid:pk>/", views.org_detail, name="org-detail"),
    path("<uuid:pk>/edit/", views.org_edit, name="org-edit"),
    path("<uuid:pk>/delete/", views.org_delete, name="org-delete"),
    # Member management
    path(
        "<uuid:org_pk>/members/invite/",
        views.member_invite,
        name="member-invite",
    ),
    path(
        "<uuid:org_pk>/members/<uuid:membership_pk>/role/",
        views.member_role,
        name="member-role",
    ),
    path(
        "<uuid:org_pk>/members/<uuid:membership_pk>/remove/",
        views.member_remove,
        name="member-remove",
    ),
    # Module Subscription management
    path(
        "<uuid:org_pk>/modules/<str:module>/toggle/",
        views.module_subscription_toggle,
        name="module-subscription-toggle",
    ),
    path(
        "<uuid:org_pk>/modules/<str:module>/add/",
        views.module_subscription_add,
        name="module-subscription-add",
    ),
    path(
        "<uuid:org_pk>/modules/<str:module>/edit/",
        views.module_subscription_edit,
        name="module-subscription-edit",
    ),
    # Module Membership management
    path(
        "<uuid:org_pk>/modules/<str:module>/members/",
        views.module_membership_manage,
        name="module-membership-manage",
    ),
    path(
        "<uuid:org_pk>/modules/<str:module>/members/<uuid:membership_pk>/role/",
        views.module_membership_role,
        name="module-membership-role",
    ),
    path(
        "<uuid:org_pk>/modules/<str:module>/members/<uuid:membership_pk>/revoke/",
        views.module_membership_revoke,
        name="module-membership-revoke",
    ),
]
