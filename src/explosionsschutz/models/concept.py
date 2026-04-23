# src/explosionsschutz/models/concept.py
"""
Anlagenstruktur und Explosionsschutzkonzept.

Area: Betriebsbereich / Anlage innerhalb eines Standorts
ExplosionConcept: Explosionsschutzkonzept nach TRGS 720ff
"""

from django.contrib.auth import get_user_model
from django.db import models
from django_tenancy.managers import TenantManager

User = get_user_model()


class Area(models.Model):
    """Betriebsbereich / Anlage innerhalb eines Standorts"""

    tenant_id = models.UUIDField(db_index=True)
    site_id = models.UUIDField(db_index=True, help_text="FK zu tenancy.Site")

    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50, blank=True, default="", help_text="Anlagenkennzeichen (z.B. 'E2-50.01')"
    )
    description = models.TextField(blank=True, default="")

    dxf_file = models.FileField(
        upload_to="areas/dxf/",
        null=True,
        blank=True,
        help_text="Grundriss-DXF für Zonengeometrie und Brandschutz-Analyse",
    )
    dxf_analysis_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Ergebnis der nl2cad-core/areas DXF-Analyse (Räume, Flächen)",
    )
    dxf_svg = models.FileField(
        upload_to="areas/svg/",
        null=True,
        blank=True,
        help_text="SVG-Preview generiert aus DXF via ezdxf",
    )
    brandschutz_analysis_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Ergebnis der nl2cad-brandschutz Analyse (Fluchtwege, Mängel)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_area"
        verbose_name = "Betriebsbereich"
        verbose_name_plural = "Betriebsbereiche"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "site_id", "code"],
                name="uq_area_code_per_site",
                condition=models.Q(code__gt=""),
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}" if self.code else self.name

    @property
    def has_explosion_hazard(self) -> bool:
        """Prüft ob Ex-relevante Konzepte im Bereich existieren"""
        return self.explosion_concepts.filter(
            status__in=["APPROVED", "APPROVED_WITH_ACTIONS", "REVIEW"]
        ).exists()


class ExplosionConcept(models.Model):
    """Explosionsschutzkonzept nach TRGS 720ff"""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Entwurf"
        IN_PROGRESS = "IN_PROGRESS", "In Bearbeitung"
        REVIEW = "REVIEW", "In Prüfung"
        APPROVED = "APPROVED", "Freigegeben"
        APPROVED_WITH_ACTIONS = "APPROVED_WITH_ACTIONS", "Freigegeben mit offenen Maßnahmen"
        REVIEW_REQUIRED = "REVIEW_REQUIRED", "Überprüfung erforderlich"
        ARCHIVED = "ARCHIVED", "Archiviert"

    class StorageMode(models.TextChoices):
        ACTIVE = "ACTIVE", "Aktive Lagerung"
        PASSIVE = "PASSIVE", "Passive Lagerung"
        PROCESS = "PROCESS", "Verfahrensanlage"

    tenant_id = models.UUIDField(db_index=True)

    # Beziehungen
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="explosion_concepts")
    assessment_id = models.UUIDField(
        null=True, blank=True, db_index=True, help_text="FK zu risk.Assessment (optional)"
    )
    substance_id = models.UUIDField(
        null=True, blank=True, db_index=True, help_text="FK zu substances.Substance (UUID)"
    )
    substance_name = models.CharField(
        max_length=255, blank=True, default="", help_text="Cached Stoffname für Anzeige"
    )

    # ADR-041 — Project-Einbettung (null=True für 3 Monate nach Release)
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.PROTECT,
        related_name="explosion_concepts",
        help_text="ADR-041 Container (ADR-044 Phase 3). Pflichtfeld nach Datenmigration 0011.",
    )

    # Metadaten
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    revision_number = models.PositiveIntegerField(
        default=1,
        help_text="Fachliche Revisionsnummer (getrennt von der internen Versions-ID)",
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    storage_mode = models.CharField(
        max_length=10,
        choices=StorageMode.choices,
        blank=True,
        default="",
        help_text="Lagerungs- / Prozess-Charakter der Anlage",
    )

    # Validierung
    is_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="validated_concepts"
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    # Audit
    created_by = models.UUIDField(
        null=True,
        blank=True,
        help_text="User-ID des Erstellers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_concept"
        verbose_name = "Explosionsschutzkonzept"
        verbose_name_plural = "Explosionsschutzkonzepte"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_concept_tenant_status",
            ),
        ]
        permissions = [
            ("use_ai", "KI-Augmentierung nutzen (ADR-018)"),
        ]

    def __str__(self) -> str:
        return f"{self.title} (v{self.version})"

    @property
    def sds_data(self) -> dict:
        """Ex-relevante Daten aus aktuellem SDS (read-only)"""
        return {
            "substance_id": str(self.substance_id),
            "substance_name": self.substance_name,
        }

    @property
    def completion_percentage(self) -> int:
        """Fortschritt des Konzepts (für UI)"""
        total = 4
        completed = 0

        if self.area.zone_definitions.filter(explosion_concept=self).exists():
            completed += 1
        if self.protection_measures.filter(category="primary").exists():
            completed += 1
        if self.protection_measures.filter(category="secondary").exists():
            completed += 1
        if self.is_validated:
            completed += 1

        return int((completed / total) * 100)
