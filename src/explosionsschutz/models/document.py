# src/explosionsschutz/models/document.py
"""
Nachweis- und Prüfdokumente zum Ex-Konzept.
"""

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_tenancy.managers import TenantManager

from .concept import ExplosionConcept

User = get_user_model()

class VerificationDocument(models.Model):
    """Nachweis- und Prüfdokumente zum Ex-Konzept"""

    class DocumentType(models.TextChoices):
        CERTIFICATE = "certificate", "Prüfbescheinigung"
        REPORT = "report", "Prüfbericht"
        MSR_TEST = "msr_test", "MSR-Prüfprotokoll"
        PHOTO = "photo", "Foto/Dokumentation"
        DRAWING = "drawing", "Zeichnung/Plan"
        APPROVAL = "approval", "Genehmigung"
        OTHER = "other", "Sonstige"

    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(
        ExplosionConcept, on_delete=models.CASCADE, related_name="documents"
    )

    title = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    description = models.TextField(blank=True, default="")

    file = models.FileField(upload_to="exschutz/docs/%Y/%m/", null=True, blank=True)
    document_version_id = models.UUIDField(
        null=True, blank=True, help_text="FK zu documents.DocumentVersion"
    )

    issued_at = models.DateField(null=True, blank=True)
    issued_by = models.CharField(max_length=200, blank=True, default="")
    valid_until = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_verification_document"
        verbose_name = "Nachweisdokument"
        verbose_name_plural = "Nachweisdokumente"
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_document_type_display()})"
