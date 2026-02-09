# substances/services/substance_service.py
"""Service für Gefahrstoff-Operationen."""

from typing import Optional
from uuid import UUID

from django.db import transaction

from permissions.authz import require_permission
from substances.models import (
    Substance,
    SdsRevision,
    Identifier,
)


class SubstanceService:
    """Service für Gefahrstoff-CRUD und -Operationen."""

    @staticmethod
    def get_by_id(
        substance_id: UUID,
        tenant_id: UUID
    ) -> Optional[Substance]:
        """Holt Gefahrstoff nach ID."""
        require_permission("substance.view")
        try:
            return Substance.objects.select_related(
                "manufacturer", "supplier"
            ).prefetch_related(
                "identifiers", "sds_revisions"
            ).get(id=substance_id, tenant_id=tenant_id)
        except Substance.DoesNotExist:
            return None

    @staticmethod
    def get_by_cas(
        cas_number: str,
        tenant_id: UUID
    ) -> Optional[Substance]:
        """Holt Gefahrstoff nach CAS-Nummer."""
        require_permission("substance.view")
        try:
            identifier = Identifier.objects.select_related(
                "substance"
            ).get(
                id_type="cas",
                id_value=cas_number,
                tenant_id=tenant_id
            )
            return identifier.substance
        except Identifier.DoesNotExist:
            return None

    @staticmethod
    def search(
        query: str,
        tenant_id: UUID,
        limit: int = 20
    ) -> list[Substance]:
        """Sucht Gefahrstoffe nach Name, Handelsname oder CAS."""
        require_permission("substance.view")
        from django.db.models import Q

        return list(
            Substance.objects.filter(
                Q(tenant_id=tenant_id) & (
                    Q(name__icontains=query) |
                    Q(trade_name__icontains=query) |
                    Q(identifiers__id_value__icontains=query)
                )
            ).distinct()[:limit]
        )

    @staticmethod
    @transaction.atomic
    def create_with_sds(
        tenant_id: UUID,
        created_by: UUID,
        name: str,
        sds_data: dict,
        **kwargs
    ) -> Substance:
        """Erstellt Gefahrstoff mit initialer SDS-Revision."""
        require_permission("substance.create")
        substance = Substance.objects.create(
            tenant_id=tenant_id,
            created_by=created_by,
            name=name,
            **kwargs
        )

        if sds_data:
            SdsRevision.objects.create(
                tenant_id=tenant_id,
                created_by=created_by,
                substance=substance,
                revision_number=1,
                **sds_data
            )

        return substance

    @staticmethod
    def get_ex_relevant_data(substance: Substance) -> dict:
        """
        Extrahiert Ex-Schutz-relevante Daten aus einem Gefahrstoff.

        Returns:
            dict mit Feldern für Zonenberechnung und Geräteklassifizierung
        """
        current_sds = substance.current_sds

        return {
            "substance_id": str(substance.id),
            "substance_name": substance.name,
            "cas_number": substance.cas_number,
            "flash_point_c": substance.flash_point_c,
            "ignition_temperature_c": substance.ignition_temperature_c,
            "lower_explosion_limit": substance.lower_explosion_limit,
            "upper_explosion_limit": substance.upper_explosion_limit,
            "temperature_class": substance.temperature_class,
            "explosion_group": substance.explosion_group,
            "vapor_density": substance.vapor_density,
            "sds_revision": current_sds.revision_number if current_sds else None,
            "sds_date": (
                current_sds.revision_date.isoformat()
                if current_sds else None
            ),
            "h_statements": (
                [h.code for h in current_sds.hazard_statements.all()]
                if current_sds else []
            ),
            "pictograms": (
                [p.code for p in current_sds.pictograms.all()]
                if current_sds else []
            ),
        }
