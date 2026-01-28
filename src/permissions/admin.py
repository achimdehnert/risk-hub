from django.contrib import admin
from permissions.models import Permission, Role, Scope, Assignment


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description", "created_at")
    search_fields = ("code", "description")


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant_id", "is_system", "created_at")
    list_filter = ("is_system",)


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    list_display = ("scope_type", "tenant_id", "site_id", "asset_id")
    list_filter = ("scope_type",)


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("user_id", "role", "scope", "tenant_id", "created_at")
    list_filter = ("role",)
