# src/global_sds/services/pubchem_service.py
"""
PubChemEnrichmentService — Anreicherung via PubChem REST API (ADR-169 Phase 1).

Ruft für eine CAS-Nummer oder einen Produktnamen folgende Daten ab:
- Molekulare Eigenschaften (Formel, Gewicht, IUPAC-Name, CID)
- GHS-Klassifizierung (H/P-Sätze, Signalwort, Piktogramme)
- Physikalische Eigenschaften (Flammpunkt wenn verfügbar)

API-Doku: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"

H_PATTERN = re.compile(r"\b(H[0-9]{3}[A-Za-z]?)\b")
P_PATTERN = re.compile(r"\b(P[0-9]{3}(?:\+P[0-9]{3})*)\b")
GHS_PATTERN = re.compile(r"\b(GHS0[1-9])\b", re.IGNORECASE)
SIGNAL_PATTERN = re.compile(r"\b(Danger|Warning|Gefahr|Achtung)\b", re.IGNORECASE)
FLASH_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*°?\s*C", re.IGNORECASE)


@dataclass
class PubChemResult:
    """Ergebnis der PubChem-Anreicherung."""

    enriched: bool = False
    cid: int | None = None
    iupac_name: str = ""
    molecular_formula: str = ""
    molecular_weight: float | None = None
    inchi_key: str = ""
    cas_number: str = ""
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    ghs_pictograms: list[str] = field(default_factory=list)
    signal_word: str = ""
    flash_point_c: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class PubChemEnrichmentService:
    """
    Reichert SDS-Daten mit PubChem REST API an.

    Nutzt httpx mit kurzem Timeout (5s connect, 15s read) und
    fängt alle Netzwerkfehler als leere Results.
    """

    TIMEOUT = (5.0, 15.0)  # connect, read

    def enrich_by_cas(self, cas: str) -> PubChemResult:
        """Anreicherung via CAS-Nummer."""
        return self._enrich("name", cas)

    def enrich_by_name(self, name: str) -> PubChemResult:
        """Anreicherung via Produktname (Fallback wenn keine CAS)."""
        return self._enrich("name", name)

    def enrich(self, parse_result: dict) -> PubChemResult:
        """Automatisch CAS oder Produktname nutzen."""
        cas = (parse_result.get("cas_number") or "").strip()
        name = (parse_result.get("product_name") or "").strip()

        if cas:
            result = self._enrich("name", cas)
            if result.enriched:
                return result

        if name:
            return self._enrich("name", name)

        return PubChemResult()

    def _enrich(self, id_type: str, identifier: str) -> PubChemResult:
        result = PubChemResult()
        if not identifier:
            return result

        try:
            import httpx
        except ImportError:
            result.errors.append("httpx not installed")
            return result

        try:
            cid = self._resolve_cid(httpx, id_type, identifier)
        except Exception as exc:
            logger.warning("PubChem CID lookup failed for %s: %s", identifier, exc)
            result.errors.append(str(exc))
            return result

        if not cid:
            return result

        result.cid = cid

        try:
            props = self._fetch_properties(httpx, cid)
            result.iupac_name = props.get("IUPACName", "")
            result.molecular_formula = props.get("MolecularFormula", "")
            mw = props.get("MolecularWeight")
            if mw:
                try:
                    result.molecular_weight = float(mw)
                except (ValueError, TypeError):
                    pass
            result.inchi_key = props.get("InChIKey", "")
        except Exception as exc:
            logger.warning("PubChem properties failed for CID %s: %s", cid, exc)
            result.errors.append(f"properties: {exc}")

        try:
            ghs = self._fetch_ghs(httpx, cid)
            result.h_statements = ghs.get("h_statements", [])
            result.p_statements = ghs.get("p_statements", [])
            result.ghs_pictograms = ghs.get("pictograms", [])
            result.signal_word = ghs.get("signal_word", "")
        except Exception as exc:
            logger.warning("PubChem GHS failed for CID %s: %s", cid, exc)
            result.errors.append(f"ghs: {exc}")

        result.enriched = bool(result.iupac_name or result.h_statements or result.molecular_formula)
        result.raw = {
            "cid": cid,
            "source": f"PubChem CID {cid}",
            "iupac_name": result.iupac_name,
            "molecular_formula": result.molecular_formula,
            "molecular_weight": result.molecular_weight,
            "inchi_key": result.inchi_key,
            "h_statements": result.h_statements,
            "p_statements": result.p_statements,
            "ghs_pictograms": result.ghs_pictograms,
            "signal_word": result.signal_word,
        }

        logger.info(
            "PubChem enriched CID=%s: H=%d P=%d formula=%s",
            cid,
            len(result.h_statements),
            len(result.p_statements),
            result.molecular_formula,
        )
        return result

    def _resolve_cid(self, httpx, id_type: str, identifier: str) -> int | None:
        url = f"{PUBCHEM_BASE}/compound/{id_type}/{identifier}/cids/JSON"
        resp = httpx.get(url, timeout=self.TIMEOUT, follow_redirects=True)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        return cids[0] if cids else None

    def _fetch_properties(self, httpx, cid: int) -> dict:
        props = "IUPACName,MolecularFormula,MolecularWeight,InChIKey"
        url = f"{PUBCHEM_BASE}/compound/cid/{cid}/property/{props}/JSON"
        resp = httpx.get(url, timeout=self.TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
        table = data.get("PropertyTable", {}).get("Properties", [])
        return table[0] if table else {}

    def _fetch_ghs(self, httpx, cid: int) -> dict:
        url = f"{PUBCHEM_VIEW}/data/compound/{cid}/JSON?heading=GHS+Classification"
        resp = httpx.get(url, timeout=self.TIMEOUT, follow_redirects=True)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        text = resp.text

        h_codes = sorted(set(H_PATTERN.findall(text)))
        p_codes = sorted(set(P_PATTERN.findall(text)))
        ghs_codes = sorted(set(GHS_PATTERN.findall(text)))
        sw_matches = SIGNAL_PATTERN.findall(text)

        signal_word = ""
        sw_lower = {s.lower() for s in sw_matches}
        if "danger" in sw_lower or "gefahr" in sw_lower:
            signal_word = "danger"
        elif "warning" in sw_lower or "achtung" in sw_lower:
            signal_word = "warning"

        return {
            "h_statements": h_codes,
            "p_statements": p_codes,
            "pictograms": [g.upper() for g in ghs_codes],
            "signal_word": signal_word,
        }

    def merge_into_parse_result(self, parse_result: dict, pubchem: PubChemResult) -> dict:
        """
        Ergänzt parse_result mit PubChem-Daten (nur leere Felder).

        PDF-extrahierte Werte haben immer Vorrang.
        """
        if not pubchem.enriched:
            return parse_result

        merged = dict(parse_result)

        if not merged.get("cas_number") and pubchem.cas_number:
            merged["cas_number"] = pubchem.cas_number

        if pubchem.h_statements:
            existing = set(merged.get("h_statements") or [])
            new = set(pubchem.h_statements) - existing
            if new:
                merged["h_statements"] = sorted(existing | new)

        if pubchem.p_statements:
            existing = set(merged.get("p_statements") or [])
            new = set(pubchem.p_statements) - existing
            if new:
                merged["p_statements"] = sorted(existing | new)

        if pubchem.ghs_pictograms:
            existing = set(merged.get("pictograms") or [])
            new = set(pubchem.ghs_pictograms) - existing
            if new:
                merged["pictograms"] = sorted(existing | new)

        if not merged.get("signal_word") and pubchem.signal_word:
            merged["signal_word"] = pubchem.signal_word

        # Molekulare Daten immer als Ergänzung speichern
        merged["_pubchem"] = pubchem.raw

        return merged
