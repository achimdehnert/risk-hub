from django.contrib import admin

from gbu.models.activity import ActivityMeasure, HazardAssessmentActivity
from gbu.models.reference import (
    ExposureRiskMatrix,
    HazardCategoryRef,
    HCodeCategoryMapping,
    MeasureTemplate,
)


@admin.register(HazardCategoryRef)
class HazardCategoryRefAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category_type", "trgs_reference", "sort_order"]
    list_filter = ["category_type"]
    search_fields = ["code", "name", "trgs_reference"]
    ordering = ["category_type", "sort_order"]


@admin.register(HCodeCategoryMapping)
class HCodeCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ["h_code", "category", "annotation"]
    list_filter = ["category__category_type"]
    search_fields = ["h_code", "annotation"]
    autocomplete_fields = ["category"]
    ordering = ["h_code"]


@admin.register(MeasureTemplate)
class MeasureTemplateAdmin(admin.ModelAdmin):
    list_display = ["title", "tops_type", "category", "is_mandatory", "sort_order"]
    list_filter = ["tops_type", "is_mandatory", "category__category_type"]
    search_fields = ["title", "description", "legal_basis"]
    ordering = ["tops_type", "sort_order"]


class ActivityMeasureInline(admin.TabularInline):
    model = ActivityMeasure
    extra = 0
    fields = ["tops_type", "title", "is_confirmed", "is_mandatory"]


@admin.register(HazardAssessmentActivity)
class HazardAssessmentActivityAdmin(admin.ModelAdmin):
    list_display = [
        "activity_description_short",
        "status",
        "risk_score",
        "tenant_id",
        "site",
        "next_review_date",
    ]
    list_filter = ["status", "risk_score", "activity_frequency"]
    search_fields = ["activity_description"]
    readonly_fields = [
        "id", "created_at", "updated_at", "approved_at", "approved_by_id",
    ]
    inlines = [ActivityMeasureInline]

    def activity_description_short(self, obj):
        return obj.activity_description[:60]

    activity_description_short.short_description = "Tätigkeit"


@admin.register(ExposureRiskMatrix)
class ExposureRiskMatrixAdmin(admin.ModelAdmin):
    list_display = [
        "quantity_class",
        "activity_frequency",
        "has_cmr",
        "risk_score",
        "emkg_class",
    ]
    list_filter = ["risk_score", "emkg_class", "has_cmr"]
    ordering = ["quantity_class", "activity_frequency", "has_cmr"]
