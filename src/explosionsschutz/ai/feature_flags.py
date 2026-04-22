# src/explosionsschutz/ai/feature_flags.py
"""
Feature-Flags für KI-Augmentierung (ADR-018).

Nutzt Organization.settings JSONField — keine neue DB-Spalte.
Globaler Kill-Switch via Django-Setting AI_FEATURES_GLOBAL_ENABLED.
"""

import logging
from uuid import UUID

from django.conf import settings

logger = logging.getLogger(__name__)

AI_FEATURES_SETTINGS_KEY = "ai_features_enabled"


def ai_enabled_for_tenant(tenant_id: UUID | str) -> bool:
    """Prüft ob KI-Features für diesen Tenant aktiv und global freigeschaltet sind.

    Zwei-Stufen-Check:
    1. Globaler Kill-Switch: settings.AI_FEATURES_GLOBAL_ENABLED
    2. Tenant-spezifische Freischaltung: Organization.settings["ai_features_enabled"]
    """
    if not getattr(settings, "AI_FEATURES_GLOBAL_ENABLED", False):
        return False

    try:
        from tenancy.models import Organization

        org = Organization.objects.filter(tenant_id=tenant_id).only("settings").first()
        if not org:
            logger.warning("ai_enabled_for_tenant: no org found for tenant_id=%s", tenant_id)
            return False
        return bool(org.settings.get(AI_FEATURES_SETTINGS_KEY, False))
    except Exception:
        logger.exception("ai_enabled_for_tenant: unexpected error for tenant_id=%s", tenant_id)
        return False
