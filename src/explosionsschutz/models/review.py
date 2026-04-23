# src/explosionsschutz/models/review.py
"""
Prüfpläne und Anhang-I-Checklisten-Assessments.

ReviewScheduleEntry: Regulatorische Prüffristen (TRGS 722-725, § 6(9) GefStoffV).
AnnexIChecklistAssessment: Konzept-gebundene Bewertung der 22 Mindestanforderungen.

ADR-044 Phase 4B.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class RegulatoryLayer(models.TextChoices):
    PRIMARY = "TRGS_722", "Primärer Schutz (TRGS 722)"
    SECONDARY = "TRGS_723", "Sekundärer Schutz (TRGS 723)"
    TERTIARY = "TRGS_724", "Konstruktiver Schutz (TRGS 724)"
    MSR = "TRGS_725", "MSR-Schutz (TRGS 725)"
    FIRE = "FIRE", "Brandschutz"
    EFFECTIVENESS = "EFFECT", "Wirksamkeitsprüfung (§ 6(9) GefStoffV)"


class InspectorRole(models.TextChoices):
    ZPBP = "zPbP", "Zur Prüfung befähigte Person (zPbP)"
    ZUES = "ZUeS", "Zugelassene Überwachungsstelle (ZÜS)"
    ARBEITGEBER = "AG", "Arbeitgeber"
    FACHFIRMA = "FF", "Fachfirma"


class ReviewScheduleEntry(models.Model):
    """
    Regulatorische Prüffrist-Eintrag pro Schutz-Layer und Konzept.

    Modelliert die 4 parallelen TRGS-Fristen-Achsen (722/723/724/725)
    plus Brandschutz und Wirksamkeitsprüfung.

    Default-Werte kommen aus einem globalen InspectionCalendarTemplate
    (seedbar), können pro Konzept überschrieben werden.
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="review_schedule_entries",
    )
    regulatory_layer = models.CharField(
        max_length=15,
        choices=RegulatoryLayer.choices,
    )
    measure_description = models.CharField(
        max_length=200,
        help_text="Bezeichnung der Prüfmaßnahme",
    )
    legal_basis = models.CharField(
        max_length=100,
        help_text="z.B. 'TRGS 722 i.V.m. § 7(7) GefStoffV'",
    )
    interval_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Prüfintervall in Monaten (NULL = einmalig oder ereignisgetriggert)",
    )
    first_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Erste Fälligkeit (Inbetriebnahme oder Erstellungsdatum)",
    )
    last_completed_date = models.DateField(
        null=True,
        blank=True,
    )
    next_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Wird automatisch aus last_completed_date + interval_months berechnet",
    )
    inspector_role = models.CharField(
        max_length=10,
        choices=InspectorRole.choices,
        help_text="Wer muss diese Prüfung durchführen?",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_review_schedule_entry"
        verbose_name = "Prüfplan-Eintrag"
        verbose_name_plural = "Prüfplan-Einträge"
        ordering = ["concept", "regulatory_layer", "next_due_date"]

    def __str__(self) -> str:
        interval = f" (alle {self.interval_months} Mo.)" if self.interval_months else ""
        return f"{self.get_regulatory_layer_display()}: {self.measure_description}{interval}"


class AnnexIChecklistAssessmentStatus(models.TextChoices):
    NOT_APPLICABLE = "NOT_APPLICABLE", "Nicht erforderlich"
    COMPLIANT = "COMPLIANT", "Erfüllt"
    NON_COMPLIANT = "NON_COMPLIANT", "Nicht erfüllt"
    PENDING = "PENDING", "In Bearbeitung"


class AnnexIChecklistAssessment(models.Model):
    """
    Konzept-gebundene Bewertung eines Anhang-I-Checklistenpunkts.

    M:1 auf AnnexIChecklistItem (globale Referenz).
    Optionale Verknüpfung mit einer offenen Maßnahme (corrective_action_link).
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="annex_i_assessments",
    )
    item = models.ForeignKey(
        "explosionsschutz.AnnexIChecklistItem",
        on_delete=models.PROTECT,
        related_name="assessments",
    )
    status = models.CharField(
        max_length=20,
        choices=AnnexIChecklistAssessmentStatus.choices,
        default=AnnexIChecklistAssessmentStatus.PENDING,
    )
    evidence_text = models.TextField(
        blank=True,
        help_text="Nachweis-Text oder Verweis auf Dokumentation",
    )
    corrective_action_link = models.ForeignKey(
        "actions.ActionItem",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="annex_i_assessments",
        help_text="Verknüpfte offene Maßnahme bei NON_COMPLIANT",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_annex_i_checklist_assessment"
        verbose_name = "Anhang-I-Bewertung"
        verbose_name_plural = "Anhang-I-Bewertungen"
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "item"],
                name="uniq_annex_i_per_concept",
            ),
        ]

    def __str__(self) -> str:
        item_clause = self.item.clause_number if self.item_id else "?"
        return f"{item_clause}: {self.get_status_display()}"
