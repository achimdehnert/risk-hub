# src/brandschutz/domain.py
"""
Brandschutz Domain-Objekte (pure Python Dataclasses).

Migriert aus nl2cad-brandschutz.models.
Regelwerke: ASR A2.3, DIN 4102, EN 13501, ATEX/BetrSichV, DIN 14675.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BrandschutzKategorie(StrEnum):
    FLUCHTWEG = "fluchtweg"
    NOTAUSGANG = "notausgang"
    BRANDABSCHNITT = "brandabschnitt"
    BRANDSCHUTZTUER = "brandschutztuer"
    LOESCHEINRICHTUNG = "loescheinrichtung"
    MELDER = "melder"
    RWA = "rwa"
    EX_ZONE = "ex_zone"


class ExZone(StrEnum):
    ZONE_0 = "Zone 0"
    ZONE_1 = "Zone 1"
    ZONE_2 = "Zone 2"
    ZONE_20 = "Zone 20"
    ZONE_21 = "Zone 21"
    ZONE_22 = "Zone 22"


class MaengelSchwere(StrEnum):
    INFO = "info"
    WARNUNG = "warnung"
    KRITISCH = "kritisch"


@dataclass
class Fluchtweg:
    """Erkannter Fluchtweg."""

    name: str = ""
    layer: str = ""
    laenge_m: float = 0.0
    breite_m: float = 0.0
    etage: str = ""
    hat_notausgang: bool = False
    # ASR A2.3 Prüfergebnisse
    laenge_ok: bool | None = None  # Max. 35m ohne Richtungsänderung
    breite_ok: bool | None = None  # Min. 0.875m / 1.0m je Personenzahl


@dataclass
class Brandabschnitt:
    """Erkannter Brandabschnitt."""

    name: str = ""
    layer: str = ""
    feuerwiderstand: str = ""  # F30, F60, F90, REI60, ...
    flaeche_m2: float = 0.0
    etage: str = ""
    # DIN 4102 Prüfergebnis
    klasse_ausreichend: bool | None = None


@dataclass
class Brandschutzeinrichtung:
    """Brandschutzeinrichtung (Feuerlöscher, Hydrant, Sprinkler, Melder)."""

    kategorie: BrandschutzKategorie = BrandschutzKategorie.LOESCHEINRICHTUNG
    name: str = ""
    layer: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    etage: str = ""
    typ: str = ""  # Feuerlöscher, Hydrant, Rauchmelder, ...


@dataclass
class ExBereich:
    """Explosionsgefährdeter Bereich (ATEX/BetrSichV)."""

    zone: ExZone = ExZone.ZONE_2
    name: str = ""
    layer: str = ""
    flaeche_m2: float = 0.0
    etage: str = ""
    medium: str = ""  # Gas, Staub, Nebel


@dataclass
class BrandschutzMangel:
    """Erkannter Mangel / Prüfergebnis."""

    schwere: MaengelSchwere = MaengelSchwere.WARNUNG
    kategorie: BrandschutzKategorie = BrandschutzKategorie.FLUCHTWEG
    beschreibung: str = ""
    regelwerk: str = ""  # "ASR A2.3 §4.2", "DIN 4102-2", ...
    empfehlung: str = ""


@dataclass
class BrandschutzAnalyse:
    """
    Vollständiges Ergebnis einer Brandschutz-Analyse.
    Einstiegspunkt für alle Downstream-Verarbeitung (Reports, Exports).
    """

    fluchtwege: list[Fluchtweg] = field(default_factory=list)
    brandabschnitte: list[Brandabschnitt] = field(default_factory=list)
    einrichtungen: list[Brandschutzeinrichtung] = field(default_factory=list)
    ex_bereiche: list[ExBereich] = field(default_factory=list)
    maengel: list[BrandschutzMangel] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)

    @property
    def kritische_maengel(self) -> list[BrandschutzMangel]:
        return [m for m in self.maengel if m.schwere == MaengelSchwere.KRITISCH]

    @property
    def hat_kritische_maengel(self) -> bool:
        return len(self.kritische_maengel) > 0

    @property
    def loescheinrichtungen_count(self) -> int:
        return sum(
            1 for e in self.einrichtungen if e.kategorie == BrandschutzKategorie.LOESCHEINRICHTUNG
        )

    def to_dict(self) -> dict:
        return {
            "fluchtwege_count": len(self.fluchtwege),
            "brandabschnitte_count": len(self.brandabschnitte),
            "einrichtungen_count": len(self.einrichtungen),
            "ex_bereiche_count": len(self.ex_bereiche),
            "maengel_count": len(self.maengel),
            "kritische_maengel_count": len(self.kritische_maengel),
            "hat_kritische_maengel": self.hat_kritische_maengel,
            "fluchtwege": [
                {
                    "name": f.name,
                    "laenge_m": f.laenge_m,
                    "breite_m": f.breite_m,
                    "laenge_ok": f.laenge_ok,
                    "breite_ok": f.breite_ok,
                    "hat_notausgang": f.hat_notausgang,
                }
                for f in self.fluchtwege
            ],
            "maengel": [
                {
                    "schwere": m.schwere.value,
                    "beschreibung": m.beschreibung,
                    "regelwerk": m.regelwerk,
                    "empfehlung": m.empfehlung,
                }
                for m in self.maengel
            ],
            "warnungen": self.warnungen,
        }
