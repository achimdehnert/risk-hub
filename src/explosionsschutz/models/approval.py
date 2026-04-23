# src/explosionsschutz/models/approval.py
"""
Freigabe-Erklärung und Compliance-Snapshot.

ApprovalStatement: Formelle Freigabe-Erklärung mit Juristenformel.
ConceptDocumentLink: M2M-Verknüpfung Konzept ↔ ProjectDocument.
ConceptApprovalSnapshot: Immutable Audit-Freeze bei Freigabe.

Snapshots werden ausschließlich durch ConceptApprovalService erstellt.
Kein updated_at — niemals manuell bearbeitet.

ADR-044 Phase 5A.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class ApprovalStatement(models.Model):
    """
    Formelle Freigabe-Erklärung (Valmet/DHRW-Stil).

    Die Juristenformel wird aus einem Template gerendert und im
    rendered_text gespeichert. signed_by_id ist UUIDField (kein FK),
    da Audit-Trail auch nach User-Löschung erhalten bleiben muss.
    """

    class SignatoryRole(models.TextChoices):
        ARBEITGEBER = "ARBEITGEBER", "Arbeitgeber"
        BETREIBER = "BETREIBER", "Betreiber"
        ARBEITGEBER_BETREIBER = "AG_BETREIBER", "Arbeitgeber / Betreiber"

    concept = models.OneToOneField(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.PROTECT,
        related_name="approval_statement",
    )
    statement_template_id = models.CharField(
        max_length=50,
        help_text="Key des verwendeten Statement-Templates",
    )
    rendered_text = models.TextField(
        help_text="Fertig gerenderter Freigabe-Text nach Variablen-Ersetzung",
    )
    legal_framework_reference = models.CharField(
        max_length=100,
        help_text="z.B. '§ 6(9) GefStoffV i.V.m. § 6(4) BetrSichV'",
    )
    signatory_role = models.CharField(
        max_length=20,
        choices=SignatoryRole.choices,
    )

    signed_by_id = models.UUIDField(
        help_text="User-UUID des Unterzeichners (kein FK — Audit-Trail bleibt nach User-Löschung erhalten)",
    )
    signed_by_name = models.CharField(max_length=200)
    signed_by_role = models.CharField(
        max_length=100,
        help_text="Funktionsbezeichnung des Unterzeichners",
    )
    signed_at = models.DateTimeField()

    digital_signature_hash = models.CharField(
        max_length=128,
        blank=True,
        help_text="SHA-256 Hash der digitalen Signatur (optional)",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_approval_statement"
        verbose_name = "Freigabe-Erklärung"
        verbose_name_plural = "Freigabe-Erklärungen"

    def __str__(self) -> str:
        concept_title = self.concept.title if self.concept_id else "?"
        return f"Freigabe: {concept_title} ({self.signed_by_name}, {self.signed_at:%Y-%m-%d})"


class ConceptDocumentLink(models.Model):
    """
    M2M-Verknüpfung zwischen ExplosionConcept und ProjectDocument.

    Ein SDB für Wasserstoff kann von mehreren Konzepten im selben Projekt
    geteilt werden, ohne dupliziert zu werden.
    Replaces AssociatedDocument (ADR-041 Konvergenz-Memo).
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.CASCADE,
        related_name="document_links",
    )
    document = models.ForeignKey(
        "projects.ProjectDocument",
        on_delete=models.PROTECT,
        related_name="concept_links",
    )
    relevance_note = models.CharField(
        max_length=200,
        blank=True,
        help_text="z.B. 'Primäres SDB für Zonenbewertung' oder 'Verfahrensplan Raum 04.01'",
    )

    class Meta:
        db_table = "concept_document_link"
        verbose_name = "Konzept-Dokument-Link"
        verbose_name_plural = "Konzept-Dokument-Links"
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "document"],
                name="uniq_document_per_concept",
            ),
        ]

    def __str__(self) -> str:
        doc_name = self.document.name if self.document_id else "?"
        return f"→ {doc_name}"


class ConceptApprovalSnapshot(models.Model):
    """
    Immutable Audit-Freeze bei Freigabe.

    Erstellt ausschließlich durch ConceptApprovalService.
    Kein updated_at — kein Edit-Permission — nur add + view.
    PostgreSQL RLS verhindert DELETE auf DB-Ebene.
    """

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.PROTECT,
        related_name="approval_snapshots",
    )
    snapshot_version = models.PositiveIntegerField()

    zones_snapshot_json = models.JSONField(
        help_text="Serialisierte ZoneDefinitions zum Freigabe-Zeitpunkt",
    )
    ignition_sources_snapshot_json = models.JSONField(
        help_text="Serialisierte ZoneIgnitionSourceAssessments zum Freigabe-Zeitpunkt",
    )
    safety_functions_snapshot_json = models.JSONField(
        help_text="Serialisierte MsrSafetyFunctions zum Freigabe-Zeitpunkt",
    )
    review_schedule_snapshot_json = models.JSONField(
        help_text="Serialisierte ReviewScheduleEntries zum Freigabe-Zeitpunkt",
    )
    annex_i_assessment_snapshot_json = models.JSONField(
        help_text="Serialisierte AnnexIChecklistAssessments zum Freigabe-Zeitpunkt",
    )
    substance_references_snapshot_json = models.JSONField(
        help_text="Serialisierte ConceptSubstanceReferences zum Freigabe-Zeitpunkt",
    )
    operational_states_snapshot_json = models.JSONField(
        default=list,
        help_text="OperationalStateAssessments zum Freigabe-Zeitpunkt eingefroren",
    )

    approval_statement = models.ForeignKey(
        ApprovalStatement,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="snapshots",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_concept_approval_snapshot"
        verbose_name = "Freigabe-Snapshot"
        verbose_name_plural = "Freigabe-Snapshots"
        default_permissions = ("add", "view")
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "snapshot_version"],
                name="uniq_snapshot_per_version",
            ),
        ]

    def __str__(self) -> str:
        concept_title = self.concept.title if self.concept_id else "?"
        return f"Snapshot v{self.snapshot_version}: {concept_title} ({self.created_at:%Y-%m-%d})"
