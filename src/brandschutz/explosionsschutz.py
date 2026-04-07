# src/brandschutz/explosionsschutz.py
"""
ExplosionsschutzDokument (ESD) nach BetrSichV § 6 Abs. 9.

Migriert aus nl2cad-brandschutz.explosionsschutz.

Invarianten (ADR B-05):
  - betrieb_name darf nicht leer sein
  - erstellungsdatum muss ISO-Format haben (YYYY-MM-DD)
  - naechste_pruefung > erstellungsdatum
  - ex_bereiche darf nicht leer sein wenn ESD ausgefüllt

BeurteilungsStatus (ADR B-06):
  - Kein bool|None — expliziter Enum
  - VORPRUEFUNG: Noch keine rechtlich belastbare Aussage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from brandschutz.constants import (
    ATEX_ZONE_ZU_GERAETEKATEGORIE,
    BETRSICHV_VERSION,
    EN60079_10_1_VERSION,
    ESD_PFLICHTFELDER,
    TRBS2152_VERSION,
)
from brandschutz.domain import ExBereich, ExZone

logger = logging.getLogger(__name__)


class BeurteilungsStatus(StrEnum):
    """
    Beurteilungsstatus einer Analyse — kein bool|None (ADR B-06).

    VORPRUEFUNG:      Daten vorhanden, aber noch keine rechtsverbindliche Aussage.
    NICHT_BEURTEILBAR: Datenbasis ungenügend für Beurteilung.
    BESTAETIGT:       Durch befugten Sachverständigen bestätigt (außerhalb System).
    ABGELEHNT:        Fachlich abgelehnt / Mangel festgestellt.
    """

    VORPRUEFUNG = "vorpruefung"
    NICHT_BEURTEILBAR = "nicht_beurteilbar"
    BESTAETIGT = "bestaetigt"
    ABGELEHNT = "abgelehnt"


@dataclass
class ExplosionsschutzMassnahme:
    """Einzelne Schutzmassnahme nach TRBS 2152 Rangfolge."""

    prioritaet: int = 1  # 1=primär, 2=sekundär, 3=tertiär
    typ: str = ""  # "Vermeidung", "Erschwerung", "Schutzeinrichtung"
    beschreibung: str = ""
    umgesetzt: bool = False
    norm_referenz: str = ""  # z.B. "TRBS 2152 Teil 2"


@dataclass
class ExplosionsschutzDokument:
    """
    Explosionsschutzdokument nach BetrSichV § 6 Abs. 9.

    Invarianten (werden in __post_init__ geprüft):
    - betrieb_name: nicht leer
    - erstellungsdatum: gültig, nicht in der Zukunft
    - naechste_pruefung: nach erstellungsdatum
    - ex_bereiche: mindestens 1 Eintrag wenn Dokument erstellt wird

    Alle Pflichtfelder gemäß ESD_PFLICHTFELDER aus constants.py.
    """

    betrieb_name: str = ""
    betriebsstaette: str = ""
    erstellungsdatum: str = ""  # ISO: YYYY-MM-DD
    erstellt_von: str = ""  # Name/Funktion des Erstellers
    naechste_pruefung: str = ""  # ISO: YYYY-MM-DD
    gefaehrdungsbeurteilung: str = ""  # Freitext oder Referenz-Nr.
    explosionsfaehige_atmosphaere_moeglich: bool = False

    ex_bereiche: list[ExBereich] = field(default_factory=list)
    massnahmen: list[ExplosionsschutzMassnahme] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)

    norm_version_betrsichv: str = BETRSICHV_VERSION
    norm_version_en60079: str = EN60079_10_1_VERSION
    norm_version_trbs: str = TRBS2152_VERSION

    def __post_init__(self) -> None:
        """Invarianten-Prüfung — kein stilles leeres ESD (ADR B-05)."""
        errors: list[str] = []

        if not self.betrieb_name.strip():
            errors.append("betrieb_name darf nicht leer sein")

        if self.erstellungsdatum:
            try:
                erstellt = date.fromisoformat(self.erstellungsdatum)
                if erstellt > date.today():
                    errors.append(f"erstellungsdatum {self.erstellungsdatum} liegt in der Zukunft")
            except ValueError:
                errors.append(
                    f"erstellungsdatum '{self.erstellungsdatum}' ist kein gültiges ISO-Datum"
                )

        if self.naechste_pruefung and self.erstellungsdatum:
            try:
                erstellt = date.fromisoformat(self.erstellungsdatum)
                pruefung = date.fromisoformat(self.naechste_pruefung)
                if pruefung <= erstellt:
                    errors.append(
                        f"naechste_pruefung {self.naechste_pruefung} "
                        f"muss nach erstellungsdatum"
                        f" {self.erstellungsdatum} liegen"
                    )
            except ValueError:
                pass  # Bereits oben gefangen

        if errors:
            raise ValueError(f"ExplosionsschutzDokument Invarianten verletzt: {'; '.join(errors)}")

        logger.debug(
            "[ESD] Dokument erstellt: betrieb=%r datum=%s bereiche=%d",
            self.betrieb_name,
            self.erstellungsdatum,
            len(self.ex_bereiche),
        )

    def ist_vollstaendig(self) -> bool:
        """Prüft ob alle BetrSichV-Pflichtfelder ausgefüllt sind."""
        for feldname in ESD_PFLICHTFELDER:
            wert = getattr(self, feldname, None)
            if wert is None or wert == "" or wert == []:
                logger.debug("[ESD] Pflichtfeld fehlt: %s", feldname)
                return False
        return bool(self.ex_bereiche)

    def geraetekategorie_fuer_zone(self, zone: ExZone) -> str:
        """Gibt ATEX-Gerätekategorie für eine Zone zurück."""
        return ATEX_ZONE_ZU_GERAETEKATEGORIE.get(zone.value, "unbekannt")

    def to_dict(self) -> dict:
        return {
            "betrieb_name": self.betrieb_name,
            "betriebsstaette": self.betriebsstaette,
            "erstellungsdatum": self.erstellungsdatum,
            "erstellt_von": self.erstellt_von,
            "naechste_pruefung": self.naechste_pruefung,
            "ist_vollstaendig": self.ist_vollstaendig(),
            "ex_bereiche_anzahl": len(self.ex_bereiche),
            "massnahmen_anzahl": len(self.massnahmen),
            "norm_betrsichv": self.norm_version_betrsichv,
            "norm_en60079": self.norm_version_en60079,
            "norm_trbs": self.norm_version_trbs,
            "warnungen": self.warnungen,
        }
