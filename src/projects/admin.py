"""Project admin (ADR-041)."""

from django.contrib import admin

from projects.models import (
    DocumentSection,
    OutputDocument,
    Project,
    ProjectDocument,
    ProjectModule,
)


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


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "doc_type", "project", "created_at")
    list_filter = ("doc_type",)
    search_fields = ("title",)


class DocumentSectionInline(admin.TabularInline):
    model = DocumentSection
    extra = 0
    ordering = ("order",)


@admin.register(OutputDocument)
class OutputDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "status", "project", "version")
    list_filter = ("kind", "status")
    search_fields = ("title",)
    inlines = [DocumentSectionInline]
