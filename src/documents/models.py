"""Document models."""

from django.db import models
from django_tenancy.managers import TenantManager


class Document(models.Model):
    """Document with versioning."""

    class Category(models.TextChoices):
        BRANDSCHUTZ = "brandschutz", "Brandschutz"
        EXPLOSIONSSCHUTZ = "explosionsschutz", "Explosionsschutz"
        ARBEITSSICHERHEIT = "arbeitssicherheit", "Arbeitssicherheit"
        NACHWEIS = "nachweis", "Nachweis"
        GENERAL = "general", "Allgemein"
        SDB = "sdb", "Sicherheitsdatenblatt"
        GEFAEHRDUNGSBEURTEILUNG = "gefaehrdungsbeurteilung", "Gefährdungsbeurteilung"
        BETRIEBSANWEISUNG = "betriebsanweisung", "Betriebsanweisung"
        UNTERWEISUNG = "unterweisung", "Unterweisungsnachweis"
        PRUEFBERICHT = "pruefbericht", "Prüfbericht"

    tenant_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=240)
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    concept_ref_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional: Verknüpfung zu Brandschutz-/Explosionsschutzkonzept",
    )
    scope = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Fachbereich: brandschutz, explosionsschutz, etc.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "documents_document"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "title"], name="uq_doc_title_per_tenant"),
        ]

    def __str__(self) -> str:
        return self.title


class DocumentVersion(models.Model):
    """Version of a document stored in S3."""

    tenant_id = models.UUIDField(db_index=True)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version = models.IntegerField()
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size_bytes = models.BigIntegerField()
    sha256 = models.CharField(max_length=64)
    s3_key = models.CharField(max_length=512)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "documents_document_version"
        constraints = [
            models.UniqueConstraint(fields=["document", "version"], name="uq_doc_version"),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} v{self.version}"
