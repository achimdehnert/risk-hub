"""Risk assessment models."""

from django.db import models
from django_tenancy.managers import TenantManager


class Assessment(models.Model):
    """Risk assessment / Gefährdungsbeurteilung."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        APPROVED = "approved", "Approved"
        ARCHIVED = "archived", "Archived"

    class Category(models.TextChoices):
        BRANDSCHUTZ = "brandschutz", "Brandschutz"
        EXPLOSIONSSCHUTZ = "explosionsschutz", "Explosionsschutz"
        ARBEITSSICHERHEIT = "arbeitssicherheit", "Arbeitssicherheit"
        ARBEITSSCHUTZ = "arbeitsschutz", "Arbeitsschutz"
        GENERAL = "general", "Allgemein"

    tenant_id = models.UUIDField(db_index=True)

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risk_assessments",
        help_text="Standort / Bereich",
    )

    created_by_id = models.UUIDField(null=True, blank=True)
    approved_by_id = models.UUIDField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_assessment"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["draft", "in_review", "approved", "archived"],
                ),
                name="ck_assessment_status_valid",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "title"],
                name="uq_assessment_title_per_tenant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_assessment_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "category"],
                name="idx_assessment_tenant_category",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Hazard(models.Model):
    """Individual hazard within an assessment."""

    class Severity(models.IntegerChoices):
        LOW = 1, "Gering"
        MEDIUM = 2, "Mittel"
        HIGH = 3, "Hoch"
        VERY_HIGH = 4, "Sehr hoch"
        CRITICAL = 5, "Kritisch"

    class Probability(models.IntegerChoices):
        UNLIKELY = 1, "Unwahrscheinlich"
        RARE = 2, "Selten"
        OCCASIONAL = 3, "Gelegentlich"
        PROBABLE = 4, "Wahrscheinlich"
        FREQUENT = 5, "Häufig"

    class MitigationStatus(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        MITIGATED = "mitigated", "Gemindert"
        ACCEPTED = "accepted", "Akzeptiert"

    tenant_id = models.UUIDField(db_index=True)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="hazards",
    )

    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")

    severity = models.IntegerField(
        choices=Severity.choices,
        default=Severity.LOW,
    )
    probability = models.IntegerField(
        choices=Probability.choices,
        default=Probability.UNLIKELY,
    )

    mitigation = models.TextField(blank=True, default="")
    residual_risk = models.IntegerField(null=True, blank=True)
    mitigation_status = models.CharField(
        max_length=15,
        choices=MitigationStatus.choices,
        default=MitigationStatus.OPEN,
        db_index=True,
    )
    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID der verantwortlichen Person für die Maßnahme",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fälligkeitsdatum der Maßnahme",
    )
    product = models.ForeignKey(
        "substances.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hazard_entries",
        help_text="Verknüpftes Handelsprodukt (UC-004+)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_hazard"
        indexes = [
            models.Index(
                fields=["tenant_id", "assessment"],
                name="idx_hazard_tenant_assessment",
            ),
            models.Index(
                fields=["tenant_id", "mitigation_status"],
                name="idx_hazard_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "due_date"],
                name="idx_hazard_tenant_due_date",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def risk_score(self) -> int:
        """Calculate risk score (severity * probability)."""
        return self.severity * self.probability

    @property
    def is_overdue(self) -> bool:
        """True if mitigation is not done and due_date has passed."""
        from django.utils import timezone

        if not self.due_date:
            return False
        return (
            self.mitigation_status
            not in (
                self.MitigationStatus.MITIGATED,
                self.MitigationStatus.ACCEPTED,
            )
            and self.due_date < timezone.now().date()
        )


# =============================================================================
# PROTECTIVE MEASURE (UC-008: STOP-Hierarchie)
# =============================================================================


class ProtectiveMeasure(models.Model):
    """Strukturierte Schutzmaßnahme nach STOP-Hierarchie (UC-008).

    Ersetzt das Freitextfeld Hazard.mitigation durch normalisierte
    Maßnahmen mit Typ, Status, Verantwortlichkeit und Wirksamkeitsprüfung.
    """

    class MeasureType(models.TextChoices):
        SUBSTITUTION = "substitution", "Substitution (S)"
        TECHNICAL = "technical", "Technische Maßnahme (T)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme (O)"
        PERSONAL = "personal", "Persönliche Schutzausrüstung (P)"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        IMPLEMENTED = "implemented", "Umgesetzt"
        NOT_POSSIBLE = "not_possible", "Nicht umsetzbar"

    class EffectivenessResult(models.TextChoices):
        EFFECTIVE = "effective", "Wirksam"
        PARTIALLY = "partially", "Teilweise wirksam"
        INEFFECTIVE = "ineffective", "Unwirksam"
        NOT_CHECKED = "not_checked", "Nicht geprüft"

    tenant_id = models.UUIDField(db_index=True)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="protective_measures",
    )
    hazard = models.ForeignKey(
        Hazard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protective_measures",
        help_text="Verknüpfte Gefährdung (NULL = Assessment-übergreifend)",
    )
    measure_type = models.CharField(
        max_length=20,
        choices=MeasureType.choices,
        db_index=True,
    )
    description = models.TextField(help_text="Beschreibung der Maßnahme")
    specification = models.TextField(
        blank=True,
        default="",
        help_text="PSA-Details, Produktspezifikation (z.B. 'Nitrilhandschuhe, Durchbruchzeit >480 min')",
    )
    norm_reference = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Norm-Referenz (z.B. 'EN 374', 'TRGS 510')",
    )

    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protective_measures",
    )
    department = models.ForeignKey(
        "tenancy.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protective_measures",
    )

    responsible_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    effectiveness_checked_at = models.DateTimeField(null=True, blank=True)
    effectiveness_result = models.CharField(
        max_length=15,
        choices=EffectivenessResult.choices,
        default=EffectivenessResult.NOT_CHECKED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_protective_measure"
        verbose_name = "Schutzmaßnahme"
        verbose_name_plural = "Schutzmaßnahmen"
        ordering = ["measure_type", "-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_measure_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "measure_type"],
                name="idx_measure_tenant_type",
            ),
            models.Index(
                fields=["tenant_id", "due_date"],
                name="idx_measure_tenant_due",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.get_measure_type_display()}] {self.description[:80]}"

    @property
    def is_overdue(self) -> bool:
        from django.utils import timezone

        if not self.due_date:
            return False
        return (
            self.status not in (self.Status.IMPLEMENTED, self.Status.NOT_POSSIBLE)
            and self.due_date < timezone.now().date()
        )


# =============================================================================
# SUBSTITUTION CHECK (UC-008: Substitutionsprüfung)
# =============================================================================


class SubstitutionCheck(models.Model):
    """Dokumentierte Substitutionsprüfung nach GefStoffV §6 (UC-008).

    Verknüpft einen SubstanceUsage mit einer ggf. gefundenen Alternative
    und dem Prüfergebnis.
    """

    class Result(models.TextChoices):
        POSSIBLE = "possible", "Substitution möglich"
        NOT_POSSIBLE = "not_possible", "Nicht möglich (begründet)"
        NOT_REQUIRED = "not_required", "Nicht erforderlich"

    tenant_id = models.UUIDField(db_index=True)
    substance_usage = models.ForeignKey(
        "substances.SubstanceUsage",
        on_delete=models.CASCADE,
        related_name="substitution_checks",
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitution_checks",
    )
    current_product = models.ForeignKey(
        "substances.Product",
        on_delete=models.CASCADE,
        related_name="substitution_checks_current",
    )
    alternative_product = models.ForeignKey(
        "substances.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitution_checks_alternative",
        help_text="Vorgeschlagenes Alternativprodukt (NULL wenn nicht möglich)",
    )

    result = models.CharField(
        max_length=20,
        choices=Result.choices,
    )
    justification = models.TextField(
        help_text="Begründung (insbes. bei 'nicht möglich')",
    )
    checked_by = models.UUIDField(db_index=True)
    checked_at = models.DateTimeField()
    implementation_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Umsetzungsfrist bei positivem Ergebnis",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "risk_substitution_check"
        verbose_name = "Substitutionsprüfung"
        verbose_name_plural = "Substitutionsprüfungen"
        ordering = ["-checked_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "result"],
                name="idx_subst_check_result",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.current_product} — {self.get_result_display()}"
