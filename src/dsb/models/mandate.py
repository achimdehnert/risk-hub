"""Mandate — Betreutes Unternehmen des DSB."""

import uuid

from django.db import models


class Mandate(models.Model):
    """Betreutes Unternehmen des DSB. KEIN Tenant — Subentität."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Aktiv"
        PAUSED = "paused", "Pausiert"
        TERMINATED = "terminated", "Beendet"

    class Industry(models.TextChoices):
        HEALTHCARE = "healthcare", "Gesundheitswesen"
        FINANCE = "finance", "Finanzwesen"
        PUBLIC_SECTOR = "public_sector", "Öffentlicher Dienst"
        EDUCATION = "education", "Bildung"
        IT_TELECOM = "it_telecom", "IT & Telekommunikation"
        MANUFACTURING = "manufacturing", "Produzierendes Gewerbe"
        RETAIL = "retail", "Handel"
        LOGISTICS = "logistics", "Logistik"
        ENERGY = "energy", "Energie"
        OTHER = "other", "Sonstige"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    industry = models.CharField(
        max_length=20,
        choices=Industry.choices,
        blank=True,
        default="",
        help_text="Branche des betreuten Unternehmens",
    )
    employee_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Anzahl Beschäftigte (für Meldepflichten relevant)",
    )
    dsb_appointed_date = models.DateField(
        help_text="Datum der DSB-Bestellung",
    )
    contract_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Vertragsende (NULL = unbefristet)",
    )
    supervisory_authority = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Zuständige Aufsichtsbehörde (z.B. LfDI Baden-Württemberg)",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_by_id = models.UUIDField(null=True, blank=True)
    updated_by_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_mandate"
        verbose_name = "Mandat"
        verbose_name_plural = "Mandate"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_dsb_mandate_tenant_name",
            ),
            models.CheckConstraint(
                check=models.Q(
                    status__in=["active", "paused", "terminated"],
                ),
                name="ck_dsb_mandate_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_dsb_mandate_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return self.name
