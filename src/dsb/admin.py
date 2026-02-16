"""Admin-Konfiguration für DSB Module."""

from django.contrib import admin

from .models import (
    AuditFinding,
    Breach,
    Category,
    DataProcessingAgreement,
    DeletionLog,
    Mandate,
    OrganizationalMeasure,
    PrivacyAudit,
    ProcessingActivity,
    Purpose,
    Recipient,
    RetentionRule,
    StandardRetentionPeriod,
    SubjectGroup,
    TechnicalMeasure,
    ThirdCountryTransfer,
    TomCategory,
)


# ---------------------------------------------------------------------------
# Inlines
# ---------------------------------------------------------------------------


class ThirdCountryTransferInline(admin.TabularInline):
    """Inline für Drittlandübermittlungen."""

    model = ThirdCountryTransfer
    extra = 0
    fields = ["country", "recipient_entity", "safeguard", "notes"]


class RetentionRuleInline(admin.TabularInline):
    """Inline für Löschfristen."""

    model = RetentionRule
    extra = 0
    fields = ["standard_period", "condition", "period", "legal_reference"]


class AuditFindingInline(admin.TabularInline):
    """Inline für Audit-Befunde."""

    model = AuditFinding
    extra = 0
    fields = ["title", "severity", "status"]
    show_change_link = True


# ---------------------------------------------------------------------------
# Mandate
# ---------------------------------------------------------------------------


@admin.register(Mandate)
class MandateAdmin(admin.ModelAdmin):
    """Admin für betreute Unternehmen."""

    list_display = [
        "name",
        "industry",
        "status",
        "dsb_appointed_date",
        "tenant_id",
    ]
    list_filter = ["status", "industry"]
    search_fields = ["name", "supervisory_authority"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["name"]


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin für Datenkategorien."""

    list_display = ["key", "label", "is_special_category"]
    list_filter = ["is_special_category"]
    search_fields = ["key", "label"]
    ordering = ["key"]


@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    """Admin für Betroffenengruppen."""

    list_display = ["key", "label"]
    search_fields = ["key", "label"]
    ordering = ["key"]


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    """Admin für Empfängerkategorien."""

    list_display = ["key", "label"]
    search_fields = ["key", "label"]
    ordering = ["key"]


@admin.register(Purpose)
class PurposeAdmin(admin.ModelAdmin):
    """Admin für Verarbeitungszwecke."""

    list_display = ["key", "label"]
    search_fields = ["key", "label"]
    ordering = ["key"]


@admin.register(TomCategory)
class TomCategoryAdmin(admin.ModelAdmin):
    """Admin für TOM-Katalog (Stammdaten)."""

    list_display = ["key", "label", "measure_type"]
    list_filter = ["measure_type"]
    search_fields = ["key", "label"]
    ordering = ["measure_type", "key"]


@admin.register(StandardRetentionPeriod)
class StandardRetentionPeriodAdmin(admin.ModelAdmin):
    """Admin für Löschfristen-Stammdaten."""

    list_display = ["key", "label", "legal_reference", "period"]
    search_fields = ["key", "label", "legal_reference"]
    ordering = ["key"]


# ---------------------------------------------------------------------------
# VVT
# ---------------------------------------------------------------------------


@admin.register(ProcessingActivity)
class ProcessingActivityAdmin(admin.ModelAdmin):
    """Admin für Verarbeitungstätigkeiten (VVT)."""

    list_display = [
        "__str__",
        "mandate",
        "legal_basis",
        "risk_level",
        "dsfa_required",
        "tenant_id",
    ]
    list_filter = ["legal_basis", "risk_level", "dsfa_required"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["mandate", "number"]
    inlines = [ThirdCountryTransferInline, RetentionRuleInline]
    filter_horizontal = [
        "purposes",
        "data_categories",
        "data_subjects",
        "recipients",
        "technical_measures",
        "organizational_measures",
    ]
    fieldsets = (
        (
            "Stammdaten",
            {
                "fields": (
                    "mandate",
                    "number",
                    "name",
                    "description",
                    "legal_basis",
                    "tenant_id",
                ),
            },
        ),
        (
            "Zwecke & Datenkategorien",
            {
                "fields": (
                    "purposes",
                    "data_categories",
                    "data_subjects",
                    "recipients",
                ),
            },
        ),
        (
            "TOM-Zuordnung",
            {
                "fields": (
                    "technical_measures",
                    "organizational_measures",
                ),
            },
        ),
        (
            "Risiko",
            {
                "fields": (
                    "risk_level",
                    "dsfa_required",
                ),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_by_id",
                    "updated_by_id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# TOM
# ---------------------------------------------------------------------------


@admin.register(TechnicalMeasure)
class TechnicalMeasureAdmin(admin.ModelAdmin):
    """Admin für technische Maßnahmen."""

    list_display = [
        "title",
        "mandate",
        "category",
        "status",
        "review_date",
        "tenant_id",
    ]
    list_filter = ["status", "category"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["title"]


@admin.register(OrganizationalMeasure)
class OrganizationalMeasureAdmin(admin.ModelAdmin):
    """Admin für organisatorische Maßnahmen."""

    list_display = [
        "title",
        "mandate",
        "category",
        "status",
        "review_date",
        "tenant_id",
    ]
    list_filter = ["status", "category"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["title"]


# ---------------------------------------------------------------------------
# AVV
# ---------------------------------------------------------------------------


@admin.register(DataProcessingAgreement)
class DataProcessingAgreementAdmin(admin.ModelAdmin):
    """Admin für Auftragsverarbeitungsverträge."""

    list_display = [
        "partner_name",
        "mandate",
        "partner_role",
        "status",
        "effective_date",
        "expiry_date",
        "tenant_id",
    ]
    list_filter = ["status", "partner_role"]
    search_fields = ["partner_name", "subject_matter"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["partner_name"]
    filter_horizontal = [
        "data_categories",
        "data_subjects",
        "processing_activities",
        "technical_measures",
        "organizational_measures",
    ]
    fieldsets = (
        (
            "Vertragspartner",
            {
                "fields": (
                    "mandate",
                    "partner_name",
                    "partner_role",
                    "subject_matter",
                    "status",
                    "tenant_id",
                ),
            },
        ),
        (
            "Laufzeit",
            {
                "fields": (
                    "effective_date",
                    "expiry_date",
                ),
            },
        ),
        (
            "Datenschutz-Details",
            {
                "fields": (
                    "data_categories",
                    "data_subjects",
                    "processing_activities",
                ),
            },
        ),
        (
            "TOM & Unterauftragsverarbeitung",
            {
                "fields": (
                    "technical_measures",
                    "organizational_measures",
                    "subprocessors_allowed",
                    "subprocessors_notes",
                ),
            },
        ),
        (
            "Dokument & Notizen",
            {
                "fields": (
                    "document_id",
                    "notes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_by_id",
                    "updated_by_id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@admin.register(PrivacyAudit)
class PrivacyAuditAdmin(admin.ModelAdmin):
    """Admin für Datenschutz-Audits."""

    list_display = [
        "title",
        "mandate",
        "audit_type",
        "status",
        "scheduled_date",
        "completed_date",
        "tenant_id",
    ]
    list_filter = ["status", "audit_type"]
    search_fields = ["title", "mandate__name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-scheduled_date"]
    inlines = [AuditFindingInline]


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    """Admin für Audit-Befunde."""

    list_display = [
        "title",
        "audit",
        "severity",
        "status",
        "tenant_id",
    ]
    list_filter = ["severity", "status"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


@admin.register(DeletionLog)
class DeletionLogAdmin(admin.ModelAdmin):
    """Admin für Löschprotokolle."""

    list_display = [
        "__str__",
        "mandate",
        "processing_activity",
        "requested_at",
        "executed_at",
        "tenant_id",
    ]
    list_filter = ["mandate"]
    search_fields = ["method"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-requested_at"]


# ---------------------------------------------------------------------------
# Breach
# ---------------------------------------------------------------------------


@admin.register(Breach)
class BreachAdmin(admin.ModelAdmin):
    """Admin für Datenpannen."""

    list_display = [
        "__str__",
        "mandate",
        "severity",
        "discovered_at",
        "reported_to_authority_at",
        "is_overdue",
        "tenant_id",
    ]
    list_filter = ["severity"]
    search_fields = ["root_cause", "measures_taken"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "deadline_72h",
        "is_overdue",
    ]
    ordering = ["-discovered_at"]
    filter_horizontal = ["affected_categories"]

    @admin.display(boolean=True, description="Überfällig?")
    def is_overdue(self, obj: Breach) -> bool:
        """Zeigt ob 72h-Frist überschritten."""
        return obj.is_overdue
