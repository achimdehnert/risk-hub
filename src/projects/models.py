"""Project models (ADR-041).

Phase 1: Project + ProjectModule
- BigAutoField (Platform-Prinzip) + separates uuid-Feld
- ProjectModule als Tabelle statt JSONField
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
