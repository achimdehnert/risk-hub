# src/global_sds/querysets.py
"""QuerySets für Global SDS Library (ADR-012)."""

import uuid

from django.db import models
from django.db.models import Q


class SdsRevisionQuerySet(models.QuerySet):
    """Custom QuerySet für globale SDS-Revisionen."""

    def visible_for_tenant(
        self,
        tenant_id: uuid.UUID | str,
    ) -> "SdsRevisionQuerySet":
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

    def verified(self) -> "SdsRevisionQuerySet":
        """Nur verifizierte Revisionen."""
        from global_sds.models import GlobalSdsRevision

        return self.filter(status=GlobalSdsRevision.Status.VERIFIED)

    def current(self) -> "SdsRevisionQuerySet":
        """Aktuell gültige Revisionen (verifiziert, nicht abgelöst)."""
        from global_sds.models import GlobalSdsRevision

        return self.filter(
            status=GlobalSdsRevision.Status.VERIFIED,
            superseded_by__isnull=True,
        )

    def for_substance(self, substance_id: int) -> "SdsRevisionQuerySet":
        """Revisionen einer bestimmten Substanz."""
        return self.filter(substance_id=substance_id)
