"""Project models (ADR-041).

- BigAutoField (Platform-Prinzip) + separates uuid-Feld
- ProjectModule als Tabelle statt JSONField
- ProjectDocument: hochgeladene Unterlagen
- OutputDocument + DocumentSection: generierte Dokumente
"""

import uuid

from django.conf import settings
from django.db import models
from django_tenancy.managers import TenantManager


class Project(models.Model):
    """Zentraler Projektcontainer — modulübergreifend (ADR-041)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        ON_HOLD = "on_hold", "Pausiert"
        COMPLETED = "completed", "Abgeschlossen"
        ARCHIVED = "archived", "Archiviert"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant_id = models.UUIDField(db_index=True)
    site = models.ForeignKey(
        "tenancy.Site",
        on_delete=models.CASCADE,
        related_name="projects",
    )

    name = models.CharField(max_length=255)
    project_number = models.CharField(max_length=50, blank=True, default="")
    client_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Auftraggeber",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Freitext-Beschreibung für KI-Modulempfehlung",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        db_table = "project"
        verbose_name = "Projekt"
        verbose_name_plural = "Projekte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="ix_project_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"

    @property
    def active_modules(self) -> list[str]:
        """Return list of active module codes."""
        return list(
            self.modules.filter(
                status=ProjectModule.Status.ACTIVE,
            ).values_list("module", flat=True)
        )

    @property
    def completion_summary(self) -> dict:
        """Quick stats for dashboard display."""
        return {
            "active_modules": self.modules.filter(
                status=ProjectModule.Status.ACTIVE,
            ).count(),
            "declined_modules": self.modules.filter(
                status=ProjectModule.Status.DECLINED,
            ).count(),
        }


class ProjectModule(models.Model):
    """Modul-Zuordnung pro Projekt (ADR-041).

    Tabelle statt JSONField für:
    - Referenzielle Integrität und DB-Index
    - Metadaten pro Modul (KI-Empfehlung, Aktivierungsdatum)
    - enabled + declined in einer Tabelle
    - Abfragbar via ORM
    - Erweiterbar ohne Migration bei neuen Modulen
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        DECLINED = "declined", "Bewusst abgelehnt"
        DEACTIVATED = "deactivated", "Nachträglich deaktiviert"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    module = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Modul-Code z.B. 'explosionsschutz', 'gbu'",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_ai_recommended = models.BooleanField(default=False)
    ai_reason = models.TextField(
        blank=True,
        default="",
        help_text="KI-Begründung für Empfehlung",
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_module"
        verbose_name = "Projekt-Modul"
        verbose_name_plural = "Projekt-Module"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "module"],
                name="uq_project_module",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.module} ({self.get_status_display()})"


class ProjectDocument(models.Model):
    """Hochgeladene Projektunterlage (ADR-041 Phase 2)."""

    class DocType(models.TextChoices):
        SDS = "sds", "Sicherheitsdatenblatt"
        PLAN = "plan", "Grundriss/Anlagenplan"
        GUTACHTEN = "gutachten", "Bestehendes Gutachten"
        REGULATION = "regulation", "Regelwerk/Norm"
        PROCESS = "process", "Verfahrensbeschreibung"
        OTHER = "other", "Sonstiges"

    uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    title = models.CharField(max_length=255)
    doc_type = models.CharField(
        max_length=20,
        choices=DocType.choices,
        default=DocType.OTHER,
    )
    file = models.FileField(upload_to="projects/docs/%Y/%m/")

    extracted_text = models.TextField(blank=True, default="")
    page_count = models.IntegerField(null=True, blank=True)
    ai_summary = models.TextField(blank=True, default="")

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "project_document"
        verbose_name = "Projektunterlage"
        verbose_name_plural = "Projektunterlagen"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_doc_type_display()})"

    @property
    def filename(self) -> str:
        """Return just the filename from the file path."""
        if self.file:
            return self.file.name.split("/")[-1]
        return ""


class OutputDocument(models.Model):
    """Generiertes Ausgabedokument (ADR-041 Phase 4)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Entwurf"
        REVIEW = "review", "In Prüfung"
        APPROVED = "approved", "Freigegeben"

    uuid = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="output_documents",
    )

    kind = models.CharField(
        max_length=50,
        help_text="Dokumenttyp, z.B. ex_schutz, gbu, brandschutz",
    )
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "project_output_document"
        verbose_name = "Ausgabedokument"
        verbose_name_plural = "Ausgabedokumente"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.title} v{self.version} ({self.get_status_display()})"


class DocumentSection(models.Model):
    """Abschnitt im Ausgabedokument (ADR-041 Phase 4)."""

    document = models.ForeignKey(
        OutputDocument,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    section_key = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True, default="")
    is_ai_generated = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project_document_section"
        verbose_name = "Dokumentabschnitt"
        verbose_name_plural = "Dokumentabschnitte"
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.order}. {self.title}"
