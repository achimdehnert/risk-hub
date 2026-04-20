from django.contrib import admin
from django_tenancy.module_models import ModuleMembership, ModuleSubscription

from tenancy.models import Department, Organization, Site


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tenant_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "tenant_id")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "site_type",
        "is_active",
        "tenant_id",
        "organization",
        "created_at",
    )
    list_filter = ("organization", "site_type", "is_active")
    search_fields = ("name", "code")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "organization", "site", "tenant_id")
    list_filter = ("organization", "site")
    search_fields = ("name", "code")


@admin.register(ModuleSubscription)
class ModuleSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "module", "status", "plan_code", "activated_at", "expires_at")
    list_filter = ("module", "status")
    search_fields = ("organization__name", "organization__slug")
    readonly_fields = ("tenant_id", "created_at", "updated_at")
    ordering = ("organization__name", "module")


@admin.register(ModuleMembership)
class ModuleMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "module", "role", "tenant_id", "granted_at", "expires_at")
    list_filter = ("module", "role")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("tenant_id", "granted_at")
    ordering = ("tenant_id", "module", "user__username")
