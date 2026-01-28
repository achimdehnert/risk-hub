from django.contrib import admin
from reporting.models import RetentionPolicy, ExportJob


@admin.register(RetentionPolicy)
class RetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "retention_days", "delete_mode", "tenant_id")
    list_filter = ("delete_mode", "category")


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("export_type", "status", "tenant_id", "requested_by_user_id", "created_at")
    list_filter = ("status", "export_type")
    readonly_fields = ("created_at", "started_at", "finished_at")
