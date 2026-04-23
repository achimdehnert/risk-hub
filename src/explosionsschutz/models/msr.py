# src/explosionsschutz/models/msr.py
"""
MSR-Sicherheitsfunktionen und TRGS 725 Klassifizierung.

TrgsK725Mapping: Seedbare PL→K-Mapping-Tabelle (Phase 1A).
MsrSafetyFunction: MSR-Sicherheitsfunktion pro Konzept (Phase 3A).

ADR-044 Phase 1A + Phase 3A.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_tenancy.managers import TenantManager


class MsrRealizationType(models.TextChoices):
    TECHNICAL = "TECH", "Technische MSR-Einrichtung (PL nach EN ISO 13849-1)"
    ORGANIZATIONAL = "ORG", "Organisatorisches Verfahren"
    COMBINED = "COMB", "Kombiniert technisch und organisatorisch"


class TrgsK725Mapping(models.Model):
    """
    Seedbare Referenztabelle: Performance Level → K-Klassifizierungsstufe.

    Quelle: TRGS 725 Tabelle 3 (EN ISO 13849-1 PL → TRGS 725 K-Stufe).

    Global, tenant-unabhängig. TRGS-Aktualisierungen erfordern nur eine
    Datenmigration, keinen Code-Release. Historische Versionen bleiben über
    applicable_from / applicable_until nachvollziehbar.

    Aktuell gültige Einträge haben applicable_until = NULL.

    Seeded via Management-Command `seed_trgs_k725_mapping`.

    Aktuell gültige Werte (TRGS 725, März 2024):
    - PL a → K3
    - PL b → K2
    - PL c → K2
    - PL d → K1
    - PL e → K1
    """

    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"

    performance_level = models.CharField(
        max_length=1,
        choices=PerformanceLevel.choices,
    )
    technical_k_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="K-Klassifizierungsstufe 1 (hoch) bis 3 (niedrig) nach TRGS 725 Tabelle 3",
    )
    applicable_from = models.DateField(
        help_text="Gültig ab diesem TRGS-Ausgabedatum",
    )
    applicable_until = models.DateField(
        null=True,
        blank=True,
        help_text="Gültig bis (NULL = aktuell gültig)",
    )
    trgs_version_note = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'TRGS 725, Ausgabe März 2024'",
    )

    class Meta:
        db_table = "ex_trgs_k725_mapping"
        verbose_name = "TRGS 725 PL→K Mapping"
        verbose_name_plural = "TRGS 725 PL→K Mappings"
        ordering = ["-applicable_from", "performance_level"]
        constraints = [
            models.UniqueConstraint(
                fields=["performance_level", "applicable_from"],
                name="uq_trgs_k725_pl_version",
            ),
        ]

    def __str__(self) -> str:
        note = f" ({self.trgs_version_note})" if self.trgs_version_note else ""
        return f"PL {self.performance_level} → K{self.technical_k_level}{note}"

    @classmethod
    def current_k_for_pl(cls, performance_level: str) -> int | None:
        """Aktuell gültige K-Stufe für einen PL-Wert (applicable_until=NULL)."""
        mapping = cls.objects.filter(
            performance_level=performance_level,
            applicable_until__isnull=True,
        ).first()
        return mapping.technical_k_level if mapping else None


class MsrSafetyFunction(models.Model):
    """
    Sicherheitsfunktion nach TRGS 725 / EN ISO 13849-1.

    Kernmodell der quantitativen MSR-Bewertung. Verknüpft Performance Level (PL)
    mit der TRGS 725 K-Klassifizierungsstufe. K-Wert aus TrgsK725Mapping
    abrufbar über `TrgsK725Mapping.current_k_for_pl(self.performance_level)`.

    zone_without_msr: Zoneneinteilung VOR der MSR-Maßnahme (FK statt CharField).
    target_zone: Zoneneinteilung NACH der MSR-Maßnahme (reduzierte Klasse).
    """

    class PerformanceLevel(models.TextChoices):
        PL_A = "a", "PL a"
        PL_B = "b", "PL b"
        PL_C = "c", "PL c"
        PL_D = "d", "PL d"
        PL_E = "e", "PL e"

    class VerificationMethod(models.TextChoices):
        SISTEMA = "SISTEMA", "SISTEMA (BGIA Tool)"
        MANUAL = "MANUAL", "Manuelle FMEA"
        EXTERNAL = "EXTERNAL", "Externer Prüfbericht (zPbP / ZÜS)"

    concept = models.ForeignKey(
        "explosionsschutz.ExplosionConcept",
        on_delete=models.PROTECT,
        related_name="safety_functions",
    )
    function_name = models.CharField(max_length=200)
    realization_type = models.CharField(
        max_length=10,
        choices=MsrRealizationType.choices,
    )

    performance_level = models.CharField(
        max_length=1,
        choices=PerformanceLevel.choices,
        blank=True,
        help_text="Required Performance Level nach EN ISO 13849-1 (nur bei TECH/COMB)",
    )
    verification_report_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="z.B. 'Marquis-AF-23-0135-001-1' (Prüfberichtnummer)",
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VerificationMethod.choices,
        blank=True,
    )

    technical_k_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="K=1/2/3 rein technisch aus PL abgeleitet (via TrgsK725Mapping)",
    )
    organizational_contribution_text = models.TextField(
        blank=True,
        help_text="Beschreibung des organisatorischen Anteils bei realization_type=ORG/COMB",
    )
    resulting_k_level = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="K=1/2/3 final (technisch + organisatorisch kombiniert, TRGS 725 Tabelle 3)",
    )

    zone_without_msr = models.ForeignKey(
        "explosionsschutz.ZoneDefinition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="msr_functions_initial_zone",
        help_text="Zoneneinteilung vor der MSR-Maßnahme",
    )
    target_zone = models.ForeignKey(
        "explosionsschutz.ZoneDefinition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="msr_functions_target_zone",
        help_text="Angestrebte Zoneneinteilung nach MSR-Maßnahme",
    )

    evaluation_narrative = models.TextField(
        help_text="Freitext-Begründung der MSR-Bewertung (Pflichtfeld)",
    )

    tenant_id = models.UUIDField(db_index=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_msr_safety_function"
        verbose_name = "MSR-Sicherheitsfunktion"
        verbose_name_plural = "MSR-Sicherheitsfunktionen"

    def __str__(self) -> str:
        pl = f" PL {self.performance_level}" if self.performance_level else ""
        k = f" → K{self.resulting_k_level}" if self.resulting_k_level else ""
        return f"{self.function_name}{pl}{k}"

    def sync_technical_k_level(self) -> None:
        """Übernimmt K-Wert aus TrgsK725Mapping für den aktuellen PL-Wert."""
        if self.performance_level:
            self.technical_k_level = TrgsK725Mapping.current_k_for_pl(self.performance_level)
