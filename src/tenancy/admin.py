from django.contrib import admin
from tenancy.models import Organization, Site


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tenant_id", "created_at")
    search_fields = ("name", "slug", "tenant_id")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant_id", "organization", "created_at")
    list_filter = ("organization",)
    search_fields = ("name",)
