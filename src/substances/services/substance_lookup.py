"""
Externe Datenbank-Lookups für Gefahrstoffe.

Quellen:
- GESTIS (DGUV): Deutsche Stoffdaten, Vorschriften, Schutzmaßnahmen
- PubChem (NIH): GHS-Klassifizierung, Molekulardaten
- ECHA C&L: via PubChem aggregiert

Usage:
    from substances.services.substance_lookup import SubstanceLookupService
    svc = SubstanceLookupService()
    result = svc.lookup("67-64-1")   # CAS
    result = svc.lookup("Aceton")    # Name
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest"
GESTIS_API = "https://gestis-api.dguv.de/api"
GESTIS_KEY = "dddiiasjhduuvnnasdkkwUUSHhjaPPKMasd"
API_TIMEOUT = 15

CAS_PATTERN = re.compile(r"^\d{1,7}-\d{2}-\d$")


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class LookupResult:
    """Ergebnis eines Gefahrstoff-Lookups."""

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
    gestis_zvg: str = ""

    # GHS
    signal_word: str = ""
    h_statements: list[str] = field(default_factory=list)
    p_statements: list[str] = field(default_factory=list)
    pictograms: list[str] = field(default_factory=list)
    ghs_descriptions: list[str] = field(default_factory=list)
    ghs_einstufung: str = ""

    # Zusatzdaten
    is_cmr: bool = False
    flash_point: Optional[str] = None
    boiling_point: Optional[str] = None
    melting_point: Optional[str] = None
    density: Optional[str] = None
    ignition_temp: Optional[str] = None
    explosion_limits: Optional[str] = None
    temp_class: str = ""
    explosion_group: str = ""
    physical_state: str = ""
    properties: str = ""
    chemical_char: str = ""

    # ECHA C&L
    echa_notifications: int = 0
    echa_summary: str = ""

    # GESTIS Arbeitsschutz
    agw: str = ""
    bgw: str = ""
    first_aid: str = ""
    protective_measures: str = ""
    storage: str = ""
    fire_protection: str = ""
    disposal: str = ""
    spill_response: str = ""
    transport: str = ""

    # Vorschriften / Regelwerke
    regulations: list[str] = field(default_factory=list)
    wgk: str = ""
    stoerfallv: str = ""

    # GESTIS Link
    gestis_url: str = ""

    def to_import_record(self) -> dict:
        """Konvertiert für SubstanceImportService."""
        return {
            "name": self.name or self.iupac_name,
            "cas": self.cas,
            "ec": self.ec_number,
            "trade_name": "",
            "description": self.iupac_name or self.chemical_char,
            "signal_word": self.signal_word,
            "h_statements": self.h_statements,
            "p_statements": self.p_statements,
            "pictograms": self.pictograms,
            "is_cmr": self.is_cmr,
            "storage_class": "",
            "flash_point_c": self._parse_temp(self.flash_point),
            "ignition_temperature_c": self._parse_temp(
                self.ignition_temp
            ),
            "temperature_class": self.temp_class,
            "explosion_group": self.explosion_group,
        }

    @staticmethod
    def _parse_temp(val: Optional[str]) -> Optional[float]:
        if not val:
            return None
        m = re.search(r"(-?\d+(?:[.,]\d+)?)", val)
        if m:
            return float(m.group(1).replace(",", "."))
        return None


class SubstanceLookupService:
    """Multi-Source Lookup für Gefahrstoffdaten."""

    def __init__(self, timeout: int = API_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "risk-hub/1.0"}
        )

    def lookup(self, query: str) -> LookupResult:
        """GESTIS zuerst, dann PubChem als Fallback."""
        query = query.strip()
        if not query:
            return LookupResult()

        # 1. GESTIS (deutsche Quelle, sehr detailliert)
        result = self._gestis_lookup(query)

        # 2. PubChem Fallback
        if not result.found:
            if CAS_PATTERN.match(query):
                result = self._pubchem_by_cas(query)
            else:
                result = self._pubchem_by_name(query)

        # 3. PubChem-Ergänzung (Molekulardaten)
        if result.found and not result.molecular_formula:
            self._pubchem_enrich(result)

        return result

    # =================================================================
    # GESTIS (DGUV) — Primary source
    # =================================================================

    def _gestis_lookup(self, query: str) -> LookupResult:
        """Search GESTIS by name or CAS, fetch full article."""
        zvg = self._gestis_search(query)
        if not zvg:
            return LookupResult()

        logger.info("GESTIS article: ZVG %s", zvg)
        url = f"{GESTIS_API}/article/de/{zvg}"
        headers = {"Authorization": f"Bearer {GESTIS_KEY}"}
        try:
            resp = self.session.get(
                url, headers=headers, timeout=self.timeout
            )
            if resp.status_code != 200:
                logger.warning("GESTIS article %s: %d", zvg, resp.status_code)
                return LookupResult()
            data = resp.json()
        except Exception:
            logger.exception("GESTIS article failed: %s", zvg)
            return LookupResult()

        result = LookupResult(
            found=True,
            source="GESTIS (DGUV)",
            name=data.get("name", ""),
            gestis_zvg=zvg,
            gestis_url=f"https://gestis.dguv.de/data?name={zvg}",
        )

        # Parse chapters
        chapters = {}
        for hk in data.get("hauptkapitel", []):
            for uk in hk.get("unterkapitel", []):
                drnr = uk.get("drnr", "")
                text = uk.get("text") or ""
                if text:
                    chapters[drnr] = text

        self._parse_gestis_chapters(chapters, result)
        return result

    def _gestis_search(self, query: str) -> Optional[str]:
        """Search GESTIS → return ZVG number."""
        url = f"{GESTIS_API}/search/de"
        headers = {"Authorization": f"Bearer {GESTIS_KEY}"}
        params = {"query": query, "exact": "true"}
        try:
            resp = self.session.get(
                url, headers=headers, params=params,
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                return None
            items = resp.json()
            if not isinstance(items, list) or not items:
                return None
            # Exact CAS match
            if CAS_PATTERN.match(query):
                for item in items:
                    if item.get("cas_nr") == query:
                        return item.get("zvg_nr")
            # Exact name match (case-insensitive)
            ql = query.lower()
            for item in items:
                if (item.get("name") or "").lower() == ql:
                    return item.get("zvg_nr")
            # First result as fallback
            return items[0].get("zvg_nr")
        except Exception:
            logger.exception("GESTIS search failed: %s", query)
        return None

    def _parse_gestis_chapters(
        self, chapters: dict, result: LookupResult
    ) -> None:
        """Extract structured data from GESTIS HTML chapters."""
        s = _strip_html

        # Physical state (0303)
        if "0303" in chapters:
            result.physical_state = s(chapters["0303"])[:200]
        # Properties (0304)
        if "0304" in chapters:
            result.properties = s(chapters["0304"])[:200]
        # Chemical characterization (0305)
        if "0305" in chapters:
            result.chemical_char = s(chapters["0305"])[:500]
        # Molecular formula (0400)
        if "0400" in chapters:
            txt = s(chapters["0400"])
            mw = re.search(r"Molare Masse:\s*([\d.,]+)", txt)
            if mw:
                result.molecular_weight = mw.group(1)
            mf = re.search(r"^([A-Z][A-Za-z0-9 ]+)", txt)
            if mf:
                result.molecular_formula = mf.group(1).strip()

        # Physical properties
        if "0602" in chapters:
            m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*°C",
                          s(chapters["0602"]))
            if m:
                result.melting_point = f"{m.group(1)} °C"
        if "0603" in chapters:
            m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*°C",
                          s(chapters["0603"]))
            if m:
                result.boiling_point = f"{m.group(1)} °C"
        if "0604" in chapters:
            m = re.search(r"Wert:\s*([\d.,]+)\s*g/cm",
                          s(chapters["0604"]))
            if m:
                result.density = f"{m.group(1)} g/cm³"
        if "0607" in chapters:
            m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*°C",
                          s(chapters["0607"]))
            if m:
                result.flash_point = f"{m.group(1)} °C"
        if "0608" in chapters:
            txt = s(chapters["0608"])
            m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*°C", txt)
            if m:
                result.ignition_temp = f"{m.group(1)} °C"
            tc = re.search(r"Temperaturklasse:\s*(T\d)", txt)
            if tc:
                result.temp_class = tc.group(1)
        if "0609" in chapters:
            txt = s(chapters["0609"])
            result.explosion_limits = txt[:300]
            eg = re.search(
                r"Explosionsgruppe:\s*(II[ABC])", txt
            )
            if eg:
                result.explosion_group = eg.group(1)

        # GHS classification (1303)
        if "1303" in chapters:
            txt = s(chapters["1303"])
            result.ghs_einstufung = txt[:500]
            # Extract H-codes
            h_codes = set(re.findall(r"H\d{3}[a-z]?", txt))
            result.h_statements = sorted(h_codes)
            # Signal word
            if "Gefahr" in txt or "Danger" in txt:
                result.signal_word = "danger"
            elif "Achtung" in txt or "Warning" in txt:
                result.signal_word = "warning"
            # CMR
            cmr = {"H340", "H341", "H350", "H351",
                   "H360", "H361", "H362"}
            result.is_cmr = bool(h_codes & cmr)
            result.ghs_descriptions = (
                self._h_codes_to_descriptions(h_codes)
            )

        # Workplace limits
        if "1201" in chapters:
            result.agw = s(chapters["1201"])[:300]
        if "1205" in chapters:
            result.bgw = s(chapters["1205"])[:300]

        # Transport (1108)
        if "1108" in chapters:
            result.transport = s(chapters["1108"])[:300]

        # WGK (1106)
        if "1106" in chapters:
            txt = s(chapters["1106"])
            result.wgk = txt[:200]

        # StörfallV (1215)
        if "1215" in chapters:
            result.stoerfallv = s(chapters["1215"])[:300]

        # Regulations/Vorschriften (1209, 1210)
        regs = []
        if "1209" in chapters:
            txt = s(chapters["1209"])
            for trgs in re.findall(
                r"TRGS \d+[^.]*", txt
            ):
                regs.append(trgs.strip()[:120])
        if "1210" in chapters:
            txt = s(chapters["1210"])
            for dguv in re.findall(
                r"DGUV [^,.\n]+", txt
            ):
                regs.append(dguv.strip()[:120])
        if "1208" in chapters:
            txt = s(chapters["1208"])
            if "REACH" in txt:
                regs.append(txt[:120])
        result.regulations = regs[:20]

        # Protective measures
        if "0703" in chapters:
            result.first_aid = s(chapters["0703"])[:500]
        if "0802" in chapters:
            result.protective_measures = (
                s(chapters["0802"])[:500]
            )
        if "0803" in chapters:
            result.storage = s(chapters["0803"])[:500]
        if "0804" in chapters:
            result.fire_protection = s(chapters["0804"])[:500]
        if "0806" in chapters:
            pm = s(chapters["0806"])
            if result.protective_measures:
                result.protective_measures += "\n" + pm[:500]
            else:
                result.protective_measures = pm[:500]
        if "0807" in chapters:
            result.disposal = s(chapters["0807"])[:300]
        if "0808" in chapters:
            result.spill_response = s(chapters["0808"])[:500]

    # =================================================================
    # PubChem — Fallback + Enrichment
    # =================================================================

    def _pubchem_by_cas(self, cas: str) -> LookupResult:
        """PubChem lookup by CAS number."""
        cid = self._pubchem_resolve_cas(cas)
        if not cid:
            return LookupResult()
        result = self._pubchem_get_ghs(cid)
        result.cas = cas
        if not result.name:
            result.name = self._pubchem_get_name(cid)
        return result

    def _pubchem_by_name(self, name: str) -> LookupResult:
        """PubChem lookup by name."""
        cid = self._pubchem_resolve_name(name)
        if not cid:
            return LookupResult()
        result = self._pubchem_get_ghs(cid)
        if not result.name:
            result.name = name
        return result

    def _pubchem_enrich(self, result: LookupResult) -> None:
        """Add PubChem molecular data to a GESTIS result."""
        query = result.cas or result.name
        if not query:
            return
        cid = self._pubchem_resolve_name(query)
        if cid:
            result.pubchem_cid = cid
            self._pubchem_get_properties(cid, result)

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

    def _pubchem_get_name(self, cid: int) -> str:
        """Fetch common name from PubChem synonyms."""
        url = (
            f"{PUBCHEM_BASE}/pug/compound/cid/{cid}"
            f"/synonyms/JSON"
        )
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            info_list = (
                data.get("InformationList", {})
                .get("Information", [])
            )
            if info_list:
                synonyms = info_list[0].get("Synonym", [])
                if synonyms:
                    return synonyms[0]
        except Exception:
            logger.exception(
                "PubChem synonyms failed for CID %d", cid
            )
        return ""

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
