# src/global_sds/services/identity_resolver.py
"""
SdsIdentityResolver — Identitätsauflösung (ADR-012 §5 Stufe 2).

CAS-Lookup (exakt) + Fuzzy Name+Hersteller Matching.
"""

import logging
from dataclasses import dataclass
from difflib import SequenceMatcher

from django.conf import settings

from global_sds.models import GlobalSubstance

logger = logging.getLogger(__name__)

# Konfigurierbare Schwellenwerte (ADR-012 §7.3 N-1)
CONFIDENCE_AUTO_MATCH = getattr(
    settings, "SDS_IDENTITY_AUTO_MATCH_THRESHOLD", 0.95,
)
CONFIDENCE_ASK_USER = getattr(
    settings, "SDS_IDENTITY_ASK_USER_THRESHOLD", 0.70,
)


@dataclass
class IdentityMatch:
    """Ergebnis der Identitätsauflösung."""

    substance: GlobalSubstance | None
    confidence: float
    match_type: str  # "cas_exact", "fuzzy", "none"

    @property
    def is_auto_match(self) -> bool:
        return self.confidence >= CONFIDENCE_AUTO_MATCH

    @property
    def needs_user_confirmation(self) -> bool:
        return (
            CONFIDENCE_ASK_USER
            <= self.confidence
            < CONFIDENCE_AUTO_MATCH
        )

    @property
    def is_new_substance(self) -> bool:
        return self.confidence < CONFIDENCE_ASK_USER


class SdsIdentityResolver:
    """
    Löst die Identität eines hochgeladenen SDS auf.

    1. CAS exact match → confidence 0.98
    2. Fuzzy Name+Hersteller ≥ 0.95 → auto match
    3. Fuzzy 0.70–0.95 → Confirmation-Queue
    4. < 0.70 → neue Substance
    """

    def resolve(
        self,
        cas_number: str | None,
        product_name: str,
        manufacturer_name: str = "",
    ) -> IdentityMatch:
        """Identität auflösen."""
        # Stufe 1: CAS exact match
        if cas_number:
            cas_clean = self._normalize_cas(cas_number)
            match = self._try_cas_match(cas_clean)
            if match:
                return match

        # Stufe 2: Fuzzy Name+Hersteller
        return self._try_fuzzy_match(
            product_name, manufacturer_name,
        )

    def _normalize_cas(self, cas: str) -> str:
        """CAS normalisieren (Leerzeichen, Bindestriche)."""
        return cas.strip().replace(" ", "").replace("‐", "-")

    def _try_cas_match(
        self, cas_number: str,
    ) -> IdentityMatch | None:
        """Exakter CAS-Match."""
        try:
            substance = GlobalSubstance.objects.get(
                cas_number=cas_number,
            )
            logger.info(
                "CAS exact match: %s → %s",
                cas_number, substance.name,
            )
            return IdentityMatch(
                substance=substance,
                confidence=0.98,
                match_type="cas_exact",
            )
        except GlobalSubstance.DoesNotExist:
            return None
        except GlobalSubstance.MultipleObjectsReturned:
            logger.warning(
                "Multiple substances for CAS %s", cas_number,
            )
            return None

    def _try_fuzzy_match(
        self,
        product_name: str,
        manufacturer_name: str,
    ) -> IdentityMatch:
        """Fuzzy-Matching über Name + Hersteller."""
        best_match = None
        best_score = 0.0

        candidates = GlobalSubstance.objects.all()[:500]

        for substance in candidates:
            name_score = SequenceMatcher(
                None,
                product_name.lower(),
                substance.name.lower(),
            ).ratio()

            # Synonyme prüfen
            for synonym in (substance.synonyms or []):
                syn_score = SequenceMatcher(
                    None,
                    product_name.lower(),
                    str(synonym).lower(),
                ).ratio()
                name_score = max(name_score, syn_score)

            if name_score > best_score:
                best_score = name_score
                best_match = substance

        if best_match and best_score >= CONFIDENCE_ASK_USER:
            logger.info(
                "Fuzzy match: '%s' → '%s' (score=%.3f)",
                product_name, best_match.name, best_score,
            )
            return IdentityMatch(
                substance=best_match,
                confidence=best_score,
                match_type="fuzzy",
            )

        logger.info(
            "No match for '%s' (best=%.3f)",
            product_name, best_score,
        )
        return IdentityMatch(
            substance=None,
            confidence=best_score,
            match_type="none",
        )
