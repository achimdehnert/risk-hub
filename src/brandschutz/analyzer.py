# src/brandschutz/analyzer.py
"""
BrandschutzAnalyzer — Haupt-Einstiegspunkt für Brandschutz-Analyse aus IFC/DXF.

Migriert aus nl2cad-brandschutz.analyzer.
Orchestriert Layer-Erkennung und Regelwerk-Checks.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from brandschutz.constants import (
    BRANDABSCHNITT_KEYWORDS,
    BRANDSCHUTZTUER_KEYWORDS,
    FEUERWIDERSTANDSKLASSEN,
    FLUCHTWEG_KEYWORDS,
    LOESCHEINRICHTUNG_KEYWORDS,
    NOTAUSGANG_KEYWORDS,
)
from brandschutz.domain import (
    Brandabschnitt,
    BrandschutzAnalyse,
    Brandschutzeinrichtung,
    BrandschutzKategorie,
    Fluchtweg,
)
from brandschutz.rules.asr_a23 import ASRA23Validator
from brandschutz.rules.din4102 import DIN4102Validator

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@runtime_checkable
class IFCFloor(Protocol):
    """Protocol for IFC floor data."""

    name: str
    doors: list


@runtime_checkable
class IFCModel(Protocol):
    """Protocol for IFC model data (replaces nl2cad.core.models.ifc.IFCModel)."""

    floors: list


class BrandschutzAnalyzer:
    """
    Analysiert IFC- oder DXF-Modelle auf Brandschutz-Relevanz.

    Erkennt:
    - Fluchtwege und Rettungswege (ASR A2.3)
    - Brandabschnitte mit Feuerwiderstandsklassen (DIN 4102)
    - Brandschutztüren (T30, T60, T90)
    - Löscheinrichtungen, Melder, RWA
    - Ex-Zonen (ATEX/BetrSichV)

    Usage:
        analyzer = BrandschutzAnalyzer()

        # IFC
        result = analyzer.analyze_ifc(ifc_model)

        # DXF (ezdxf doc)
        result = analyzer.analyze_dxf(dxf_doc, etage="EG")

        for mangel in result.kritische_maengel:
            logger.error(f"KRITISCH: {mangel.beschreibung} [{mangel.regelwerk}]")
    """

    def __init__(self) -> None:
        self._asr_validator = ASRA23Validator()
        self._din_validator = DIN4102Validator()

    def analyze_ifc(self, model: IFCModel) -> BrandschutzAnalyse:
        """Analysiert IFCModel auf Brandschutz-Elemente."""
        analyse = BrandschutzAnalyse()

        for floor in model.floors:
            etage = floor.name

            # Brandschutztüren aus IFC-Türen
            for door in floor.doors:
                if door.is_fire_door or door.fire_rating:
                    einrichtung = Brandschutzeinrichtung(
                        kategorie=BrandschutzKategorie.BRANDSCHUTZTUER,
                        name=door.name,
                        typ=door.fire_rating,
                        etage=etage,
                    )
                    analyse.einrichtungen.append(einrichtung)

                    # Brandabschnitt-Vermutung bei Brandschutztür
                    brandabschnitt = Brandabschnitt(
                        name=f"Brandabschnitt via {door.name}",
                        feuerwiderstand=door.fire_rating,
                        etage=etage,
                    )
                    analyse.brandabschnitte.append(brandabschnitt)

        # Regelwerk-Checks
        analyse = self._asr_validator.validate(analyse)
        analyse = self._din_validator.validate(analyse)

        logger.info(
            "[BrandschutzAnalyzer] IFC: %d Fluchtwege, %d Brandabschnitte, %d Mängel",
            len(analyse.fluchtwege),
            len(analyse.brandabschnitte),
            len(analyse.maengel),
        )
        return analyse

    def analyze_dxf(self, doc, etage: str = "EG") -> BrandschutzAnalyse:
        """Analysiert ezdxf-Dokument auf Brandschutz-Elemente."""
        analyse = BrandschutzAnalyse()

        try:
            msp = doc.modelspace()
        except Exception as e:
            analyse.warnungen.append(f"DXF Modelspace nicht lesbar: {e}")
            return analyse

        # Layer-basierte Erkennung
        for entity in msp:
            try:
                layer_name = entity.dxf.layer.lower() if hasattr(entity.dxf, "layer") else ""
                self._process_entity(entity, layer_name, etage, analyse)
            except Exception as e:
                logger.debug("[BrandschutzAnalyzer] Entity skip: %s", e)

        # Regelwerk-Checks
        analyse = self._asr_validator.validate(analyse)
        analyse = self._din_validator.validate(analyse)

        logger.info(
            "[BrandschutzAnalyzer] DXF %s: %d Fluchtwege, %d Mängel",
            etage,
            len(analyse.fluchtwege),
            len(analyse.maengel),
        )
        return analyse

    def _process_entity(
        self,
        entity,
        layer_name: str,
        etage: str,
        analyse: BrandschutzAnalyse,
    ) -> None:
        """Verarbeitet eine DXF-Entity basierend auf Layer-Keywords."""
        if any(kw in layer_name for kw in FLUCHTWEG_KEYWORDS):
            length = self._estimate_length(entity)
            fluchtweg = Fluchtweg(
                name=entity.dxf.layer,
                layer=entity.dxf.layer,
                laenge_m=length,
                etage=etage,
            )
            analyse.fluchtwege.append(fluchtweg)

        elif any(kw in layer_name for kw in NOTAUSGANG_KEYWORDS):
            fluchtweg = Fluchtweg(
                name=entity.dxf.layer,
                layer=entity.dxf.layer,
                hat_notausgang=True,
                etage=etage,
            )
            analyse.fluchtwege.append(fluchtweg)

        elif any(kw in layer_name for kw in BRANDABSCHNITT_KEYWORDS):
            feuerwiderstand = self._extract_feuerwiderstand(entity.dxf.layer)
            brandabschnitt = Brandabschnitt(
                name=entity.dxf.layer,
                layer=entity.dxf.layer,
                feuerwiderstand=feuerwiderstand,
                etage=etage,
            )
            analyse.brandabschnitte.append(brandabschnitt)

        elif any(kw in layer_name for kw in LOESCHEINRICHTUNG_KEYWORDS):
            einrichtung = Brandschutzeinrichtung(
                kategorie=BrandschutzKategorie.LOESCHEINRICHTUNG,
                name=entity.dxf.layer,
                layer=entity.dxf.layer,
                etage=etage,
            )
            analyse.einrichtungen.append(einrichtung)

        elif any(kw in layer_name for kw in BRANDSCHUTZTUER_KEYWORDS):
            typ = self._extract_tuerklasse(layer_name)
            einrichtung = Brandschutzeinrichtung(
                kategorie=BrandschutzKategorie.BRANDSCHUTZTUER,
                name=entity.dxf.layer,
                layer=entity.dxf.layer,
                typ=typ,
                etage=etage,
            )
            analyse.einrichtungen.append(einrichtung)

    def _estimate_length(self, entity) -> float:
        """Schätzt Länge einer Entity (LINE, LWPOLYLINE). 0.0 bei unbekanntem Typ."""
        try:
            if entity.dxftype() == "LINE":
                dx = entity.dxf.end.x - entity.dxf.start.x
                dy = entity.dxf.end.y - entity.dxf.start.y
                return (dx**2 + dy**2) ** 0.5
            if entity.dxftype() == "LWPOLYLINE":
                pts = list(entity.get_points(format="xy"))
                length = 0.0
                for i in range(len(pts) - 1):
                    dx = pts[i + 1][0] - pts[i][0]
                    dy = pts[i + 1][1] - pts[i][1]
                    length += (dx**2 + dy**2) ** 0.5
                return length
            logger.debug(
                "[BrandschutzAnalyzer] Unbekannter Entity-Typ für Länge: %s",
                entity.dxftype(),
            )
        except Exception as e:
            logger.debug("[BrandschutzAnalyzer] Längenberechnung fehlgeschlagen: %s", e)
        return 0.0

    def _extract_feuerwiderstand(self, layer_name: str) -> str:
        """Extrahiert Feuerwiderstandsklasse aus Layer-Namen."""
        for klasse in FEUERWIDERSTANDSKLASSEN:
            if klasse.lower() in layer_name.lower():
                return klasse
        return ""

    def _extract_tuerklasse(self, layer_name: str) -> str:
        """Extrahiert Türklasse (T30/T60/T90) aus Layer-Namen."""
        match = re.search(r"t(30|60|90|120)", layer_name.lower())
        if match:
            return f"T{match.group(1)}"
        return ""
