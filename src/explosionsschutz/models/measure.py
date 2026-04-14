# src/explosionsschutz/models/measure.py
"""
Schutzmaßnahmen (primär, sekundär, tertiär, organisatorisch).
"""

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_tenancy.managers import TenantManager

from .concept import ExplosionConcept
from .master_data import MeasureCatalog, SafetyFunction

User = get_user_model()

class ProtectionMeasure(models.Model):
    """Schutzmaßnahme (primär, sekundär, tertiär, organisatorisch)"""

    class Category(models.TextChoices):
        PRIMARY = "primary", "Primäre Maßnahme (Vermeidung)"
        SECONDARY = "secondary", "Sekundäre Maßnahme (Zündquellenvermeidung)"
        TERTIARY = "tertiary", "Tertiäre Maßnahme (Auswirkungsbegrenzung)"
        ORGANIZATIONAL = "organizational", "Organisatorische Maßnahme"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        DONE = "done", "Umgesetzt"
        VERIFIED = "verified", "Verifiziert"
        OBSOLETE = "obsolete", "Obsolet"

    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(ExplosionConcept, on_delete=models.CASCADE, related_name="measures")

    # Klassifikation
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SECONDARY)
    catalog_reference = models.ForeignKey(
        MeasureCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Vorlage aus Maßnahmenkatalog",
    )

    # Inhalt
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # MSR-Bewertung (optional)
    safety_function = models.ForeignKey(
        SafetyFunction, on_delete=models.SET_NULL, null=True, blank=True, related_name="measures"
    )

    # Status & Verantwortung
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    responsible_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsible_measures"
    )
    due_date = models.DateField(null=True, blank=True)

    # Verifizierung
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_measures"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.TextField(blank=True, default="")

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_protection_measure"
        verbose_name = "Schutzmaßnahme"
        verbose_name_plural = "Schutzmaßnahmen"
        ordering = ["category", "title"]

    def __str__(self) -> str:
        return f"[{self.get_category_display()}] {self.title}"

    @property
    def is_safety_device(self) -> bool:
        """Prüft ob Maßnahme eine MSR-Sicherheitsfunktion ist"""
        return self.safety_function is not None
