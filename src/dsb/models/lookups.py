"""Globale Referenzdaten (kein tenant_id, ADR-038 R2-F13)."""

import uuid

from django.db import models


class Category(models.Model):
    """Datenkategorie (Art. 9 DSGVO). Global, nicht tenant-spezifisch."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)
    is_special_category = models.BooleanField(
        default=False,
        help_text="Art. 9 besondere Kategorie (Gesundheit, Religion, etc.)",
    )

    class Meta:
        db_table = "dsb_category"
        verbose_name = "Datenkategorie"
        verbose_name_plural = "Datenkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class SubjectGroup(models.Model):
    """Lookup: Betroffenengruppe (z.B. Besch\u00e4ftigte, Kunden, Patienten)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_subject_group"
        verbose_name = "Betroffenengruppe"
        verbose_name_plural = "Betroffenengruppen"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class Recipient(models.Model):
    """Lookup: Empf\u00e4ngerkategorie (Art. 30 Abs. 1 lit. d DSGVO)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=200)

    class Meta:
        db_table = "dsb_recipient"
        verbose_name = "Empf\u00e4ngerkategorie"
        verbose_name_plural = "Empf\u00e4ngerkategorien"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class Purpose(models.Model):
    """Lookup: Verarbeitungszweck (Art. 30 Abs. 1 lit. b DSGVO)."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)

    class Meta:
        db_table = "dsb_purpose"
        verbose_name = "Verarbeitungszweck"
        verbose_name_plural = "Verarbeitungszwecke"
        ordering = ["key"]

    def __str__(self) -> str:
        return self.label


class TomCategory(models.Model):
    """Stammdaten-Katalog f\u00fcr TOM (Art. 32 DSGVO).

    Globale Vorlagen, z.B. 'Verschl\u00fcsselung', 'Zugriffsbeschr\u00e4nkung',
    'Schulung'. Tenant-spezifische Instanzen verweisen hierauf.
    """

    class MeasureType(models.TextChoices):
        TECHNICAL = "technical", "Technisch"
        ORGANIZATIONAL = "organizational", "Organisatorisch"
        AVV = "avv", "Auftragsverarbeitung (AVV)"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)
    measure_type = models.CharField(
        max_length=20,
        choices=MeasureType.choices,
        help_text="Art der Ma\u00dfnahme",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Beschreibung / Best Practice",
    )

    class Meta:
        db_table = "dsb_tom_category"
        verbose_name = "TOM-Katalog (Stammdaten)"
        verbose_name_plural = "TOM-Katalog (Stammdaten)"
        ordering = ["measure_type", "key"]

    def __str__(self) -> str:
        return f"[{self.get_measure_type_display()}] {self.label}"


class StandardRetentionPeriod(models.Model):
    """Stammdaten: Gesetzliche Aufbewahrungsfristen.

    Globaler Katalog wiederverwendbarer L\u00f6schfristen,
    z.B. '\u00a7 257 HGB \u2014 10 Jahre', '\u00a7 147 AO \u2014 10 Jahre'.
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    key = models.CharField(max_length=80, unique=True)
    label = models.CharField(max_length=300)
    legal_reference = models.CharField(
        max_length=200,
        help_text="Gesetzliche Grundlage (z.B. '\u00a7 257 HGB')",
    )
    period = models.CharField(
        max_length=100,
        help_text="Frist (z.B. '10 Jahre', 'unverz\u00fcglich')",
    )
    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:
        db_table = "dsb_standard_retention"
        verbose_name = "L\u00f6schfrist (Stammdaten)"
        verbose_name_plural = "L\u00f6schfristen (Stammdaten)"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.label} ({self.period})"
