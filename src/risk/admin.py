from django.contrib import admin

from risk.models import Assessment, Hazard, ProtectiveMeasure, SubstitutionCheck


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


@admin.register(ProtectiveMeasure)
class ProtectiveMeasureAdmin(admin.ModelAdmin):
    list_display = ("description", "measure_type", "status", "assessment", "due_date")
    list_filter = ("measure_type", "status", "effectiveness_result")
    search_fields = ("description", "specification")
    readonly_fields = ("created_at", "updated_at")


@admin.register(SubstitutionCheck)
class SubstitutionCheckAdmin(admin.ModelAdmin):
    list_display = ("current_product", "result", "checked_at", "implementation_deadline")
    list_filter = ("result",)
    search_fields = ("justification",)
    readonly_fields = ("created_at", "updated_at")
