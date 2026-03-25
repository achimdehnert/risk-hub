"""
Externe Datenbank-Lookups für Gefahrstoffe.

Quellen:
- PubChem (NIH): CAS/Name → GHS-Klassifizierung, H/P-Sätze, Molekulardaten
- ECHA C&L: via PubChem aggregiert (ECHA-Notifikationen)
- GESTIS (DGUV): Reserviert für zukünftige Integration (API erfordert Auth)

Usage:
    from substances.services.substance_lookup import SubstanceLookupService

    svc = SubstanceLookupService()
    result = svc.lookup("67-64-1")          # by CAS
    result = svc.lookup("Aceton")           # by name
    result = svc.lookup_by_name("acetone")  # explicit name search
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest"
PUBCHEM_TIMEOUT = 15

CAS_PATTERN = re.compile(r"^\d{1,7}-\d{2}-\d$")


@dataclass
class LookupResult:
    """Ergebnis eines Gefahrstoff-Lookups aus externen Quellen."""

    found: bool = False
    source: str = ""

    # Identifikation
    name: str = ""
    cas: str = ""
    ec_number: str = ""
    iupac_name: str = ""
    molecular_formula: str = ""
    molecular_weight: str = ""
    pubchem_cid: Optional[int] = None

    # GHS-Klassifizierung
    signal_word: str = ""  # "danger" | "warning" | ""
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    pictograms: list[str] = field(default_factory=list)
    ghs_descriptions: list[str] = field(default_factory=list)

    # Zusatzdaten
    is_cmr: bool = False
    flash_point: Optional[str] = None
    boiling_point: Optional[str] = None

    # ECHA C&L Info
    echa_notifications: int = 0
    echa_summary: str = ""

    def to_import_record(self) -> dict:
        """Konvertiert in Format für SubstanceImportService.import_from_records()."""
        return {
            "name": self.name,
            "cas": self.cas,
            "ec": self.ec_number,
            "trade_name": "",
            "description": self.iupac_name,
            "signal_word": self.signal_word,
            "h_statements": self.h_statements,
            "p_statements": self.p_statements,
            "pictograms": self.pictograms,
            "is_cmr": self.is_cmr,
            "storage_class": "",
        }


class SubstanceLookupService:
    """Multi-Source Lookup für Gefahrstoffdaten."""

    def __init__(self, timeout: int = PUBCHEM_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "risk-hub/1.0"}
        )

    def lookup(self, query: str) -> LookupResult:
        """Auto-detect: CAS-Nummer oder Name → Lookup."""
        query = query.strip()
        if not query:
            return LookupResult()

        if CAS_PATTERN.match(query):
            return self.lookup_by_cas(query)
        return self.lookup_by_name(query)

    def lookup_by_cas(self, cas: str) -> LookupResult:
        """Lookup via CAS-Nummer."""
        logger.info("PubChem lookup by CAS: %s", cas)
        cid = self._pubchem_resolve_cas(cas)
        if not cid:
            logger.info("CAS %s nicht gefunden in PubChem", cas)
            return LookupResult()
        result = self._pubchem_get_ghs(cid)
        result.cas = cas
        return result

    def lookup_by_name(self, name: str) -> LookupResult:
        """Lookup via Stoffname."""
        logger.info("PubChem lookup by name: %s", name)
        cid = self._pubchem_resolve_name(name)
        if not cid:
            logger.info("Name '%s' nicht gefunden in PubChem", name)
            return LookupResult()
        result = self._pubchem_get_ghs(cid)
        if not result.name:
            result.name = name
        return result

    # =========================================================================
    # PubChem API
    # =========================================================================

    def _pubchem_resolve_name(self, name: str) -> Optional[int]:
        """Resolve substance name → PubChem CID."""
        url = f"{PUBCHEM_BASE}/pug/compound/name/{requests.utils.quote(name)}/property/MolecularFormula,MolecularWeight/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                return props[0].get("CID")
        except Exception:
            logger.exception("PubChem name resolve failed for '%s'", name)
        return None

    def _pubchem_resolve_cas(self, cas: str) -> Optional[int]:
        """Resolve CAS number → PubChem CID."""
        url = f"{PUBCHEM_BASE}/pug/compound/name/{cas}/property/MolecularFormula,MolecularWeight/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None
            data = resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                return props[0].get("CID")
        except Exception:
            logger.exception("PubChem CAS resolve failed for '%s'", cas)
        return None

    def _pubchem_get_ghs(self, cid: int) -> LookupResult:
        """Fetch GHS classification data from PubChem PUG View."""
        result = LookupResult(found=True, source="PubChem", pubchem_cid=cid)

        # Get basic properties
        self._pubchem_get_properties(cid, result)

        # Get GHS data
        url = f"{PUBCHEM_BASE}/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning("PubChem GHS request failed: %d", resp.status_code)
                return result
            data = resp.json()
            self._parse_ghs_data(data, result)
        except Exception:
            logger.exception("PubChem GHS fetch failed for CID %d", cid)

        return result

    def _pubchem_get_properties(self, cid: int, result: LookupResult) -> None:
        """Fetch basic molecular properties."""
        url = f"{PUBCHEM_BASE}/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return
            data = resp.json()
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                p = props[0]
                result.molecular_formula = p.get("MolecularFormula", "")
                result.molecular_weight = str(p.get("MolecularWeight", ""))
                result.iupac_name = p.get("IUPACName", "")
        except Exception:
            logger.exception("PubChem properties fetch failed for CID %d", cid)

    def _parse_ghs_data(self, data: dict, result: LookupResult) -> None:
        """Parse GHS classification from PubChem PUG View response."""
        h_codes = set()
        p_codes = set()
        signal_word = ""
        pictograms = set()
        echa_summary_parts = []

        for section in data.get("Record", {}).get("Section", []):
            for sub in section.get("Section", []):
                for sub2 in sub.get("Section", []):
                    if "GHS" not in sub2.get("TOCHeading", ""):
                        continue
                    for info in sub2.get("Information", []):
                        name = info.get("Name", "")
                        val = info.get("Value", {})
                        strings = [
                            s.get("String", "")
                            for s in val.get("StringWithMarkup", [])
                            if s.get("String")
                        ]

                        if name == "Signal":
                            for s in strings:
                                if "Danger" in s:
                                    signal_word = "danger"
                                elif "Warning" in s and signal_word != "danger":
                                    signal_word = "warning"

                        elif "Hazard Statements" in name:
                            for s in strings:
                                h_match = re.match(r"(H\d{3}[a-z]?)", s)
                                if h_match:
                                    h_codes.add(h_match.group(1))

                        elif "Precautionary" in name:
                            for s in strings:
                                for p_match in re.finditer(r"(P\d{3}(?:\+P\d{3})*)", s):
                                    p_codes.add(p_match.group(1))

                        elif "ECHA" in name:
                            for s in strings:
                                echa_summary_parts.append(s)
                                notif_match = re.search(r"(\d+)\s*notifications", s)
                                if notif_match:
                                    result.echa_notifications = int(
                                        notif_match.group(1)
                                    )

        result.signal_word = signal_word
        result.h_statements = sorted(h_codes)
        result.p_statements = sorted(p_codes)
        result.pictograms = sorted(pictograms)
        result.echa_summary = " ".join(echa_summary_parts[:3])

        # CMR detection from H-statements
        cmr_codes = {"H340", "H341", "H350", "H351", "H360", "H361", "H362"}
        result.is_cmr = bool(h_codes & cmr_codes)

        # Map H-codes to GHS descriptions
        result.ghs_descriptions = self._h_codes_to_descriptions(h_codes)

    @staticmethod
    def _h_codes_to_descriptions(h_codes: set[str]) -> list[str]:
        """Map H-codes to German descriptions."""
        H_MAP = {
            "H200": "Instabil, explosiv",
            "H201": "Explosiv; Gefahr der Massenexplosion",
            "H202": "Explosiv; große Gefahr durch Splitter",
            "H220": "Extrem entzündbares Gas",
            "H221": "Entzündbares Gas",
            "H224": "Flüssigkeit und Dampf extrem entzündbar",
            "H225": "Flüssigkeit und Dampf leicht entzündbar",
            "H226": "Flüssigkeit und Dampf entzündbar",
            "H228": "Entzündbarer Feststoff",
            "H242": "Erwärmung kann Brand verursachen",
            "H270": "Kann Brand verursachen oder verstärken; Oxidationsmittel",
            "H271": "Kann Brand oder Explosion verursachen; starkes Oxidationsmittel",
            "H272": "Kann Brand verstärken; Oxidationsmittel",
            "H280": "Enthält Gas unter Druck",
            "H281": "Enthält tiefgekühltes Gas",
            "H290": "Kann gegenüber Metallen korrosiv sein",
            "H300": "Lebensgefahr bei Verschlucken",
            "H301": "Giftig bei Verschlucken",
            "H302": "Gesundheitsschädlich bei Verschlucken",
            "H304": "Kann bei Verschlucken und Eindringen in die Atemwege tödlich sein",
            "H310": "Lebensgefahr bei Hautkontakt",
            "H311": "Giftig bei Hautkontakt",
            "H312": "Gesundheitsschädlich bei Hautkontakt",
            "H314": "Verursacht schwere Verätzungen der Haut und schwere Augenschäden",
            "H315": "Verursacht Hautreizungen",
            "H317": "Kann allergische Hautreaktionen verursachen",
            "H318": "Verursacht schwere Augenschäden",
            "H319": "Verursacht schwere Augenreizung",
            "H330": "Lebensgefahr bei Einatmen",
            "H331": "Giftig bei Einatmen",
            "H332": "Gesundheitsschädlich bei Einatmen",
            "H334": "Kann bei Einatmen Allergie oder Asthma auslösen",
            "H335": "Kann die Atemwege reizen",
            "H336": "Kann Schläfrigkeit und Benommenheit verursachen",
            "H340": "Kann genetische Defekte verursachen",
            "H341": "Kann vermutlich genetische Defekte verursachen",
            "H350": "Kann Krebs erzeugen",
            "H351": "Kann vermutlich Krebs erzeugen",
            "H360": "Kann die Fruchtbarkeit beeinträchtigen oder das Kind im Mutterleib schädigen",
            "H361": "Kann vermutlich die Fruchtbarkeit beeinträchtigen oder das Kind schädigen",
            "H362": "Kann Säuglinge über die Muttermilch schädigen",
            "H370": "Schädigt die Organe",
            "H371": "Kann die Organe schädigen",
            "H372": "Schädigt die Organe bei längerer oder wiederholter Exposition",
            "H373": "Kann die Organe schädigen bei längerer oder wiederholter Exposition",
            "H400": "Sehr giftig für Wasserorganismen",
            "H410": "Sehr giftig für Wasserorganismen mit langfristiger Wirkung",
            "H411": "Giftig für Wasserorganismen mit langfristiger Wirkung",
            "H412": "Schädlich für Wasserorganismen mit langfristiger Wirkung",
            "H413": "Kann für Wasserorganismen schädlich sein mit langfristiger Wirkung",
            "H420": "Schädigt die öffentliche Gesundheit und die Umwelt durch Ozonabbau",
        }
        descriptions = []
        for code in sorted(h_codes):
            desc = H_MAP.get(code, "")
            if desc:
                descriptions.append(f"{code}: {desc}")
        return descriptions


def lookup_substance(query: str) -> LookupResult:
    """Convenience function for quick lookups."""
    svc = SubstanceLookupService()
    return svc.lookup(query)
