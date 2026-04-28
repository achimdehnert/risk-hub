"""URL configuration für Tenancy (Mandantenverwaltung)."""

from django.urls import path

from tenancy import views

app_name = "tenancy"

urlpatterns = [
    # Organization CRUD
    path("", views.org_list, name="org-list"),
    path("new/", views.org_create, name="org-create"),
    path("<int:pk>/", views.org_detail, name="org-detail"),
    path("<int:pk>/edit/", views.org_edit, name="org-edit"),
    path("<int:pk>/delete/", views.org_delete, name="org-delete"),
    # Member management
    path(
        "<int:org_pk>/members/invite/",
        views.member_invite,
        name="member-invite",
    ),
    path(
        "<int:org_pk>/members/<int:membership_pk>/role/",
        views.member_role,
        name="member-role",
    ),
    path(
        "<int:org_pk>/members/<int:membership_pk>/remove/",
        views.member_remove,
        name="member-remove",
    ),
    # Module Subscription management
    path(
        "<int:org_pk>/modules/<str:module>/toggle/",
        views.module_subscription_toggle,
        name="module-subscription-toggle",
    ),
    path(
        "<int:org_pk>/modules/<str:module>/add/",
        views.module_subscription_add,
        name="module-subscription-add",
    ),
    path(
        "<int:org_pk>/modules/<str:module>/edit/",
        views.module_subscription_edit,
        name="module-subscription-edit",
    ),
    # Module Membership management
    path(
        "<int:org_pk>/modules/<str:module>/members/",
        views.module_membership_manage,
        name="module-membership-manage",
    ),
    path(
        "<int:org_pk>/modules/<str:module>/members/<uuid:membership_pk>/role/",
        views.module_membership_role,
        name="module-membership-role",
    ),
    path(
        "<int:org_pk>/modules/<str:module>/members/<uuid:membership_pk>/revoke/",
        views.module_membership_revoke,
        name="module-membership-revoke",
    ),
    # Site management
    path("sites/", views.site_list, name="site-list"),
    path("sites/new/", views.site_create, name="site-create"),
    path("sites/<int:pk>/edit/", views.site_edit, name="site-edit"),
    path("sites/<int:pk>/delete/", views.site_delete, name="site-delete"),
    # Facility management (Produktionsstätten)
    path("sites/<int:site_pk>/facilities/", views.facility_list, name="facility-list"),
    path("sites/<int:site_pk>/facilities/new/", views.facility_create, name="facility-create"),
    path("sites/<int:site_pk>/facilities/<int:pk>/edit/", views.facility_edit, name="facility-edit"),
    path("sites/<int:site_pk>/facilities/<int:pk>/delete/", views.facility_delete, name="facility-delete"),
]
