"""
Externe Datenbank-Lookups für Gefahrstoffe.

Uses iil-enrichment providers (GESTIS + PubChem) via EnrichmentRegistry.
Providers are registered in global_sds.apps.GlobalSdsConfig.ready().

Usage:
    from substances.services.substance_lookup import SubstanceLookupService
    svc = SubstanceLookupService()
    result = svc.lookup("67-64-1")   # CAS
    result = svc.lookup("Aceton")    # Name
"""

from __future__ import annotations

import logging
import re
import warnings
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
    pubchem_cid: int | None = None
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
    flash_point: str | None = None
    boiling_point: str | None = None
    melting_point: str | None = None
    density: str | None = None
    ignition_temp: str | None = None
    explosion_limits: str | None = None
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
        import json as _json

        return {
            "name": self.name or self.iupac_name,
            "cas": self.cas,
            "ec": self.ec_number,
            "trade_name": "",
            "description": (self.iupac_name or self.chemical_char),
            "signal_word": self.signal_word,
            "h_statements": self.h_statements,
            "p_statements": self.p_statements,
            "pictograms": self.pictograms,
            "is_cmr": self.is_cmr,
            "storage_class": "",
            "flash_point_c": self._parse_temp(self.flash_point),
            "ignition_temperature_c": self._parse_temp(self.ignition_temp),
            "temperature_class": self.temp_class,
            "explosion_group": self.explosion_group,
            # GESTIS-Daten
            "boiling_point_c": self._parse_temp(self.boiling_point),
            "melting_point_c": self._parse_temp(self.melting_point),
            "density": self.density or "",
            "molecular_formula": (self.molecular_formula or ""),
            "molecular_weight": (self.molecular_weight or ""),
            "agw": self.agw or "",
            "wgk": self.wgk or "",
            "first_aid": self.first_aid or "",
            "protective_measures": (self.protective_measures or ""),
            "storage_info": self.storage or "",
            "fire_protection": (self.fire_protection or ""),
            "disposal": self.disposal or "",
            "spill_response": (self.spill_response or ""),
            "regulations": _json.dumps(self.regulations, ensure_ascii=False),
            "gestis_zvg": self.gestis_zvg or "",
            "gestis_url": self.gestis_url or "",
        }

    @staticmethod
    def _parse_temp(val: str | None) -> float | None:
        if not val:
            return None
        m = re.search(r"(-?\d+(?:[.,]\d+)?)", val)
        if m:
            return float(m.group(1).replace(",", "."))
        return None


class SubstanceLookupService:
    """Multi-Source Lookup via iil-enrichment registry (GESTIS + PubChem)."""

    def lookup(self, query: str) -> LookupResult:
        """Lookup substance via enrichment registry, return LookupResult."""
        query = query.strip()
        if not query:
            return LookupResult()

        try:
            from enrichment import default_registry
        except ImportError:
            warnings.warn(
                "iil-enrichment not installed — substance lookup unavailable",
                stacklevel=2,
            )
            return LookupResult()

        merged = default_registry.enrich_merged("substance", query)
        if merged.is_empty:
            return LookupResult()

        return self._map_to_lookup_result(merged)

    def _map_to_lookup_result(self, enrichment) -> LookupResult:
        """Map EnrichmentResult → LookupResult."""
        g = self._get_str
        gl = self._get_list
        props = enrichment.properties

        h_codes = set(gl(props, "h_statements"))
        result = LookupResult(
            found=True,
            source=enrichment.source,
            # Identity
            name=g(props, "name"),
            cas=g(props, "cas_number"),
            ec_number=g(props, "ec_number"),
            iupac_name=g(props, "iupac_name"),
            molecular_formula=g(props, "molecular_formula"),
            molecular_weight=g(props, "molecular_weight"),
            pubchem_cid=self._get_int(props, "pubchem_cid"),
            gestis_zvg=g(props, "gestis_zvg"),
            # GHS
            signal_word=g(props, "signal_word"),
            h_statements=sorted(h_codes),
            p_statements=gl(props, "p_statements"),
            pictograms=gl(props, "pictograms"),
            ghs_einstufung=g(props, "ghs_einstufung"),
            ghs_descriptions=self._resolve_h_descriptions(h_codes),
            # CMR
            is_cmr=self._get_bool(props, "is_cmr"),
            # Physical
            flash_point=self._fmt_temp(props, "flash_point_c"),
            boiling_point=self._fmt_temp(props, "boiling_point_c"),
            melting_point=self._fmt_temp(props, "melting_point_c"),
            density=self._fmt_density(props),
            ignition_temp=self._fmt_temp(props, "ignition_temperature_c"),
            explosion_limits=g(props, "explosion_limits") or None,
            temp_class=g(props, "temperature_class"),
            explosion_group=g(props, "explosion_group"),
            physical_state=g(props, "physical_state"),
            properties=g(props, "properties"),
            chemical_char=g(props, "chemical_characterization"),
            # GESTIS Arbeitsschutz
            agw=g(props, "agw"),
            bgw=g(props, "bgw"),
            first_aid=g(props, "first_aid"),
            protective_measures=g(props, "protective_measures"),
            storage=g(props, "storage"),
            fire_protection=g(props, "fire_protection"),
            disposal=g(props, "disposal"),
            spill_response=g(props, "spill_response"),
            transport=g(props, "transport"),
            # Regulations
            regulations=gl(props, "regulations"),
            wgk=g(props, "wgk"),
            stoerfallv=g(props, "stoerfallv"),
            # GESTIS Link
            gestis_url=g(props, "gestis_url"),
        )
        return result

    # -- Property extraction helpers --

    @staticmethod
    def _get_str(props: dict, key: str) -> str:
        pv = props.get(key)
        if pv is None:
            return ""
        v = pv.value
        return str(v) if not isinstance(v, str) else v

    @staticmethod
    def _get_list(props: dict, key: str) -> list[str]:
        pv = props.get(key)
        if pv is None:
            return []
        v = pv.value
        return list(v) if isinstance(v, list) else [str(v)]

    @staticmethod
    def _get_int(props: dict, key: str) -> int | None:
        pv = props.get(key)
        if pv is None:
            return None
        try:
            return int(pv.value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _get_bool(props: dict, key: str) -> bool:
        pv = props.get(key)
        if pv is None:
            return False
        return bool(pv.value)

    @staticmethod
    def _fmt_temp(props: dict, key: str) -> str | None:
        pv = props.get(key)
        if pv is None:
            return None
        v = pv.value
        if isinstance(v, (int, float)):
            return f"{v} °C"
        return str(v) if v else None

    @staticmethod
    def _fmt_density(props: dict) -> str | None:
        pv = props.get("density")
        if pv is None:
            return None
        v = pv.value
        if isinstance(v, (int, float)):
            return f"{v} g/cm³"
        return str(v) if v else None

    @staticmethod
    def _resolve_h_descriptions(h_codes: set[str]) -> list[str]:
        """Map H-codes to German descriptions via iil-enrichment."""
        try:
            from enrichment.ghs import h_codes_to_descriptions
            return h_codes_to_descriptions(h_codes)
        except ImportError:
            return [code for code in sorted(h_codes)]


def lookup_substance(query: str) -> LookupResult:
    """Convenience function for quick lookups."""
    svc = SubstanceLookupService()
    return svc.lookup(query)
