# src/global_sds/services/identity_resolver.py
"""
SdsIdentityResolver — Identitätsauflösung (ADR-012 §5 Stufe 2).

CAS-Lookup (exakt) + Fuzzy Name+Hersteller Matching.
"""

import logging
from dataclasses import dataclass

from django.conf import settings

from global_sds.models import GlobalSubstance

logger = logging.getLogger(__name__)

# Konfigurierbare Schwellenwerte (ADR-012 §7.3 N-1)
CONFIDENCE_AUTO_MATCH = getattr(
    settings,
    "SDS_IDENTITY_AUTO_MATCH_THRESHOLD",
    0.95,
)
CONFIDENCE_ASK_USER = getattr(
    settings,
    "SDS_IDENTITY_ASK_USER_THRESHOLD",
    0.70,
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
        return CONFIDENCE_ASK_USER <= self.confidence < CONFIDENCE_AUTO_MATCH

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
            product_name,
            manufacturer_name,
        )

    def _normalize_cas(self, cas: str) -> str:
        """CAS normalisieren (Leerzeichen, Bindestriche)."""
        return cas.strip().replace(" ", "").replace("‐", "-")

    def _try_cas_match(
        self,
        cas_number: str,
    ) -> IdentityMatch | None:
        """Exakter CAS-Match."""
        try:
            substance = GlobalSubstance.objects.get(
                cas_number=cas_number,
            )
            logger.info(
                "CAS exact match: %s → %s",
                cas_number,
                substance.name,
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
                "Multiple substances for CAS %s",
                cas_number,
            )
            return None

    def _try_fuzzy_match(
        self,
        product_name: str,
        manufacturer_name: str,
    ) -> IdentityMatch:
        """
        Fuzzy-Matching über Name via pg_trgm similarity (ADR-161 §P0.4).

        Uses PostgreSQL pg_trgm extension for trigram-based similarity
        scoring directly in the database — no Python loop required.
        Falls back to difflib SequenceMatcher if pg_trgm is unavailable.
        """
        search_term = product_name.lower().strip()
        if not search_term:
            return IdentityMatch(
                substance=None,
                confidence=0.0,
                match_type="none",
            )

        try:
            result = self._pg_trgm_match(search_term)
        except Exception:
            logger.warning(
                "pg_trgm unavailable, falling back to difflib",
                exc_info=True,
            )
            result = self._difflib_fallback(search_term)

        if result and result.confidence >= CONFIDENCE_ASK_USER:
            logger.info(
                "Fuzzy match: '%s' → '%s' (score=%.3f, type=%s)",
                product_name,
                result.substance.name,
                result.confidence,
                result.match_type,
            )
            return result

        score = result.confidence if result else 0.0
        logger.info("No match for '%s' (best=%.3f)", product_name, score)
        return IdentityMatch(
            substance=None,
            confidence=score,
            match_type="none",
        )

    def _pg_trgm_match(self, search_term: str) -> IdentityMatch | None:
        """
        pg_trgm similarity search — single DB query, O(1) scalability.

        Uses similarity() on name field. Synonyms are checked via
        a raw annotation since JSONField arrays need unnesting.
        """

        # Annotate with trigram similarity score on name
        candidates = (
            GlobalSubstance.objects.extra(
                select={"name_similarity": "similarity(LOWER(name), %s)"},
                select_params=[search_term],
            ).order_by("-name_similarity")
        )[:5]  # Top 5 candidates

        best_match = None
        best_score = 0.0

        for substance in candidates:
            score = float(substance.name_similarity)

            # Also check synonyms (JSON array) with Python fallback
            for synonym in substance.synonyms or []:
                from difflib import SequenceMatcher

                syn_score = SequenceMatcher(
                    None,
                    search_term,
                    str(synonym).lower(),
                ).ratio()
                score = max(score, syn_score)

            if score > best_score:
                best_score = score
                best_match = substance

        if best_match:
            return IdentityMatch(
                substance=best_match,
                confidence=best_score,
                match_type="fuzzy",
            )
        return None

    def _difflib_fallback(self, search_term: str) -> IdentityMatch | None:
        """Pure-Python fallback when pg_trgm is not available."""
        from difflib import SequenceMatcher

        best_match = None
        best_score = 0.0

        for substance in GlobalSubstance.objects.all()[:500]:
            name_score = SequenceMatcher(
                None,
                search_term,
                substance.name.lower(),
            ).ratio()

            for synonym in substance.synonyms or []:
                syn_score = SequenceMatcher(
                    None,
                    search_term,
                    str(synonym).lower(),
                ).ratio()
                name_score = max(name_score, syn_score)

            if name_score > best_score:
                best_score = name_score
                best_match = substance

        if best_match:
            return IdentityMatch(
                substance=best_match,
                confidence=best_score,
                match_type="fuzzy",
            )
        return None
