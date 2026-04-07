# src/explosionsschutz/models/doc_template.py
"""
Standalone Dokument-Template-System für Explosionsschutz.

Unabhängig von concept_templates Package.
BigAutoField PKs (Platform-Standard DB-001).

Workflow:
  UC1: PDF hochladen → Template-Struktur erstellen → editieren → akzeptieren
  UC2: Template auswählen → Inhalte von Grund auf erstellen
  UC3: Template auswählen → Dokument hochladen → Inhalte einlesen → editieren
"""

import uuid

from django.db import models
from django_tenancy.managers import TenantManager


class ExDocTemplate(models.Model):
    """Wiederverwendbare Dokumentvorlage für Ex-Schutz.

    Struktur als JSON:
    {
      "sections": [
        {
          "key": "section_1",
          "label": "1. Allgemeines",
          "fields": [
            {"key": "zweck", "label": "Zweck", "type": "text", "required": true},
            {"key": "beschreibung", "label": "Beschreibung", "type": "textarea"}
          ]
        }
      ]
    }
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        ACCEPTED = "accepted", "Akzeptiert"
        ARCHIVED = "archived", "Archiviert"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    structure_json = models.TextField(
        default='{"sections": []}',
        help_text="Template-Struktur als JSON",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    source_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Dateiname des Quell-PDFs (falls aus Upload)",
    )
    source_text = models.TextField(
        blank=True,
        default="",
        help_text="Extrahierter Text aus Quell-PDF",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_doc_template"
        verbose_name = "Ex-Dokumentvorlage"
        verbose_name_plural = "Ex-Dokumentvorlagen"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_ex_doctmpl_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    @property
    def section_count(self) -> int:
        import json

        try:
            data = json.loads(self.structure_json)
            return len(data.get("sections", []))
        except (json.JSONDecodeError, TypeError):
            return 0

    @property
    def field_count(self) -> int:
        import json

        try:
            data = json.loads(self.structure_json)
            return sum(len(s.get("fields", [])) for s in data.get("sections", []))
        except (json.JSONDecodeError, TypeError):
            return 0


class ExDocInstance(models.Model):
    """Ausgefülltes Dokument basierend auf einem Template.

    Werte als JSON:
    {
      "section_1": {
        "zweck": "Dieses Dokument...",
        "beschreibung": "..."
      }
    }
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    template = models.ForeignKey(
        ExDocTemplate,
        on_delete=models.PROTECT,
        related_name="instances",
    )
    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="doc_instances",
        help_text="Verknüpftes Ex-Konzept (optional)",
    )
    name = models.CharField(max_length=255)
    values_json = models.TextField(
        default="{}",
        help_text="Ausgefüllte Werte als JSON",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    source_filename = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Dateiname des importierten Dokuments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_doc_instance"
        verbose_name = "Ex-Dokument"
        verbose_name_plural = "Ex-Dokumente"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_ex_docinst_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"
