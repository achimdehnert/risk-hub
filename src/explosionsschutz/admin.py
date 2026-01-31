# src/explosionsschutz/admin.py
"""
Django Admin Interface für Explosionsschutz-Modul (v5)

Features:
- TenantAwareAdmin für Multi-Tenancy
- ReadOnlyMixin für System-Daten
- Inline-Modelle für zusammenhängende Daten
- Custom Actions für Workflow
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count

from .models import (
    ReferenceStandard,
    MeasureCatalog,
    SafetyFunction,
    EquipmentType,
    Area,
    ExplosionConcept,
    ZoneDefinition,
    ProtectionMeasure,
    Equipment,
    Inspection,
    VerificationDocument,
    ZoneIgnitionSourceAssessment,
)


# =============================================================================
# MIXINS
# =============================================================================

class TenantAwareAdmin(admin.ModelAdmin):
    """
    Base Admin mit Tenant-Awareness.
    
    - Filtert automatisch nach tenant_id
    - Setzt tenant_id beim Speichern
    """
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        tenant_id = getattr(request.user, "tenant_id", None)
        if tenant_id:
            return qs.filter(tenant_id=tenant_id)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "tenant_id") and not obj.tenant_id:
            obj.tenant_id = getattr(request.user, "tenant_id", None)
        super().save_model(request, obj, form, change)


class ReadOnlyMixin:
    """Verhindert Bearbeitung von System-Daten"""
    
    def has_change_permission(self, request, obj=None):
        if obj and getattr(obj, "is_system", False):
            return False
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        if obj and getattr(obj, "is_system", False):
            return False
        return super().has_delete_permission(request, obj)


# =============================================================================
# STAMMDATEN ADMIN
# =============================================================================

@admin.register(ReferenceStandard)
class ReferenceStandardAdmin(ReadOnlyMixin, TenantAwareAdmin):
    """Admin für Regelwerksreferenzen"""
    
    list_display = [
        "code",
        "title",
        "category",
        "is_system_badge",
        "valid_from",
        "valid_until",
    ]
    list_filter = ["category", "is_system"]
    search_fields = ["code", "title"]
    ordering = ["code"]
    
    fieldsets = [
        (None, {
            "fields": ["code", "title", "category"]
        }),
        ("Details", {
            "fields": ["url", "valid_from", "valid_until"],
            "classes": ["collapse"]
        }),
        ("System", {
            "fields": ["is_system"],
            "classes": ["collapse"]
        }),
    ]
    
    def is_system_badge(self, obj):
        if obj.is_system:
            return format_html(
                '<span style="background:#28a745;color:white;'
                'padding:2px 8px;border-radius:4px">System</span>'
            )
        return format_html(
            '<span style="background:#6c757d;color:white;'
            'padding:2px 8px;border-radius:4px">Tenant</span>'
        )
    is_system_badge.short_description = "Typ"


@admin.register(MeasureCatalog)
class MeasureCatalogAdmin(ReadOnlyMixin, TenantAwareAdmin):
    """Admin für Maßnahmenkatalog"""
    
    list_display = ["code", "title", "default_type", "is_system_badge"]
    list_filter = ["default_type", "is_system"]
    search_fields = ["code", "title"]
    filter_horizontal = ["reference_standards"]
    
    def is_system_badge(self, obj):
        if obj.is_system:
            return format_html(
                '<span style="background:#28a745;color:white;'
                'padding:2px 8px;border-radius:4px">System</span>'
            )
        return "-"
    is_system_badge.short_description = "System"


@admin.register(SafetyFunction)
class SafetyFunctionAdmin(ReadOnlyMixin, TenantAwareAdmin):
    """Admin für MSR-Sicherheitsfunktionen"""
    
    list_display = [
        "name",
        "performance_level",
        "sil_level",
        "monitoring_method",
        "is_system_badge",
    ]
    list_filter = ["performance_level", "sil_level", "monitoring_method", "is_system"]
    search_fields = ["name", "description"]
    filter_horizontal = ["reference_standards"]
    
    def is_system_badge(self, obj):
        if obj.is_system:
            return format_html(
                '<span style="background:#28a745;color:white;'
                'padding:2px 8px;border-radius:4px">System</span>'
            )
        return "-"
    is_system_badge.short_description = "System"


@admin.register(EquipmentType)
class EquipmentTypeAdmin(ReadOnlyMixin, TenantAwareAdmin):
    """Admin für Betriebsmitteltypen mit ATEX-Kennzeichnung"""
    
    list_display = [
        "manufacturer",
        "model",
        "atex_marking_display",
        "epl",
        "ip_rating",
        "is_system_badge",
    ]
    list_filter = [
        "atex_group",
        "atex_category",
        "protection_type",
        "temperature_class",
        "is_system",
    ]
    search_fields = ["manufacturer", "model", "certificate_number"]
    
    fieldsets = [
        ("Hersteller & Modell", {
            "fields": ["manufacturer", "model", "description"]
        }),
        ("ATEX-Kennzeichnung", {
            "fields": [
                "atex_group",
                "atex_category",
                "protection_type",
                "explosion_group",
                "temperature_class",
                "epl",
            ]
        }),
        ("Technische Daten", {
            "fields": [
                "ip_rating",
                ("ambient_temp_min", "ambient_temp_max"),
                "default_inspection_interval_months",
            ],
            "classes": ["collapse"]
        }),
        ("Dokumentation", {
            "fields": ["datasheet_url", "certificate_number", "notified_body"],
            "classes": ["collapse"]
        }),
        ("System", {
            "fields": ["is_system"],
            "classes": ["collapse"]
        }),
    ]
    
    def atex_marking_display(self, obj):
        return format_html(
            '<code style="background:#f8f9fa;padding:2px 6px">{}</code>',
            obj.full_atex_marking
        )
    atex_marking_display.short_description = "ATEX"
    
    def is_system_badge(self, obj):
        if obj.is_system:
            return format_html(
                '<span style="background:#28a745;color:white;'
                'padding:2px 8px;border-radius:4px">System</span>'
            )
        return "-"
    is_system_badge.short_description = "System"


# =============================================================================
# CORE ADMIN
# =============================================================================

@admin.register(Area)
class AreaAdmin(TenantAwareAdmin):
    """Admin für Betriebsbereiche"""
    
    list_display = ["code", "name", "site_id", "has_ex_hazard_badge", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["code", "name"]
    readonly_fields = ["created_at", "updated_at"]
    
    def has_ex_hazard_badge(self, obj):
        if obj.has_explosion_hazard:
            return format_html(
                '<span style="background:#dc3545;color:white;'
                'padding:2px 8px;border-radius:4px">⚠️ Ex-Gefahr</span>'
            )
        return format_html(
            '<span style="background:#28a745;color:white;'
            'padding:2px 8px;border-radius:4px">✓ Kein Ex</span>'
        )
    has_ex_hazard_badge.short_description = "Ex-Status"


class ZoneDefinitionInline(admin.TabularInline):
    """Inline für Zonen im Konzept"""
    model = ZoneDefinition
    extra = 0
    fields = ["zone_type", "name", "reference_standard"]
    readonly_fields = ["zone_type", "name", "reference_standard"]
    show_change_link = True


class ProtectionMeasureInline(admin.TabularInline):
    """Inline für Maßnahmen im Konzept"""
    model = ProtectionMeasure
    extra = 0
    fields = ["category", "title", "status"]
    readonly_fields = ["category", "title", "status"]
    show_change_link = True


class VerificationDocumentInline(admin.TabularInline):
    """Inline für Dokumente im Konzept"""
    model = VerificationDocument
    extra = 0
    fields = ["title", "document_type", "issued_at"]
    readonly_fields = ["title", "document_type", "issued_at"]
    show_change_link = True


@admin.register(ExplosionConcept)
class ExplosionConceptAdmin(TenantAwareAdmin):
    """Admin für Explosionsschutzkonzepte"""
    
    list_display = [
        "title",
        "version",
        "area",
        "substance_name",
        "status_badge",
        "completion_badge",
        "validated_at",
    ]
    list_filter = ["status", "is_validated", "created_at"]
    search_fields = ["title", "area__name", "substance_name"]
    readonly_fields = [
        "version",
        "is_validated",
        "validated_by",
        "validated_at",
        "created_at",
        "updated_at",
        "completion_percentage",
    ]
    inlines = [ZoneDefinitionInline, ProtectionMeasureInline, VerificationDocumentInline]
    
    fieldsets = [
        (None, {
            "fields": ["title", "area", "substance_id", "substance_name", "assessment_id"]
        }),
        ("Status", {
            "fields": ["status", "version", "completion_percentage"]
        }),
        ("Validierung", {
            "fields": ["is_validated", "validated_by", "validated_at"],
            "classes": ["collapse"]
        }),
        ("Audit", {
            "fields": ["created_by", "created_at", "updated_at"],
            "classes": ["collapse"]
        }),
    ]
    
    actions = ["validate_concepts", "archive_concepts"]
    
    def status_badge(self, obj):
        colors = {
            "draft": "#ffc107",
            "in_review": "#17a2b8",
            "approved": "#28a745",
            "archived": "#6c757d",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def completion_badge(self, obj):
        pct = obj.completion_percentage
        if pct >= 100:
            color = "#28a745"
        elif pct >= 50:
            color = "#ffc107"
        else:
            color = "#dc3545"
        return format_html(
            '<div style="background:#e9ecef;border-radius:4px;width:60px">'
            '<div style="background:{};width:{}%;height:20px;border-radius:4px;'
            'text-align:center;color:white;font-size:11px;line-height:20px">'
            '{}%</div></div>',
            color, pct, pct
        )
    completion_badge.short_description = "Fortschritt"
    
    @admin.action(description="Ausgewählte Konzepte validieren")
    def validate_concepts(self, request, queryset):
        from .services import validate_explosion_concept, ValidateExplosionConceptCmd
        count = 0
        for concept in queryset.filter(status="draft"):
            try:
                cmd = ValidateExplosionConceptCmd(concept_id=concept.id)
                validate_explosion_concept(
                    cmd,
                    tenant_id=concept.tenant_id,
                    user_id=request.user.id if request.user else None
                )
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} Konzept(e) validiert.")
    
    @admin.action(description="Ausgewählte Konzepte archivieren")
    def archive_concepts(self, request, queryset):
        from .services import archive_explosion_concept
        count = 0
        for concept in queryset.filter(status="approved"):
            try:
                archive_explosion_concept(
                    concept_id=concept.id,
                    tenant_id=concept.tenant_id,
                    user_id=request.user.id if request.user else None
                )
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} Konzept(e) archiviert.")


class ZoneIgnitionSourceInline(admin.TabularInline):
    """Inline für Zündquellenbewertung"""
    model = ZoneIgnitionSourceAssessment
    extra = 0
    fields = ["ignition_source", "is_present", "is_effective", "mitigation"]
    readonly_fields = ["ignition_source"]


@admin.register(ZoneDefinition)
class ZoneDefinitionAdmin(TenantAwareAdmin):
    """Admin für Zonendefinitionen"""
    
    list_display = [
        "name",
        "zone_type_badge",
        "concept",
        "required_equipment_category",
        "reference_standard",
    ]
    list_filter = ["zone_type", "concept__status"]
    search_fields = ["name", "concept__title"]
    inlines = [ZoneIgnitionSourceInline]
    
    fieldsets = [
        (None, {
            "fields": ["concept", "zone_type", "name"]
        }),
        ("Ausdehnung", {
            "fields": [
                "extent",
                ("extent_horizontal_m", "extent_vertical_m"),
            ],
            "classes": ["collapse"]
        }),
        ("Begründung", {
            "fields": [
                "justification",
                "reference_standard",
                "reference_section",
            ]
        }),
    ]
    
    def zone_type_badge(self, obj):
        colors = {
            "0": "#dc3545",
            "1": "#fd7e14",
            "2": "#ffc107",
            "20": "#dc3545",
            "21": "#fd7e14",
            "22": "#ffc107",
            "non_ex": "#28a745",
        }
        color = colors.get(obj.zone_type, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_zone_type_display()
        )
    zone_type_badge.short_description = "Zone"


@admin.register(ProtectionMeasure)
class ProtectionMeasureAdmin(TenantAwareAdmin):
    """Admin für Schutzmaßnahmen"""
    
    list_display = [
        "title",
        "category_badge",
        "status_badge",
        "concept",
        "due_date",
        "is_safety_device",
    ]
    list_filter = ["category", "status", "concept__status"]
    search_fields = ["title", "description", "concept__title"]
    date_hierarchy = "due_date"
    
    fieldsets = [
        (None, {
            "fields": ["concept", "category", "title", "description"]
        }),
        ("Vorlage & MSR", {
            "fields": ["catalog_reference", "safety_function"],
            "classes": ["collapse"]
        }),
        ("Status", {
            "fields": ["status", "responsible_user", "due_date"]
        }),
        ("Verifizierung", {
            "fields": ["verified_by", "verified_at", "verification_notes"],
            "classes": ["collapse"]
        }),
    ]
    
    def category_badge(self, obj):
        colors = {
            "primary": "#007bff",
            "secondary": "#6610f2",
            "tertiary": "#fd7e14",
            "organizational": "#20c997",
        }
        color = colors.get(obj.category, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_category_display()[:20]
        )
    category_badge.short_description = "Kategorie"
    
    def status_badge(self, obj):
        colors = {
            "open": "#dc3545",
            "in_progress": "#ffc107",
            "done": "#28a745",
            "verified": "#17a2b8",
            "obsolete": "#6c757d",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"


class InspectionInline(admin.TabularInline):
    """Inline für Prüfungen"""
    model = Inspection
    extra = 0
    fields = ["inspection_type", "inspection_date", "result", "inspector_name"]
    readonly_fields = ["inspection_type", "inspection_date", "result", "inspector_name"]
    show_change_link = True


@admin.register(Equipment)
class EquipmentAdmin(TenantAwareAdmin):
    """Admin für Betriebsmittel"""
    
    list_display = [
        "equipment_type",
        "serial_number",
        "asset_number",
        "zone",
        "status_badge",
        "inspection_status_badge",
        "next_inspection_date",
    ]
    list_filter = ["status", "equipment_type__atex_category", "zone__zone_type"]
    search_fields = ["serial_number", "asset_number", "equipment_type__model"]
    date_hierarchy = "next_inspection_date"
    inlines = [InspectionInline]
    
    fieldsets = [
        (None, {
            "fields": ["equipment_type", "area", "zone"]
        }),
        ("Identifikation", {
            "fields": ["serial_number", "asset_number", "location_detail"]
        }),
        ("Status", {
            "fields": ["status", "installation_date"]
        }),
        ("Prüfungen", {
            "fields": [
                "last_inspection_date",
                "next_inspection_date",
                "inspection_interval_months",
            ]
        }),
    ]
    
    def status_badge(self, obj):
        colors = {
            "active": "#28a745",
            "inactive": "#6c757d",
            "maintenance": "#ffc107",
            "decommissioned": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def inspection_status_badge(self, obj):
        if obj.is_inspection_due:
            return format_html(
                '<span style="background:#dc3545;color:white;'
                'padding:2px 8px;border-radius:4px">⚠️ Überfällig</span>'
            )
        if obj.next_inspection_date:
            days = (obj.next_inspection_date - timezone.now().date()).days
            if days <= 30:
                return format_html(
                    '<span style="background:#ffc107;color:black;'
                    'padding:2px 8px;border-radius:4px">⏰ {} Tage</span>',
                    days
                )
        return format_html(
            '<span style="background:#28a745;color:white;'
            'padding:2px 8px;border-radius:4px">✓ OK</span>'
        )
    inspection_status_badge.short_description = "Prüfstatus"


@admin.register(Inspection)
class InspectionAdmin(TenantAwareAdmin):
    """Admin für Prüfungen"""
    
    list_display = [
        "equipment",
        "inspection_type",
        "inspection_date",
        "result_badge",
        "inspector_name",
        "certificate_number",
    ]
    list_filter = ["inspection_type", "result", "inspection_date"]
    search_fields = [
        "equipment__serial_number",
        "equipment__asset_number",
        "inspector_name",
        "certificate_number",
    ]
    date_hierarchy = "inspection_date"
    
    def result_badge(self, obj):
        colors = {
            "passed": "#28a745",
            "passed_notes": "#ffc107",
            "failed": "#dc3545",
            "pending": "#6c757d",
        }
        color = colors.get(obj.result, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;'
            'padding:2px 8px;border-radius:4px">{}</span>',
            color,
            obj.get_result_display()
        )
    result_badge.short_description = "Ergebnis"


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(TenantAwareAdmin):
    """Admin für Nachweisdokumente"""
    
    list_display = [
        "title",
        "document_type",
        "concept",
        "issued_at",
        "valid_until",
        "validity_badge",
    ]
    list_filter = ["document_type", "issued_at"]
    search_fields = ["title", "concept__title", "issued_by"]
    date_hierarchy = "issued_at"
    
    def validity_badge(self, obj):
        if not obj.valid_until:
            return "-"
        if obj.valid_until < timezone.now().date():
            return format_html(
                '<span style="background:#dc3545;color:white;'
                'padding:2px 8px;border-radius:4px">Abgelaufen</span>'
            )
        days = (obj.valid_until - timezone.now().date()).days
        if days <= 30:
            return format_html(
                '<span style="background:#ffc107;color:black;'
                'padding:2px 8px;border-radius:4px">{} Tage</span>',
                days
            )
        return format_html(
            '<span style="background:#28a745;color:white;'
            'padding:2px 8px;border-radius:4px">Gültig</span>'
        )
    validity_badge.short_description = "Gültigkeit"


@admin.register(ZoneIgnitionSourceAssessment)
class ZoneIgnitionSourceAssessmentAdmin(TenantAwareAdmin):
    """Admin für Zündquellenbewertungen"""
    
    list_display = [
        "zone",
        "ignition_source",
        "is_present_badge",
        "is_effective_badge",
        "assessed_by",
        "assessed_at",
    ]
    list_filter = ["ignition_source", "is_present", "is_effective"]
    search_fields = ["zone__name", "mitigation"]
    
    def is_present_badge(self, obj):
        if obj.is_present:
            return format_html(
                '<span style="background:#ffc107;color:black;'
                'padding:2px 8px;border-radius:4px">Vorhanden</span>'
            )
        return format_html(
            '<span style="background:#28a745;color:white;'
            'padding:2px 8px;border-radius:4px">Nein</span>'
        )
    is_present_badge.short_description = "Vorhanden"
    
    def is_effective_badge(self, obj):
        if obj.is_effective:
            return format_html(
                '<span style="background:#dc3545;color:white;'
                'padding:2px 8px;border-radius:4px">⚠️ Wirksam</span>'
            )
        return format_html(
            '<span style="background:#28a745;color:white;'
            'padding:2px 8px;border-radius:4px">Unwirksam</span>'
        )
    is_effective_badge.short_description = "Wirksam"
