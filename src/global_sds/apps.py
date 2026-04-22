# src/global_sds/apps.py
"""Django App Configuration für Global SDS Library (ADR-012)."""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class GlobalSdsConfig(AppConfig):
    """Globale Gefahrstoff-Stammdaten — tenant-übergreifend."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "global_sds"
    verbose_name = "Globale SDS-Bibliothek"

    def ready(self) -> None:
        """Register enrichment providers (ADR-169)."""
        self._register_enrichment_providers()

    @staticmethod
    def _register_enrichment_providers() -> None:
        """Register GESTIS + PubChem providers in the default registry."""
        try:
            from enrichment import default_registry
            from enrichment.providers.gestis import GESTISProvider
            from enrichment.providers.pubchem import PubChemProvider

            default_registry.register("substance", GESTISProvider())
            default_registry.register("substance", PubChemProvider())
            default_registry.register("sds", GESTISProvider())
            default_registry.register("sds", PubChemProvider())
            logger.info("Enrichment providers registered: GESTIS + PubChem (ADR-169)")
        except ImportError:
            logger.warning(
                "iil-enrichment not installed — SDS enrichment unavailable. "
                "Install: pip install iil-enrichment[gestis,pubchem]"
            )
