# src/explosionsschutz/models/dust.py
"""
Staub-spezifische Stoff-Kenngrößen als OneToOne-Erweiterung auf Substance.

DustSubstanceProperties: Nur befüllt wenn Substance.phase = DUST.
Enthält Glimmtemperatur, KSt, Pmax, Brennzahl, Korngröße, Feuchte.

Bestehende Alt-Felder auf Substance (staubexplosionsklasse_kst,
glimmtemperatur_c) werden per Datenmigration hierher migriert (ADR-044 Phase 2).

ADR-044 Phase 1B.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_tenancy.managers import TenantManager


class DustSubstanceProperties(models.Model):
    """
    Erweiterungsmodell für Staub-spezifische Ex-Schutz-Kenngrößen.

    OneToOne auf substances.Substance. Nur anlegen wenn Substance.phase = DUST.

    Migrationshinweis (ADR-044 Phase 2):
    - Substance.staubexplosionsklasse_kst → dust_class + kst_bar_m_per_s
    - Substance.glimmtemperatur_c → glow_temperature_c
    Alt-Felder werden deprecated, nach 6 Monaten entfernt.
    """

    class DustClass(models.TextChoices):
        ST0 = "St0", "St 0 (inert, nicht explosionsfähig)"
        ST1 = "St1", "St 1 (schwach explosiv, KSt ≤ 200 bar·m/s)"
        ST2 = "St2", "St 2 (mittel explosiv, KSt 200–300 bar·m/s)"
        ST3 = "St3", "St 3 (stark explosiv, KSt > 300 bar·m/s)"

    substance = models.OneToOneField(
        "substances.Substance",
        on_delete=models.CASCADE,
        related_name="dust_properties",
    )

    glow_temperature_c = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Glimmtemperatur Staubschicht 5 mm in °C (DIN EN 50281-2-1)",
    )
    kst_bar_m_per_s = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="KSt-Wert: Höchstwert des norm. Druckanstiegs in bar·m/s (ASTM E1226)",
    )
    dust_class = models.CharField(
        max_length=3,
        choices=DustClass.choices,
        blank=True,
        help_text="Staubexplosionsklasse abgeleitet aus KSt (VDI 3673)",
    )
    p_max_bar = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Maximaler Explosionsdruck in bar (ASTM E1226)",
    )
    burn_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        help_text="Brennzahl BZ 1–6 nach VDI 2263 (1=kaum brennbar, 6=leicht entzündlich)",
    )
    particle_size_median_um = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Korngröße Median d50 in μm (Siebanalyse). Ex-relevant typisch < 400 μm",
    )
    moisture_influence_text = models.TextField(
        blank=True,
        help_text="Einfluss der Feuchte auf Zündempfindlichkeit und Explosionsfähigkeit",
    )

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Kopie von substance.tenant_id für direkte RLS-Kompatibilität",
    )

    objects = TenantManager()

    class Meta:
        db_table = "ex_dust_substance_properties"
        verbose_name = "Staub-Kenngrößen"
        verbose_name_plural = "Staub-Kenngrößen"

    def __str__(self) -> str:
        name = self.substance.name if self.substance_id else "?"
        dust_class = f" ({self.dust_class})" if self.dust_class else ""
        return f"Staub-Kenngrößen: {name}{dust_class}"

    @property
    def is_explosible(self) -> bool:
        """St0 ist inert — kein Ex-Risiko durch Staub."""
        return self.dust_class != self.DustClass.ST0
