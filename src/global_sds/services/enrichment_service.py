# src/global_sds/services/enrichment_service.py
"""
SdsEnrichmentService — Web-Anreicherung via REFLEX PubChem/GESTIS.

Ergänzt parse_result-Daten um fehlende CAS-Nummern, H/P-Sätze
und Signalwörter aus öffentlichen Gefahrstoffdatenbanken.

Requires: iil-reflex[web]>=0.2.1
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Ergebnis der Web-Anreicherung."""

    enriched: bool = False
    cas_number: str = ""
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    signal_word: str = ""
    ghs_pictograms: list[str] = field(default_factory=list)
    iupac_name: str = ""
    source: str = ""
    errors: list[str] = field(default_factory=list)


class SdsEnrichmentService:
    """
    Reichert SDS-Parse-Ergebnisse mit Webdaten an.

    Strategie:
    1. Wenn CAS vorhanden → PubChem lookup_by_cas
    2. Wenn nur Produktname → PubChem lookup_by_name
    3. Fehlende Felder aus Web-Ergebnis ergänzen
    """

    def __init__(self):
        self._pubchem = None
        self._gestis = None

    def _get_pubchem(self):
        """Lazy init PubChem adapter."""
        if self._pubchem is None:
            try:
                from reflex.web import PubChemAdapter

                self._pubchem = PubChemAdapter()
            except ImportError:
                logger.warning(
                    "iil-reflex[web] not installed — "
                    "PubChem enrichment unavailable"
                )
        return self._pubchem

    def _get_gestis(self):
        """Lazy init GESTIS adapter."""
        if self._gestis is None:
            try:
                from reflex.web import GESTISAdapter

                self._gestis = GESTISAdapter()
            except ImportError:
                logger.warning(
                    "iil-reflex[web] not installed — "
                    "GESTIS enrichment unavailable"
                )
        return self._gestis

    def enrich(self, parse_result: dict) -> EnrichmentResult:
        """
        Fehlende Daten via PubChem/GESTIS ergänzen.

        Args:
            parse_result: Dict aus SdsParserService.parse_pdf()

        Returns:
            EnrichmentResult mit angereicherten Feldern.
        """
        result = EnrichmentResult()
        cas = parse_result.get("cas_number", "")
        product_name = parse_result.get("product_name", "")

        if not cas and not product_name:
            return result

        # ── PubChem Lookup ──
        pubchem = self._get_pubchem()
        if pubchem:
            sds = None
            try:
                if cas:
                    sds = pubchem.lookup_by_cas(cas)
                elif product_name:
                    sds = pubchem.lookup_by_name(product_name)
            except Exception as e:
                logger.warning("PubChem lookup failed: %s", e)
                result.errors.append(f"PubChem: {e}")

            if sds:
                result.source = "pubchem"
                if sds.cas_number:
                    result.cas_number = sds.cas_number
                if sds.h_statements:
                    result.h_statements = sds.h_statements
                if sds.p_statements:
                    result.p_statements = sds.p_statements
                if sds.signal_word:
                    result.signal_word = sds.signal_word
                if sds.ghs_pictograms:
                    result.ghs_pictograms = sds.ghs_pictograms
                if sds.substance_name:
                    result.iupac_name = sds.substance_name
                result.enriched = True

        return result

    def merge_into_parse_result(
        self,
        parse_result: dict,
        enrichment: EnrichmentResult,
    ) -> dict:
        """
        Ergänzt parse_result mit Enrichment-Daten (nur leere Felder).

        Originalwerte aus der PDF-Extraktion haben Vorrang.
        Web-Daten füllen nur leere Felder auf.
        """
        if not enrichment.enriched:
            return parse_result

        merged = dict(parse_result)

        # CAS ergänzen wenn aus PDF leer
        if not merged.get("cas_number") and enrichment.cas_number:
            merged["cas_number"] = enrichment.cas_number
            logger.info(
                "Enriched CAS: %s (source: %s)",
                enrichment.cas_number,
                enrichment.source,
            )

        # H-Sätze ergänzen (merge, nicht ersetzen)
        if enrichment.h_statements:
            existing = set(merged.get("h_statements", []))
            new = set(enrichment.h_statements) - existing
            if new:
                merged["h_statements"] = sorted(existing | new)
                logger.info("Enriched H-statements: +%d", len(new))

        # P-Sätze ergänzen
        if enrichment.p_statements:
            existing = set(merged.get("p_statements", []))
            new = set(enrichment.p_statements) - existing
            if new:
                merged["p_statements"] = sorted(existing | new)
                logger.info("Enriched P-statements: +%d", len(new))

        # Signalwort ergänzen wenn fehlend
        if (
            merged.get("signal_word", "none") == "none"
            and enrichment.signal_word
        ):
            merged["signal_word"] = enrichment.signal_word.lower()

        return merged
