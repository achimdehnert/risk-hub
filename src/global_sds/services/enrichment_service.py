# src/global_sds/services/enrichment_service.py
"""
SdsEnrichmentService — Web-Anreicherung via iil-enrichment (ADR-169).

Ergänzt parse_result-Daten um fehlende CAS-Nummern, H/P-Sätze
und Signalwörter aus GESTIS + PubChem via EnrichmentRegistry.

Requires: iil-enrichment[gestis,pubchem]>=0.1.0
Replaces: reflex.web PubChem/GESTIS adapters (legacy)
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SdsEnrichmentResult:
    """Ergebnis der Web-Anreicherung (Pipeline-kompatibel)."""

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

    Uses iil-enrichment registry (ADR-169) with GESTIS + PubChem
    providers registered in GlobalSdsConfig.ready().

    Strategie:
    1. Natural key = CAS oder Produktname
    2. Registry.enrich_merged("sds", key) → merged EnrichmentResult
    3. Extrahiere relevante Felder in Pipeline-kompatibles SdsEnrichmentResult
    """

    def enrich(self, parse_result: dict) -> SdsEnrichmentResult:
        """
        Fehlende Daten via GESTIS/PubChem ergänzen.

        Args:
            parse_result: Dict aus SdsParserService.parse_pdf()

        Returns:
            SdsEnrichmentResult mit angereicherten Feldern.
        """
        result = SdsEnrichmentResult()
        cas = parse_result.get("cas_number", "")
        product_name = parse_result.get("product_name", "")

        natural_key = cas or product_name
        if not natural_key:
            return result

        try:
            from enrichment import default_registry
        except ImportError:
            logger.warning("iil-enrichment not installed — enrichment skipped")
            result.errors.append("iil-enrichment not installed")
            return result

        try:
            enriched = default_registry.enrich_merged("sds", natural_key)
        except Exception as e:
            logger.warning("Enrichment failed for key=%s: %s", natural_key, e)
            result.errors.append(str(e))
            return result

        if enriched.is_empty:
            return result

        result.enriched = True
        result.source = enriched.source

        # Extract known properties into pipeline-compatible fields
        _get = enriched.get

        h_val = _get("h_statements")
        if h_val and isinstance(h_val.value, list):
            result.h_statements = h_val.value

        p_val = _get("p_statements")
        if p_val and isinstance(p_val.value, list):
            result.p_statements = p_val.value

        pic_val = _get("pictograms")
        if pic_val and isinstance(pic_val.value, list):
            result.ghs_pictograms = pic_val.value

        sw_val = _get("signal_word")
        if sw_val and isinstance(sw_val.value, str):
            result.signal_word = sw_val.value

        iupac = _get("iupac_name")
        if iupac and isinstance(iupac.value, str):
            result.iupac_name = iupac.value

        logger.info(
            "Enriched via iil-enrichment (source=%s, props=%d, key=%s)",
            enriched.source,
            len(enriched.properties),
            natural_key,
        )
        return result

    def merge_into_parse_result(
        self,
        parse_result: dict,
        enrichment: SdsEnrichmentResult,
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
        if merged.get("signal_word", "none") == "none" and enrichment.signal_word:
            merged["signal_word"] = enrichment.signal_word.lower()

        return merged
