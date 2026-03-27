"""Project admin (ADR-041)."""

from django.contrib import admin

from projects.models import Project, ProjectModule


class ProjectModuleInline(admin.TabularInline):
    model = ProjectModule
    extra = 0
    readonly_fields = ("activated_at",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project_number",
        "client_name",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("name", "project_number", "client_name")
    readonly_fields = ("uuid", "created_at", "updated_at")
    inlines = [ProjectModuleInline]
