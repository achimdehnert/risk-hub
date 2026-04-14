# src/explosionsschutz/models/equipment.py
"""
Betriebsmittel, Prüfungen und ATEX-Eignungsprüfungen.

Equipment: Konkretes Ex-geschütztes Betriebsmittel
Inspection: Prüfung nach BetrSichV
EquipmentATEXCheck: Archivierter ATEX-Eignungsnachweis
"""

import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django_tenancy.managers import TenantManager

from .concept import Area
from .master_data import EquipmentType
from .zone import ZoneDefinition

User = get_user_model()

class Equipment(models.Model):
    """Konkretes Ex-geschütztes Betriebsmittel"""

    class Status(models.TextChoices):
        ACTIVE = "active", "In Betrieb"
        INACTIVE = "inactive", "Außer Betrieb"
        MAINTENANCE = "maintenance", "In Wartung"
        DECOMMISSIONED = "decommissioned", "Stillgelegt"

    tenant_id = models.UUIDField(db_index=True)

    equipment_type = models.ForeignKey(
        EquipmentType, on_delete=models.PROTECT, related_name="instances"
    )
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="equipment")
    zone = models.ForeignKey(
        ZoneDefinition, on_delete=models.SET_NULL, null=True, blank=True, related_name="equipment"
    )

    serial_number = models.CharField(max_length=100, blank=True, default="")
    asset_number = models.CharField(
        max_length=100, blank=True, default="", help_text="Interne Anlagennummer"
    )
    location_detail = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Genauer Standort (z.B. 'Halle 3, Ebene 2')",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    installation_date = models.DateField(null=True, blank=True)

    last_inspection_date = models.DateField(null=True, blank=True)
    next_inspection_date = models.DateField(null=True, blank=True)
    inspection_interval_months = models.PositiveIntegerField(
        null=True, blank=True, help_text="Überschreibt Standard-Intervall des Typs"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_equipment"
        verbose_name = "Betriebsmittel"
        verbose_name_plural = "Betriebsmittel"
        indexes = [
            models.Index(
                fields=["tenant_id", "next_inspection_date"],
                name="idx_equip_tenant_inspect",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.equipment_type} ({self.asset_number or self.serial_number or 'N/A'})"

    @property
    def is_inspection_due(self) -> bool:
        """Prüft ob Inspektion fällig"""
        from django.utils import timezone

        if not self.next_inspection_date:
            return False
        return self.next_inspection_date <= timezone.now().date()

    @property
    def is_suitable_for_zone(self) -> bool:
        """Prüft ob Gerätekategorie zur Zone passt"""
        if not self.zone:
            return True

        required = self.zone.required_equipment_category
        actual = self.equipment_type.atex_category

        if required == "non_ex":
            return True
        if not actual:
            return False

        # Höhere Kategorie ist immer zulässig
        category_order = {"1G": 1, "2G": 2, "3G": 3, "1D": 1, "2D": 2, "3D": 3}
        return category_order.get(actual, 99) <= category_order.get(required, 0)

class Inspection(models.Model):
    """Prüfung eines Betriebsmittels nach BetrSichV"""

    class InspectionType(models.TextChoices):
        INITIAL = "initial", "Erstprüfung"
        PERIODIC = "periodic", "Wiederkehrende Prüfung"
        SPECIAL = "special", "Sonderprüfung"
        REPAIR = "repair", "Prüfung nach Instandsetzung"

    class Result(models.TextChoices):
        PASSED = "passed", "Bestanden"
        PASSED_WITH_NOTES = "passed_notes", "Bestanden mit Hinweisen"
        FAILED = "failed", "Nicht bestanden"
        PENDING = "pending", "Ausstehend"

    tenant_id = models.UUIDField(db_index=True)

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="inspections")

    inspection_type = models.CharField(
        max_length=20, choices=InspectionType.choices, default=InspectionType.PERIODIC
    )
    inspection_date = models.DateField()
    inspector_name = models.CharField(max_length=200)
    inspector_organization = models.CharField(
        max_length=200, blank=True, default="", help_text="z.B. ZÜS, befähigte Person"
    )

    result = models.CharField(max_length=20, choices=Result.choices, default=Result.PENDING)
    findings = models.TextField(blank=True, default="")
    recommendations = models.TextField(blank=True, default="")

    certificate_number = models.CharField(max_length=100, blank=True, default="")
    document_id = models.UUIDField(null=True, blank=True, help_text="FK zu documents.Document")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_inspection"
        verbose_name = "Prüfung"
        verbose_name_plural = "Prüfungen"
        ordering = ["-inspection_date"]

    def __str__(self) -> str:
        return f"{self.get_inspection_type_display()} - {self.equipment} ({self.inspection_date})"

    # NOTE: Equipment inspection date updates are handled in
    # explosionsschutz.services.create_inspection() to keep
    # the model free of hidden side-effects (F-07).

class EquipmentATEXCheck(models.Model):
    """
    Archivierter ATEX-Eignungsnachweis für ein Betriebsmittel.
    Wird explizit in create_equipment_with_atex_check() angelegt (kein Signal).
    """

    tenant_id = models.UUIDField(db_index=True)

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT,
        related_name="atex_checks",
    )
    is_suitable = models.BooleanField()
    result = models.JSONField(
        help_text="Vollständiges ATEXCheckResult (dataclasses.asdict())",
    )
    riskfw_version = models.CharField(max_length=20)
    checked_at = models.DateTimeField(auto_now_add=True)

    objects = TenantManager()

    class Meta:
        db_table = "ex_equipment_atex_check"
        verbose_name = "ATEX-Eignungsprüfung"
        verbose_name_plural = "ATEX-Eignungsprüfungen"
        ordering = ["-checked_at"]
        default_permissions = ("add", "view")

    def __str__(self) -> str:
        status = "geeignet" if self.is_suitable else "NICHT geeignet"
        return f"{self.equipment} — {status} ({self.checked_at:%Y-%m-%d})"
