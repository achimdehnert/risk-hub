"""Deletion — Löschprotokolle (Art. 17 DSGVO)."""

import uuid

from django.db import models

from .lookups import Category
from .mandate import Mandate
from .vvt import ProcessingActivity


class DeletionLog(models.Model):
    """Löschprotokoll gemäß Art. 17 DSGVO."""

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )
    tenant_id = models.UUIDField(db_index=True)
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="deletion_logs",
    )
    processing_activity = models.ForeignKey(
        ProcessingActivity,
        on_delete=models.PROTECT,
        related_name="deletion_logs",
    )
    requested_at = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    data_category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        help_text="Gelöschte Datenkategorie",
    )
    record_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Anzahl gelöschter Datensätze",
    )
    method = models.CharField(
        max_length=100,
        help_text="Löschmethode (z.B. 'DB DELETE', 'Aktenvernichtung')",
    )
    confirmed_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="User-ID des Bestätigenden (lose Kopplung)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dsb_deletion_log"
        verbose_name = "Löschprotokoll"
        verbose_name_plural = "Löschprotokolle"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "mandate"],
                name="idx_dsb_del_tenant_mandate",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Löschung {self.data_category}"
            f" @ {self.requested_at:%Y-%m-%d}"
        )
