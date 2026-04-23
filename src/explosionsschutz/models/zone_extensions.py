# src/explosionsschutz/models/zone_extensions.py
"""
ZoneDefinition-Erweiterungsfelder und ConditionalZoneTrigger.

Neue Felder für ZoneDefinition (werden als AddField-Migration ergänzt):
- atmosphere_form (Wolke/Schicht/Hybrid für Staubzonen)
- zone_condition_type (permanent, messungsgetriggert, tätigkeitsgebunden)
- geometry (strukturierte Geometrie statt Freitext)
- derived_from_clause (FK auf ReferenceStandardClause)

ConditionalZoneTrigger: Separates Modell für nicht-permanente Zonen
(Messwert-Schwellwert oder Tätigkeitsbindung).

Erweiterungsfelder werden via Migration 0005 auf ex_zone_definition addiert.
ConditionalZoneTrigger ist ein neues Modell.

ADR-044 Phase 1C.
"""

from django.db import models
from django_tenancy.managers import TenantManager


class AtmosphereForm(models.TextChoices):
    WOLKE = "WOLKE", "Staubwolke (aufgewirbelt)"
    SCHICHT = "SCHICHT", "Staubschicht (abgelagert)"
    HYBRID = "HYBRID", "Beides relevant (Wolke und Schicht)"


class ZoneConditionType(models.TextChoices):
    PERMANENT = "PERMANENT", "Dauerhaft vorhanden"
    MEASUREMENT_TRIGGERED = "MEAS", "Abhängig von Messung (Gaswarnanlage etc.)"
    ACTIVITY_LINKED = "ACTIVITY", "Tätigkeitsgebunden (Abfüllen, Reinigung etc.)"


class ConditionalZoneTrigger(models.Model):
    """
    Auslöser-Bedingung für nicht-permanente Zonen (zone_condition_type ≠ PERMANENT).

    OneToOne auf ZoneDefinition. Nur anlegen wenn zone_condition_type in
    [MEASUREMENT_TRIGGERED, ACTIVITY_LINKED].

    Beispiele:
    - Gaswarnanlage: measured_variable='H2-Konzentration', threshold_value=10,
      threshold_unit='% UEG', fallback_zone='2'
    - Abfüllvorgang: activity_name='Abfüllen Behälter A', duration_minutes=30
    """

    zone = models.OneToOneField(
        "explosionsschutz.ZoneDefinition",
        on_delete=models.CASCADE,
        related_name="trigger",
    )

    class TriggerType(models.TextChoices):
        MEASUREMENT = "measurement", "Messtechnisch (Gaswarnanlage, Sensor)"
        ACTIVITY = "activity", "Tätigkeitsgebunden (Handlungsanweisung)"
        TIME_SCHEDULE = "time", "Zeitgebunden (Schichtplan)"

    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices,
    )

    measured_variable = models.CharField(
        max_length=100,
        blank=True,
        help_text="z.B. 'H2-Konzentration', 'LEL-Wert am Sensor S-04'",
    )
    threshold_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Schwellwert bei dem die Zone aktiv wird",
    )
    threshold_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="z.B. '% UEG', 'mg/m³', 'Vol.%'",
    )
    fallback_zone = models.CharField(
        max_length=10,
        blank=True,
        help_text="Zone-Klassifikation wenn Trigger nicht aktiv (z.B. 'non_ex', '2')",
    )

    activity_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Bezeichnung der auslösenden Tätigkeit",
    )
    activity_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Typische Dauer der Tätigkeit in Minuten",
    )
    post_activity_clearance_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Abklingzeit nach Tätigkeitsende bevor Zone wieder als inaktiv gilt",
    )

    tenant_id = models.UUIDField(
        db_index=True,
        help_text="Kopie von zone.tenant_id für direkte RLS-Kompatibilität",
    )

    objects = TenantManager()

    class Meta:
        db_table = "ex_conditional_zone_trigger"
        verbose_name = "Zonen-Auslöser"
        verbose_name_plural = "Zonen-Auslöser"

    def __str__(self) -> str:
        zone_name = self.zone.name if self.zone_id else "?"
        return f"Trigger [{self.get_trigger_type_display()}] für Zone: {zone_name}"
