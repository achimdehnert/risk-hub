# src/substances/admin.py
"""Admin-Konfiguration für Substances Module."""

from django.contrib import admin
from .models import (
    Party,
    Substance,
    Identifier,
    SdsRevision,
    SiteInventoryItem,
    HazardStatementRef,
    PrecautionaryStatementRef,
    PictogramRef,
)


class IdentifierInline(admin.TabularInline):
    """Inline für Stoffkennungen."""
    model = Identifier
    extra = 1
    fields = ["id_type", "id_value"]


class SdsRevisionInline(admin.TabularInline):
    """Inline für SDS-Revisionen."""
    model = SdsRevision
    extra = 0
    fields = ["revision_number", "revision_date", "status", "signal_word"]
    readonly_fields = ["revision_number"]
    show_change_link = True


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    """Admin für Hersteller/Lieferanten."""
    list_display = ["name", "party_type", "email", "phone", "tenant_id"]
    list_filter = ["party_type", "tenant_id"]
    search_fields = ["name", "email"]
    ordering = ["name"]


@admin.register(Substance)
class SubstanceAdmin(admin.ModelAdmin):
    """Admin für Gefahrstoffe."""
    list_display = [
        "name",
        "cas_number_display",
        "storage_class",
        "is_cmr",
        "status",
        "manufacturer",
        "tenant_id",
    ]
    list_filter = ["status", "storage_class", "is_cmr", "tenant_id"]
    search_fields = ["name", "trade_name", "description"]
    ordering = ["name"]
    inlines = [IdentifierInline, SdsRevisionInline]
    
    fieldsets = (
        ("Stammdaten", {
            "fields": ("name", "trade_name", "description", "status")
        }),
        ("Klassifikation", {
            "fields": ("storage_class", "is_cmr")
        }),
        ("Parteien", {
            "fields": ("manufacturer", "supplier")
        }),
        ("Ex-Schutz-Daten", {
            "fields": (
                "flash_point_c",
                "ignition_temperature_c",
                ("lower_explosion_limit", "upper_explosion_limit"),
                "temperature_class",
                "explosion_group",
                "vapor_density",
            ),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="CAS-Nr.")
    def cas_number_display(self, obj):
        return obj.cas_number or "-"


@admin.register(SdsRevision)
class SdsRevisionAdmin(admin.ModelAdmin):
    """Admin für SDS-Revisionen."""
    list_display = [
        "substance",
        "revision_number",
        "revision_date",
        "status",
        "signal_word",
        "approved_at",
    ]
    list_filter = ["status", "signal_word", "tenant_id"]
    search_fields = ["substance__name"]
    ordering = ["-revision_date", "-revision_number"]
    filter_horizontal = [
        "hazard_statements",
        "precautionary_statements",
        "pictograms",
    ]
    readonly_fields = ["approved_by", "approved_at"]
    
    fieldsets = (
        ("Stoff", {
            "fields": ("substance",)
        }),
        ("Version", {
            "fields": ("revision_number", "revision_date", "document")
        }),
        ("Klassifikation", {
            "fields": ("status", "signal_word")
        }),
        ("H-/P-Sätze & Piktogramme", {
            "fields": (
                "hazard_statements",
                "precautionary_statements",
                "pictograms",
            )
        }),
        ("Freigabe", {
            "fields": ("approved_by", "approved_at", "notes"),
            "classes": ("collapse",),
        }),
    )


@admin.register(SiteInventoryItem)
class SiteInventoryItemAdmin(admin.ModelAdmin):
    """Admin für Standort-Inventar."""
    list_display = [
        "substance",
        "site",
        "quantity",
        "unit",
        "state",
        "storage_location",
    ]
    list_filter = ["state", "site", "tenant_id"]
    search_fields = ["substance__name", "storage_location"]
    ordering = ["substance__name"]


@admin.register(HazardStatementRef)
class HazardStatementRefAdmin(admin.ModelAdmin):
    """Admin für H-Sätze Referenz."""
    list_display = ["code", "text_de_short", "category"]
    list_filter = ["category"]
    search_fields = ["code", "text_de", "text_en"]
    ordering = ["code"]

    @admin.display(description="Text (DE)")
    def text_de_short(self, obj):
        return obj.text_de[:80] + "..." if len(obj.text_de) > 80 else obj.text_de


@admin.register(PrecautionaryStatementRef)
class PrecautionaryStatementRefAdmin(admin.ModelAdmin):
    """Admin für P-Sätze Referenz."""
    list_display = ["code", "text_de_short", "category"]
    list_filter = ["category"]
    search_fields = ["code", "text_de", "text_en"]
    ordering = ["code"]

    @admin.display(description="Text (DE)")
    def text_de_short(self, obj):
        return obj.text_de[:80] + "..." if len(obj.text_de) > 80 else obj.text_de


@admin.register(PictogramRef)
class PictogramRefAdmin(admin.ModelAdmin):
    """Admin für Piktogramme Referenz."""
    list_display = ["code", "name_de", "name_en"]
    search_fields = ["code", "name_de", "name_en"]
    ordering = ["code"]
