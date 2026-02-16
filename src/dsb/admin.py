"""Admin-Konfiguration für DSB Module."""

from django.contrib import admin

from .models import (
    AuditFinding,
    Breach,
    Category,
    DeletionLog,
    Mandate,
    OrganizationalMeasure,
    PrivacyAudit,
    ProcessingActivity,
    Purpose,
    Recipient,
    RetentionRule,
    SubjectGroup,
    TechnicalMeasure,
    ThirdCountryTransfer,
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
    fields = ["condition", "period", "legal_reference"]


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
        "status",
        "review_date",
        "tenant_id",
    ]
    list_filter = ["status"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["title"]


@admin.register(OrganizationalMeasure)
class OrganizationalMeasureAdmin(admin.ModelAdmin):
    """Admin für organisatorische Maßnahmen."""

    list_display = [
        "title",
        "mandate",
        "status",
        "review_date",
        "tenant_id",
    ]
    list_filter = ["status"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["title"]


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@admin.register(PrivacyAudit)
class PrivacyAuditAdmin(admin.ModelAdmin):
    """Admin für Datenschutz-Audits."""

    list_display = [
        "__str__",
        "mandate",
        "status",
        "scheduled_date",
        "completed_date",
        "tenant_id",
    ]
    list_filter = ["status", "audit_type"]
    search_fields = ["mandate__name"]
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
