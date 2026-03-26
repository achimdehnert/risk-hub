# src/global_sds/admin.py
"""Admin-Registrierung für Global SDS Library (ADR-012)."""

from django.contrib import admin

from global_sds.models import (
    GlobalSdsComponent,
    GlobalSdsExposureLimit,
    GlobalSdsRevision,
    GlobalSubstance,
    SdsRevisionDiffRecord,
)
from global_sds.sds_usage import SdsUsage


# ─────────────────────────────────────────────────────────────────────
# Inlines
# ─────────────────────────────────────────────────────────────────────


class GlobalSdsComponentInline(admin.TabularInline):
    model = GlobalSdsComponent
    extra = 0
    fields = (
        "chemical_name", "cas_number", "concentration_min",
        "concentration_max",
    )


class GlobalSdsExposureLimitInline(admin.TabularInline):
    model = GlobalSdsExposureLimit
    extra = 0
    fields = (
        "component", "limit_type", "route",
        "value", "unit", "basis",
    )


# ─────────────────────────────────────────────────────────────────────
# ModelAdmins
# ─────────────────────────────────────────────────────────────────────


@admin.register(GlobalSubstance)
class GlobalSubstanceAdmin(admin.ModelAdmin):
    list_display = ("name", "cas_number", "ec_number", "created_at")
    search_fields = ("name", "cas_number", "ec_number")
    list_filter = ("created_at",)
    readonly_fields = ("uuid", "created_at")


@admin.register(GlobalSdsRevision)
class GlobalSdsRevisionAdmin(admin.ModelAdmin):
    list_display = (
        "product_name", "substance", "status",
        "version_number", "revision_date",
        "parse_confidence", "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = (
        "product_name", "manufacturer_name",
        "substance__name", "substance__cas_number",
    )
    readonly_fields = (
        "uuid", "source_hash", "created_at", "updated_at",
    )
    inlines = [
        GlobalSdsComponentInline,
        GlobalSdsExposureLimitInline,
    ]
    raw_id_fields = ("substance", "superseded_by")


@admin.register(SdsRevisionDiffRecord)
class SdsRevisionDiffRecordAdmin(admin.ModelAdmin):
    list_display = (
        "old_revision", "new_revision",
        "overall_impact", "computed_at",
    )
    list_filter = ("overall_impact",)
    readonly_fields = (
        "old_revision", "new_revision", "overall_impact",
        "field_diffs", "added_h_codes", "removed_h_codes",
        "changed_components", "computed_at",
    )


@admin.register(SdsUsage)
class SdsUsageAdmin(admin.ModelAdmin):
    list_display = (
        "sds_revision", "tenant_id", "status",
        "approved_by", "review_deadline",
    )
    list_filter = ("status",)
    search_fields = (
        "sds_revision__product_name",
        "sds_revision__substance__name",
    )
    raw_id_fields = (
        "sds_revision", "pending_update_revision",
        "approved_by", "update_deferred_by",
    )
