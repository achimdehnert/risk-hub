"""AVV — Auftragsverarbeitungsvertrag (Art. 28 DSGVO)."""

import uuid

from django.db import models

from .lookups import Category, SubjectGroup
from .mandate import Mandate
from .vvt import ProcessingActivity


class DataProcessingAgreement(models.Model):
    """Auftragsverarbeitungsvertrag (AVV) gemäß Art. 28 DSGVO."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ACTIVE = "active", "Aktiv"
        EXPIRED = "expired", "Abgelaufen"
        TERMINATED = "terminated", "Gekündigt"

    class Role(models.TextChoices):
        CONTROLLER = "controller", "Verantwortlicher"
        PROCESSOR = "processor", "Auftragsverarbeiter"
        JOINT_CONTROLLER = "joint", "Gemeinsam Verantwortliche"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="dpa_agreements",
    )
    partner_name = models.CharField(
        max_length=300,
        help_text="Name des Vertragspartners",
    )
    partner_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PROCESSOR,
        help_text="Rolle des Partners im Vertrag",
    )
    subject_matter = models.TextField(
        help_text="Gegenstand der Auftragsverarbeitung",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Inkrafttreten",
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Ablaufdatum / Kündigungstermin",
    )
    data_categories = models.ManyToManyField(
        Category,
        blank=True,
        help_text="Verarbeitete Datenkategorien",
    )
    data_subjects = models.ManyToManyField(
        SubjectGroup,
        blank=True,
        help_text="Betroffene Personengruppen",
    )
    processing_activities = models.ManyToManyField(
        ProcessingActivity,
        blank=True,
        related_name="dpa_agreements",
        help_text="Zugeordnete Verarbeitungstätigkeiten",
    )
    technical_measures = models.ManyToManyField(
        "TechnicalMeasure",
        blank=True,
        help_text="Vereinbarte technische Maßnahmen",
    )
    organizational_measures = models.ManyToManyField(
        "OrganizationalMeasure",
        blank=True,
        help_text="Vereinbarte organisatorische Maßnahmen",
    )
    subprocessors_allowed = models.BooleanField(
        default=False,
        help_text="Unterauftragsverarbeitung zulässig",
    )
    subprocessors_notes = models.TextField(
        blank=True,
        default="",
        help_text="Hinweise zu Unterauftragsverarbeitern",
    )
    document_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="FK zu documents.Document (lose Kopplung)",
    )
    notes = models.TextField(blank=True, default="")
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_dpa"
        verbose_name = "Auftragsverarbeitungsvertrag"
        verbose_name_plural = "Auftragsverarbeitungsverträge"
        ordering = ["partner_name"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_dpa_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"AVV: {self.partner_name} ({self.get_status_display()})"
