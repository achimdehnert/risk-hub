"""
Django Admin für das Explosionsschutz-Modul.
Optimiert für Stammdaten-Pflege und Systemverwaltung.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Area,
    Equipment,
    EquipmentType,
    ExplosionConcept,
    Inspection,
    MeasureCatalog,
    ProtectionMeasure,
    ReferenceStandard,
    SafetyFunction,
    VerificationDocument,
    ZoneDefinition,
    ZoneIgnitionSourceAssessment,
)


# ──────────────────────────────────────────────────────────────────────────────
# Stammdaten (schreibgeschützt für Tenants via is_system)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ReferenceStandard)
class ReferenceStandardAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "category", "issue_date", "is_system", "is_active"]
    list_filter = ["category", "is_system", "is_active"]
    search_fields = ["code", "title"]
    ordering = ["category", "code"]
    readonly_fields = ["id"]

    def get_queryset(self, request):
        return super().get_queryset(request)

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_system and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)


@admin.register(MeasureCatalog)
class MeasureCatalogAdmin(admin.ModelAdmin):
    list_display = ["title", "default_category", "is_system", "is_active"]
    list_filter = ["default_category", "is_system"]
    search_fields = ["title"]


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = [
        "manufacturer", "model_name", "atex_marking", "atex_category",
        "temperature_class", "default_inspection_interval_months", "is_system"
    ]
    list_filter = ["atex_category", "temperature_class", "is_system"]
    search_fields = ["manufacturer", "model_name"]

    @admin.display(description="ATEX")
    def atex_marking(self, obj):
        return obj.atex_marking


@admin.register(SafetyFunction)
class SafetyFunctionAdmin(admin.ModelAdmin):
    list_display = ["name", "performance_level", "sil_level", "test_interval_months"]
    list_filter = ["performance_level", "sil_level"]
    search_fields = ["name"]


# ──────────────────────────────────────────────────────────────────────────────
# Betriebsbereiche
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "has_explosion_hazard_display", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    readonly_fields = ["id", "created_at"]

    @admin.display(description="Ex-Hazard", boolean=True)
    def has_explosion_hazard_display(self, obj):
        return obj.has_explosion_hazard


# ──────────────────────────────────────────────────────────────────────────────
# Konzept
# ──────────────────────────────────────────────────────────────────────────────


class ZoneInline(admin.TabularInline):
    model = ZoneDefinition
    extra = 0
    fields = ["zone_type", "name", "ventilation_type", "justification"]
    show_change_link = True


class MeasureInline(admin.TabularInline):
    model = ProtectionMeasure
    extra = 0
    fields = ["category", "title", "status"]
    show_change_link = True


@admin.register(ExplosionConcept)
class ExplosionConceptAdmin(admin.ModelAdmin):
    list_display = [
        "title", "version", "area", "status_badge", "is_current",
        "approved_at", "next_review_date"
    ]
    list_filter = ["status", "is_current", "atmosphere_type"]
    search_fields = ["title", "area__code", "area__name"]
    readonly_fields = [
        "id", "created_at", "updated_at",
        "approved_by_id", "approved_by_name", "approved_at",  # immutable
    ]
    inlines = [ZoneInline, MeasureInline]
    fieldsets = [
        ("Grunddaten", {"fields": [
            "id", "area", "title", "version", "document_number",
            "substance_id", "atmosphere_type", "status", "is_current",
        ]}),
        ("Verfahrensbeschreibung", {"fields": [
            "process_description", "substitute_check_status", "substitute_check_notes",
            "release_source_type", "release_grade", "release_description",
        ], "classes": ["collapse"]}),
        ("Verantwortlichkeiten", {"fields": [
            "responsible_id", "responsible_name", "author_id", "author_name",
        ], "classes": ["collapse"]}),
        ("Freigabe (unveränderlich nach Approval)", {"fields": [
            "approved_by_id", "approved_by_name", "approved_at", "approval_notes",
            "next_review_date",
        ], "classes": ["collapse"]}),
        ("System", {"fields": ["created_at", "updated_at"], "classes": ["collapse"]}),
    ]

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "draft": "#888",
            "review": "#e69900",
            "approved": "#2e7d32",
            "archived": "#555",
        }
        color = colors.get(obj.status, "#888")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:3px;">{}</span>',
            color,
            obj.get_status_display(),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Zonen & Zündquellen
# ──────────────────────────────────────────────────────────────────────────────


class IgnitionAssessmentInline(admin.TabularInline):
    model = ZoneIgnitionSourceAssessment
    extra = 0
    fields = ["ignition_source", "is_present", "is_effective", "mitigation"]
    readonly_fields = ["ignition_source"]


@admin.register(ZoneDefinition)
class ZoneDefinitionAdmin(admin.ModelAdmin):
    list_display = ["name", "zone_type", "concept", "ventilation_type", "ignition_complete"]
    list_filter = ["zone_type", "ventilation_type"]
    search_fields = ["name", "concept__title"]
    inlines = [IgnitionAssessmentInline]

    @admin.display(description="Zündquellen komplett", boolean=True)
    def ignition_complete(self, obj):
        return obj.ignition_assessment_complete


# ──────────────────────────────────────────────────────────────────────────────
# Equipment & Inspections
# ──────────────────────────────────────────────────────────────────────────────


class InspectionInline(admin.TabularInline):
    model = Inspection
    extra = 0
    fields = ["inspection_type", "scheduled_date", "performed_date", "result"]
    show_change_link = True


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        "name", "inventory_number", "area", "atex_marking",
        "next_inspection_date", "inspection_status_badge"
    ]
    list_filter = ["is_active", "area"]
    search_fields = ["name", "inventory_number", "serial_number"]
    inlines = [InspectionInline]

    @admin.display(description="ATEX")
    def atex_marking(self, obj):
        return obj.atex_marking

    @admin.display(description="Prüfstatus")
    def inspection_status_badge(self, obj):
        status = obj.inspection_status
        colors = {
            "current": "#2e7d32",
            "due_soon": "#e69900",
            "overdue": "#c62828",
            "not_required": "#888",
        }
        color = colors.get(status.value, "#888")
        return format_html(
            '<span style="background:{};color:white;padding:2px 6px;border-radius:3px;">{}</span>',
            color,
            status.label if hasattr(status, "label") else status.value,
        )


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = [
        "equipment", "inspection_type", "scheduled_date",
        "performed_date", "result", "external_inspector"
    ]
    list_filter = ["inspection_type", "result"]
    search_fields = ["equipment__name", "external_inspector"]
    readonly_fields = ["id", "created_at"]
