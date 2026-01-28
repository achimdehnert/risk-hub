"""Document models."""

import uuid
from django.db import models


class Document(models.Model):
    """Document with versioning."""
    
    CATEGORY_CHOICES = [
        ("brandschutz", "Brandschutz"),
        ("explosionsschutz", "Explosionsschutz"),
        ("arbeitssicherheit", "Arbeitssicherheit"),
        ("nachweis", "Nachweis"),
        ("general", "Allgemein"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=240)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="general")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_document"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_doc_title_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.title


class DocumentVersion(models.Model):
    """Version of a document stored in S3."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version = models.IntegerField()
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    s3_key = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "documents_document_version"
        constraints = [
            models.UniqueConstraint(fields=["document", "version"], name="uq_doc_version"),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} v{self.version}"
