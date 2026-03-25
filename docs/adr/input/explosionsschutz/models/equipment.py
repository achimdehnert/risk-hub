"""
Betriebsmittel und Prüfungen nach BetrSichV §§14–16.
Entspricht Kapitel 5 (Arbeitsmittel) und Kapitel 9 (Wirksamkeitsprüfungen).
"""
from __future__ import annotations

import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models


class Equipment(models.Model):
    """
    Betriebsmittel / Arbeitsmittel im explosionsgefährdeten Bereich.

    ATEX-Eignung wird gegen die Zone(n) geprüft.
    Prüffristen nach BetrSichV §§14–16.
    """

    class InspectionStatus(models.TextChoices):
        CURRENT = "current", "Prüfung aktuell"
        DUE_SOON = "due_soon", "Prüfung fällig (< 30 Tage)"
        OVERDUE = "overdue", "Prüfung überfällig"
        NOT_REQUIRED = "not_required", "Keine Prüfpflicht"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    area = models.ForeignKey(
        "concept.Area",
        on_delete=models.PROTECT,
        related_name="equipment",
    )
    # Zone(n), in denen das Gerät eingesetzt wird
    zones = models.ManyToManyField(
        "zone.ZoneDefinition",
        blank=True,
        related_name="equipment",
    )
    equipment_type = models.ForeignKey(
        "master_data.EquipmentType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="equipment",
    )

    # Identifikation
    inventory_number = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    location_detail = models.CharField(
        max_length=300,
        blank=True,
        help_text="Genauer Aufstellungsort im Bereich",
    )

    # ATEX-Kennzeichnung (aus EquipmentType oder manuell überschrieben)
    atex_marking_override = models.CharField(
        max_length=100,
        blank=True,
        help_text="Manuelle ATEX-Kennzeichnung falls vom Typ abweichend",
    )
    manufacturer = models.CharField(max_length=200, blank=True)
    year_of_manufacture = models.PositiveSmallIntegerField(null=True, blank=True)
    year_of_installation = models.PositiveSmallIntegerField(null=True, blank=True)

    # Prüffristen
    first_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(null=True, blank=True)
    inspection_interval_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Überschreibt den Typ-Standard",
    )

    is_active = models.BooleanField(default=True)
    decommission_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ex_equipment"
        ordering = ["area", "name"]

    def __str__(self) -> str:
        inv = f" [{self.inventory_number}]" if self.inventory_number else ""
        return f"{self.name}{inv}"

    @property
    def atex_marking(self) -> str:
        if self.atex_marking_override:
            return self.atex_marking_override
        if self.equipment_type:
            return self.equipment_type.atex_marking
        return "—"

    @property
    def inspection_status(self) -> "Equipment.InspectionStatus":
        if not self.next_inspection_date:
            return self.InspectionStatus.NOT_REQUIRED
        today = date.today()
        delta = (self.next_inspection_date - today).days
        if delta < 0:
            return self.InspectionStatus.OVERDUE
        if delta <= 30:
            return self.InspectionStatus.DUE_SOON
        return self.InspectionStatus.CURRENT

    def clean(self) -> None:
        """Validiert ATEX-Eignung gegen zugeordnete Zonen."""
        if self.equipment_type and self.pk:
            for zone in self.zones.all():
                if not self.equipment_type.is_suitable_for_zone(zone.zone_type):
                    raise ValidationError(
                        f"Betriebsmittel {self.equipment_type} ist nicht geeignet "
                        f"für Zone {zone.zone_type} ({zone.name}). "
                        f"Kategorie {self.equipment_type.atex_category} nicht ausreichend."
                    )


class Inspection(models.Model):
    """
    Prüfprotokoll nach BetrSichV §§14–16.

    Sichtprüfung / Nahprüfung / Eingehende Prüfung / ZÜS-Prüfung.
    approved_by_id als UUID (kein FK!) – Compliance-Datensicherheit.
    """

    class InspectionType(models.TextChoices):
        VISUAL = "visual", "Sichtprüfung (§15 BetrSichV)"
        CLOSE = "close", "Nahprüfung (§15 BetrSichV)"
        DETAILED = "detailed", "Eingehende Prüfung (§15 BetrSichV)"
        ZUS = "zus", "Prüfung durch ZÜS (§16 BetrSichV)"
        EFFECTIVENESS = "effectiveness", "Wirksamkeitsprüfung (§3 BetrSichV)"

    class Result(models.TextChoices):
        PASSED = "passed", "Bestanden"
        PASSED_WITH_REMARKS = "passed_with_remarks", "Bestanden mit Auflagen"
        FAILED = "failed", "Nicht bestanden"
        POSTPONED = "postponed", "Verschoben"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,  # Compliance: Prüfnachweis niemals kaskadengelöscht
        related_name="inspections",
    )
    inspection_type = models.CharField(max_length=20, choices=InspectionType.choices)
    scheduled_date = models.DateField()

    # Durchführung
    performed_date = models.DateField(null=True, blank=True)
    performed_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="UUID des Prüfers (intern)",
    )
    performed_by_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name des Prüfers (Snapshot)",
    )
    external_inspector = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name der externen Prüforganisation (ZÜS, TÜV, BG …)",
    )

    # Ergebnis
    result = models.CharField(
        max_length=30, choices=Result.choices, null=True, blank=True
    )
    findings = models.TextField(blank=True, help_text="Festgestellte Mängel")
    corrective_actions = models.TextField(
        blank=True, help_text="Festgelegte Abstellmaßnahmen"
    )

    # Dokument
    protocol = models.ForeignKey(
        "documents.Document",
        null=True,
        blank=True,
        on_delete=models.PROTECT,  # Prüfprotokoll niemals löschen
        related_name="inspection_protocols",
    )

    # Folgeprüfung
    next_inspection_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_inspection"
        ordering = ["-scheduled_date"]

    def __str__(self) -> str:
        return (
            f"{self.equipment.name} – {self.get_inspection_type_display()} "
            f"({self.scheduled_date})"
        )


class VerificationDocument(models.Model):
    """
    Nachweis-/Begleitdokument zu einem Ex-Konzept.
    Verifikationsberichte, Prüfbescheinigungen, MSR-Protokolle, etc.
    Entspricht Kapitel "Anlagen / mitgeltende Dokumente".
    """

    class DocumentType(models.TextChoices):
        VERIFICATION_REPORT = "verification", "Verifikationsbericht"
        ZUS_CERTIFICATE = "zus_cert", "ZÜS-Prüfbescheinigung"
        TIGHTNESS_TEST = "tightness", "Dichtheitsnachweis"
        MSR_ASSESSMENT = "msr", "MSR-Bewertung (TRGS 725)"
        HAZARD_ASSESSMENT = "hazard_assessment", "Gefährdungsbeurteilung"
        OPERATING_INSTRUCTION = "operating_inst", "Betriebsanweisung (§14 GefStoffV)"
        PHOTO = "photo", "Fotodokumentation"
        OTHER = "other", "Sonstiges"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField(db_index=True)

    concept = models.ForeignKey(
        "concept.ExplosionConcept",
        on_delete=models.PROTECT,  # Compliance: Nachweise nicht verlieren
        related_name="verification_documents",
    )
    title = models.CharField(max_length=300)
    document_type = models.CharField(
        max_length=30, choices=DocumentType.choices
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.PROTECT,
        related_name="verification_refs",
    )
    issuer = models.CharField(
        max_length=200,
        blank=True,
        help_text="Ausstellende Organisation (z.B. TÜV Süd)",
    )
    issued_at = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ex_verification_document"
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"{self.get_document_type_display()}: {self.title}"
