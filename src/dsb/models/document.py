"""DsbDocument — Dokumenten-Archiv für DSB-Modul (PDF, DOCX, etc.)."""

import uuid
from pathlib import Path

from django.db import models

from .mandate import Mandate


def _upload_path(instance: "DsbDocument", filename: str) -> str:
    """Speichert Dateien unter media/dsb/<tenant_id>/<ref_type>/<pk>/<filename>."""
    ext = Path(filename).suffix.lower()
    safe_name = Path(filename).stem[:80]
    return (
        f"dsb/{instance.tenant_id}/{instance.ref_type}/"
        f"{instance.ref_id or 'general'}/{safe_name}{ext}"
    )


class DsbDocument(models.Model):
    """Archiviertes Dokument im DSB-Modul (PDF, DOCX, etc.)."""

    class RefType(models.TextChoices):
        AVV = "avv", "AVV (Art. 28)"
        VVT = "vvt", "VVT (Art. 30)"
        TOM = "tom", "TOM (Art. 32)"
        BREACH = "breach", "Datenpanne (Art. 33)"
        DELETION = "deletion", "Löschantrag (Art. 17)"
        MANDATE = "mandate", "Mandat"
        GENERAL = "general", "Allgemein"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="documents",
        null=True,
        blank=True,
    )

    # Generische Verknüpfung (kein GenericForeignKey um Komplexität zu vermeiden)
    ref_type = models.CharField(
        max_length=20,
        choices=RefType.choices,
        default=RefType.GENERAL,
        db_index=True,
    )
    ref_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID des verknüpften Objekts (AVV, Breach, DeletionRequest, etc.)",
    )

    # Datei
    file = models.FileField(
        upload_to=_upload_path,
        verbose_name="Datei",
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="Bytes")
    mime_type = models.CharField(max_length=100, blank=True)

    # Metadaten
    title = models.CharField(
        max_length=300,
        verbose_name="Bezeichnung",
        help_text="Kurzbeschreibung des Dokuments",
    )
    description = models.TextField(blank=True, verbose_name="Beschreibung")
    document_date = models.DateField(
        null=True, blank=True,
        verbose_name="Dokumentdatum",
        help_text="Datum des Dokuments (z.B. Unterzeichnungsdatum)",
    )

    uploaded_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_document"
        verbose_name = "DSB-Dokument"
        verbose_name_plural = "DSB-Dokumente"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "ref_type", "ref_id"],
                name="idx_dsb_doc_tenant_ref",
            ),
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_doc_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_ref_type_display()})"

    @property
    def file_size_display(self) -> str:
        if not self.file_size:
            return "—"
        if self.file_size < 1024:
            return f"{self.file_size} B"
        if self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        return f"{self.file_size / (1024 * 1024):.1f} MB"

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == "application/pdf" or (
            self.original_filename.lower().endswith(".pdf")
        )

    @property
    def icon(self) -> str:
        if self.is_pdf:
            return "file-text"
        if self.original_filename.lower().endswith((".doc", ".docx")):
            return "file-text"
        if self.original_filename.lower().endswith((".xls", ".xlsx")):
            return "file-spreadsheet"
        return "file"
