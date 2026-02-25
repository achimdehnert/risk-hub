from django.contrib import admin
from tenancy.models import Organization, Site
from django_tenancy.module_models import ModuleMembership, ModuleSubscription


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tenant_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "tenant_id")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant_id", "organization", "created_at")
    list_filter = ("organization",)
    search_fields = ("name",)


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
