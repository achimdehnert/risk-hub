# src/explosionsschutz/models/concept_doc.py
"""
Concept-Template Integration für Explosionsschutz (ADR-147).

Concrete Models für iil-concept-templates:
- ExConceptDocument: Hochgeladene Dokumente + LLM-Analyse
- ExConceptTemplateStore: Persistierte Templates
- ExFilledTemplate: Ausgefüllte Templates
"""

from django.db import models
from django_tenancy.managers import TenantManager

from .concept import ExplosionConcept


class ExConceptDocument(models.Model):
    """Unterlage zu einem Explosionsschutzkonzept (ADR-147).

    Speichert hochgeladene Dokumente mit Extraktionsergebnis und
    optionalem Template-JSON aus LLM-Analyse.
    """

    class DocStatus(models.TextChoices):
        UPLOADED = "uploaded", "Hochgeladen"
        EXTRACTING = "extracting", "Wird extrahiert"
        EXTRACTED = "extracted", "Text extrahiert"
        ANALYZING = "analyzing", "Wird analysiert"
        ANALYZED = "analyzed", "Analysiert"
        FAILED = "failed", "Fehlgeschlagen"

    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        ExplosionConcept,
        on_delete=models.CASCADE,
        related_name="concept_documents",
    )
    title = models.CharField(max_length=240)
    scope = models.CharField(
        max_length=30,
        blank=True,
        default="explosionsschutz",
    )
    source_filename = models.CharField(max_length=255, blank=True, default="")
    content_type = models.CharField(max_length=120, blank=True, default="")
    extracted_text = models.TextField(blank=True, default="")
    extraction_warnings = models.TextField(
        blank=True,
        default="",
        help_text="JSON-Liste von Warnungen aus der Extraktion",
    )
    page_count = models.IntegerField(null=True, blank=True)
    template_json = models.TextField(
        blank=True,
        default="",
        help_text="Serialisiertes ConceptTemplate nach LLM-Analyse",
    )
    analysis_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="0.0-1.0, Konfidenz der LLM-Strukturanalyse",
    )
    status = models.CharField(
        max_length=20,
        choices=DocStatus.choices,
        default=DocStatus.UPLOADED,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_concept_document"
        verbose_name = "Ex-Konzept-Unterlage"
        verbose_name_plural = "Ex-Konzept-Unterlagen"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_ex_cdoc_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def has_extracted_text(self) -> bool:
        return bool(self.extracted_text)

    @property
    def has_template(self) -> bool:
        return bool(self.template_json)


class ExConceptTemplateStore(models.Model):
    """Persistiertes Konzept-Template für Explosionsschutz (ADR-147).

    Wird erstellt aus:
    - LLM-Analyse eines ExConceptDocument
    - Built-in Framework (exschutz_trgs720)
    - Manueller Merge mehrerer Analysen
    """

    class TemplateSource(models.TextChoices):
        ANALYZED = "analyzed", "Aus Dokumentanalyse"
        BUILTIN = "builtin", "Framework-Vorlage"
        MERGED = "merged", "Zusammengeführt"
        MANUAL = "manual", "Manuell erstellt"

    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=30, default="explosionsschutz")
    version = models.CharField(max_length=20, default="1.0")
    is_master = models.BooleanField(default=False)
    framework = models.CharField(max_length=100, blank=True, default="")
    source = models.CharField(
        max_length=20,
        choices=TemplateSource.choices,
        default=TemplateSource.ANALYZED,
    )
    source_document = models.ForeignKey(
        ExConceptDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_templates",
    )
    template_json = models.TextField(
        help_text="Serialisiertes ConceptTemplate (Pydantic JSON)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_concept_template_store"
        verbose_name = "Ex-Konzept-Template"
        verbose_name_plural = "Ex-Konzept-Templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "scope"],
                name="ix_ex_ctmpl_tenant_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.get_source_display()})"


class ExFilledTemplate(models.Model):
    """Ausgefülltes Template für ein Explosionsschutzkonzept (ADR-147).

    Enthält die vom Benutzer (und optional KI) eingetragenen Werte
    für ein ExConceptTemplateStore. Daraus wird das finale Dokument generiert.
    """

    class FillStatus(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"
        EXPORTED = "exported", "Exportiert"

    tenant_id = models.UUIDField(db_index=True)
    concept = models.ForeignKey(
        ExplosionConcept,
        on_delete=models.CASCADE,
        related_name="filled_templates",
    )
    template = models.ForeignKey(
        ExConceptTemplateStore,
        on_delete=models.PROTECT,
        related_name="filled_instances",
    )
    name = models.CharField(max_length=240)
    values_json = models.TextField(
        default="{}",
        help_text="JSON: {section_name: {field_name: value}}",
    )
    status = models.CharField(
        max_length=20,
        choices=FillStatus.choices,
        default=FillStatus.DRAFT,
        db_index=True,
    )
    generated_pdf_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="S3-Pfad des generierten PDFs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_filled_template"
        verbose_name = "Ausgefülltes Ex-Template"
        verbose_name_plural = "Ausgefüllte Ex-Templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_ex_ftmpl_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"
