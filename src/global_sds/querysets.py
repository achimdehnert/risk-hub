# src/global_sds/querysets.py
"""QuerySets für Global SDS Library (ADR-012)."""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class SdsRevisionQuerySet(models.QuerySet):
    """Custom QuerySet für globale SDS-Revisionen."""

    def visible_for_tenant(
        self,
        tenant_id: uuid.UUID | str,
    ) -> SdsRevisionQuerySet:
        """
        VERIFIED/SUPERSEDED: global sichtbar (alle Tenants).
        PENDING/REJECTED: nur für den hochladenden Tenant.
        """
        from global_sds.models import GlobalSdsRevision

        return self.filter(
            Q(
                status__in=[
                    GlobalSdsRevision.Status.VERIFIED,
                    GlobalSdsRevision.Status.SUPERSEDED,
                ]
            )
            | Q(
                status=GlobalSdsRevision.Status.PENDING,
                uploaded_by_tenant_id=str(tenant_id),
            )
        )

    def verified(self) -> SdsRevisionQuerySet:
        """Nur verifizierte Revisionen."""
        from global_sds.models import GlobalSdsRevision

        return self.filter(status=GlobalSdsRevision.Status.VERIFIED)

    def current(self) -> SdsRevisionQuerySet:
        """Aktuell gültige Revisionen (verifiziert, nicht abgelöst)."""
        from global_sds.models import GlobalSdsRevision

        return self.filter(
            status=GlobalSdsRevision.Status.VERIFIED,
            superseded_by__isnull=True,
        )

    def for_substance(self, substance_id: int) -> SdsRevisionQuerySet:
        """Revisionen einer bestimmten Substanz."""
        return self.filter(substance_id=substance_id)


class SdsUsageQuerySet(models.QuerySet):
    """Custom QuerySet für tenant-spezifische SDS-Nutzung (ADR-012 §5.5)."""

    def for_tenant(self, tenant_id: uuid.UUID | str) -> SdsUsageQuerySet:
        """Filter auf einen bestimmten Tenant."""
        return self.filter(tenant_id=str(tenant_id))

    def requiring_action(self) -> SdsUsageQuerySet:
        """Einträge die Handlungsbedarf haben (Review, Update, Freigabe)."""
        return self.filter(
            status__in=[
                "REVIEW_REQUIRED",
                "UPDATE_AVAILABLE",
                "PENDING_APPROVAL",
            ]
        )

    def overdue(self) -> SdsUsageQuerySet:
        """Einträge deren review_deadline überschritten ist."""
        return self.filter(
            review_deadline__lt=timezone.now().date(),
            status__in=["REVIEW_REQUIRED", "UPDATE_AVAILABLE"],
        )

    def with_pending_update(self) -> SdsUsageQuerySet:
        """Einträge mit ausstehender neuer Revision."""
        return self.filter(pending_update_revision__isnull=False)

    def active(self) -> SdsUsageQuerySet:
        """Nur aktive (freigegebene) Nutzungen."""
        return self.filter(status="ACTIVE")
