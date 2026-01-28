from django.contrib import admin
from risk.models import Assessment, Hazard


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "tenant_id", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at", "approved_at")


@admin.register(Hazard)
class HazardAdmin(admin.ModelAdmin):
    list_display = ("title", "assessment", "severity", "probability", "risk_score")
    list_filter = ("severity", "probability")
    search_fields = ("title", "description")
