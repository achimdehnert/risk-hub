"""
Tätigkeitsbezogene GBU-Daten (tenant-gebunden).

HazardAssessmentActivity — Kern-Entity (GBU-Tätigkeit), erbt TenantScopedModel
ActivityMeasure           — Konkrete Schutzmaßnahme, tenant_id denormalisiert
"""
import uuid
from enum import StrEnum

from django.db import models

from gbu.models.reference import HazardCategoryRef, MeasureTemplate, TOPSType
from substances.models import TenantScopedModel


class ActivityFrequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    OCCASIONAL = "occasional"
    RARE = "rare"


class QuantityClass(StrEnum):
    XS = "xs"
    S = "s"
    M = "m"
    L = "l"


class RiskScore(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActivityStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    OUTDATED = "outdated"


class HazardAssessmentActivity(TenantScopedModel):
    """
    GBU-Tätigkeit mit Gefahrstoff — Kern-Entity von Modul 2.

    Erbt von TenantScopedModel: id (UUID PK), tenant_id, created_at, updated_at, created_by.

    Compliance:
    - kein DELETE-Permission (default_permissions)
    - SdsRevision: PROTECT (verhindert Löschen wenn GBU referenziert)
    - approved_by_id: UUIDField (unveränderlich nach Freigabe, kein FK SET_NULL)
    """

    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.PROTECT,
        related_name="gbu_activities",
    )
    sds_revision = models.ForeignKey(
        "substances.SdsRevision",
        on_delete=models.PROTECT,
        related_name="gbu_activities",
    )
    activity_description = models.TextField(
        help_text="Tätigkeitsbeschreibung (was wird gemacht, womit, wie lange)",
    )
    activity_frequency = models.CharField(
        max_length=15,
        choices=[(f.value, f.name.title()) for f in ActivityFrequency],
    )
    duration_minutes = models.PositiveSmallIntegerField(
        help_text="Expositionsdauer in Minuten pro Vorgang",
    )
    quantity_class = models.CharField(
        max_length=2,
        choices=[(q.value, q.name) for q in QuantityClass],
        help_text="Mengenkategorie nach EMKG",
    )
    substitution_checked = models.BooleanField(
        default=False,
        help_text="Substitutionsprüfung nach §7 GefStoffV durchgeführt",
    )
    substitution_notes = models.TextField(blank=True, default="")
    derived_hazard_categories = models.ManyToManyField(
        HazardCategoryRef,
        blank=True,
        related_name="activities",
        help_text="Auto-abgeleitete Gefährdungskategorien (via H-Code-Mapping)",
    )
    risk_score = models.CharField(
        max_length=10,
        choices=[(r.value, r.name.title()) for r in RiskScore],
        blank=True,
        default="",
        help_text="EMKG-Risikostufe (berechnet)",
    )
    status = models.CharField(
        max_length=10,
        choices=[(s.value, s.name.title()) for s in ActivityStatus],
        default=ActivityStatus.DRAFT,
        db_index=True,
    )
    approved_by_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID der freigebenden Person (unveränderlich nach Freigabe)",
    )
    approved_by_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Vollname der freigebenden Person (Snapshot, immutable nach Freigabe)",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Nächste Überprüfung (GefStoffV §6)",
    )
    gbu_document = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Generiertes GBU-PDF",
    )
    ba_document = models.ForeignKey(
        "documents.DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Generierte Betriebsanweisung (TRGS 555)",
    )

    class Meta(TenantScopedModel.Meta):
        db_table = "gbu_hazard_assessment_activity"
        default_permissions = ("add", "change", "view")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_gbu_activity_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "next_review_date"],
                name="ix_gbu_activity_review_date",
            ),
        ]
        verbose_name = "GBU-Tätigkeit"
        verbose_name_plural = "GBU-Tätigkeiten"

    def __str__(self) -> str:
        return f"{self.activity_description[:60]} ({self.status})"

    @property
    def is_approved(self) -> bool:
        return self.status == ActivityStatus.APPROVED


class ActivityMeasure(models.Model):
    """
    Konkrete Schutzmaßnahme einer GBU-Tätigkeit.

    tenant_id denormalisiert für RLS ohne JOIN auf activity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Denormalisiert von HazardAssessmentActivity.tenant_id (ADR-003)",
    )
    activity = models.ForeignKey(
        HazardAssessmentActivity,
        on_delete=models.PROTECT,
        related_name="measures",
    )
    template = models.ForeignKey(
        MeasureTemplate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Vorlage aus der Datenbank (optional)",
    )
    tops_type = models.CharField(
        max_length=1,
        choices=[(t.value, t.name.title()) for t in TOPSType],
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    legal_basis = models.CharField(max_length=200, blank=True, default="")
    is_confirmed = models.BooleanField(
        default=False,
        help_text="Vom Nutzer bestätigt (nicht nur Vorlage)",
    )
    is_mandatory = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gbu_activity_measure"
        ordering = ["tops_type", "sort_order"]
        verbose_name = "GBU-Schutzmaßnahme"
        verbose_name_plural = "GBU-Schutzmaßnahmen"

    def __str__(self) -> str:
        return f"[{self.tops_type}] {self.title}"
