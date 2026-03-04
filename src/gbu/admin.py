from django.contrib import admin
from django.http import HttpRequest
from django.utils import timezone

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
    actions = ["mark_mandatory", "mark_optional"]

    @admin.action(description="Als Pflichtmaßnahme markieren")
    def mark_mandatory(self, request: HttpRequest, queryset) -> None:
        updated = queryset.update(is_mandatory=True)
        self.message_user(request, f"{updated} Vorlagen als Pflicht markiert.")

    @admin.action(description="Als optionale Maßnahme markieren")
    def mark_optional(self, request: HttpRequest, queryset) -> None:
        updated = queryset.update(is_mandatory=False)
        self.message_user(request, f"{updated} Vorlagen als optional markiert.")


class ActivityMeasureInline(admin.TabularInline):
    model = ActivityMeasure
    extra = 0
    fields = ["tops_type", "title", "is_confirmed", "is_mandatory"]
    readonly_fields = ["tops_type"]


@admin.register(HazardAssessmentActivity)
class HazardAssessmentActivityAdmin(admin.ModelAdmin):
    list_display = [
        "activity_description_short",
        "status",
        "risk_score",
        "tenant_id",
        "site",
        "next_review_date",
        "approved_by_name",
    ]
    list_filter = ["status", "risk_score", "activity_frequency", "quantity_class"]
    search_fields = ["activity_description", "approved_by_name"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "approved_at",
        "approved_by_id",
        "gbu_document",
        "ba_document",
    ]
    date_hierarchy = "next_review_date"
    inlines = [ActivityMeasureInline]
    actions = ["mark_as_review", "mark_as_outdated"]

    def activity_description_short(self, obj) -> str:
        return obj.activity_description[:60]

    activity_description_short.short_description = "Tätigkeit"

    @admin.action(description="Status → In Prüfung setzen")
    def mark_as_review(self, request: HttpRequest, queryset) -> None:
        from gbu.models.activity import ActivityStatus

        updated = queryset.filter(status=ActivityStatus.DRAFT).update(status=ActivityStatus.REVIEW)
        self.message_user(request, f"{updated} Tätigkeiten auf 'review' gesetzt.")

    @admin.action(description="Status → Veraltet markieren (Compliance)")
    def mark_as_outdated(self, request: HttpRequest, queryset) -> None:
        from gbu.models.activity import ActivityStatus

        updated = queryset.filter(status=ActivityStatus.APPROVED).update(
            status=ActivityStatus.OUTDATED,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} Tätigkeiten als veraltet markiert.",
        )


@admin.register(ExposureRiskMatrix)
class ExposureRiskMatrixAdmin(admin.ModelAdmin):
    list_display = [
        "quantity_class",
        "activity_frequency",
        "has_cmr",
        "risk_score",
        "emkg_class",
        "note",
    ]
    list_filter = ["risk_score", "emkg_class", "has_cmr"]
    search_fields = ["note"]
    ordering = ["quantity_class", "activity_frequency", "has_cmr"]
