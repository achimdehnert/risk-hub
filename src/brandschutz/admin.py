"""Brandschutz Django Admin."""

from django.contrib import admin

from .models import (
    EscapeRoute,
    FireExtinguisher,
    FireProtectionConcept,
    FireProtectionMeasure,
    FireSection,
)


class FireSectionInline(admin.TabularInline):
    model = FireSection
    extra = 0
    fields = (
        "name",
        "floor",
        "area_sqm",
        "construction_class",
        "has_sprinkler",
        "has_smoke_detector",
    )


class FireProtectionMeasureInline(admin.TabularInline):
    model = FireProtectionMeasure
    extra = 0
    fields = ("category", "title", "status", "responsible_user_id", "due_date")


@admin.register(FireProtectionConcept)
class FireProtectionConceptAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "concept_type", "status", "valid_until", "created_at")
    list_filter = ("status", "concept_type")
    search_fields = ("title", "site__name")
    inlines = [FireSectionInline, FireProtectionMeasureInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(FireSection)
class FireSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "concept", "floor", "area_sqm", "has_sprinkler", "has_smoke_detector")
    list_filter = ("construction_class",)
    search_fields = ("name", "concept__title")


@admin.register(EscapeRoute)
class EscapeRouteAdmin(admin.ModelAdmin):
    list_display = (
        "section",
        "route_type",
        "status",
        "width_m",
        "is_signposted",
        "last_inspection_date",
    )
    list_filter = ("status", "route_type")
    search_fields = ("description",)


@admin.register(FireExtinguisher)
class FireExtinguisherAdmin(admin.ModelAdmin):
    list_display = (
        "section",
        "extinguisher_type",
        "capacity_kg",
        "status",
        "next_inspection_date",
        "location_description",
    )
    list_filter = ("status", "extinguisher_type")
    search_fields = ("serial_number", "location_description")


@admin.register(FireProtectionMeasure)
class FireProtectionMeasureAdmin(admin.ModelAdmin):
    list_display = ("title", "concept", "category", "status", "due_date")
    list_filter = ("status", "category")
    search_fields = ("title", "description")
