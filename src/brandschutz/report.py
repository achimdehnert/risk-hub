# src/brandschutz/report.py
"""
BrandschutzkonzeptReport — Gesamtergebnis.

Migriert aus nl2cad-brandschutz.report.

Aggregiert:
  - GebaeudeklasseResult
  - BrandschutzAnalyse
  - ExplosionsschutzDokument (optional)

BeurteilungsStatus (ADR B-06): kein bool|None.
Kein stiller Fallback: fehlende Teilberichte erzeugen NICHT_BEURTEILBAR.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

from brandschutz.domain import BrandschutzAnalyse
from brandschutz.explosionsschutz import (
    BeurteilungsStatus,
    ExplosionsschutzDokument,
)
from brandschutz.gebaeudeklasse import GebaeudeklasseResult

logger = logging.getLogger(__name__)


@dataclass
class BrandschutzkonzeptReport:
    """
    Vollständiger Brandschutzkonzept-Report für ein Gebäude.

    Felder:
        gebaeudeklasse: GK-Ermittlung (MBO § 2)
        analyse: Layer-Analyse (Fluchtwege, Brandabschnitte, Mängel)
        explosionsschutz: ESD nach BetrSichV (optional)
        status: Gesamtbeurteilung
        erstellt_am: Zeitpunkt der Report-Erstellung
        report_hash: SHA256 über Eingabedaten (Reproduzierbarkeit)
    """

    gebaeudeklasse: GebaeudeklasseResult | None = None
    analyse: BrandschutzAnalyse | None = None
    explosionsschutz: ExplosionsschutzDokument | None = None
    status: BeurteilungsStatus = BeurteilungsStatus.VORPRUEFUNG
    erstellt_am: str = ""
    report_hash: str = ""
    meldungen: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.erstellt_am:
            self.erstellt_am = datetime.now().isoformat(timespec="seconds")
        self._berechne_status()

    def _berechne_status(self) -> None:
        """Bestimmt Gesamtstatus aus Teilberichten."""
        if self.analyse is None and self.gebaeudeklasse is None:
            self.status = BeurteilungsStatus.NICHT_BEURTEILBAR
            self.meldungen.append(
                "Keine Analyse-Daten vorhanden"
                " — Beurteilung nicht möglich"
            )
            return

        if self.analyse and self.analyse.hat_kritische_maengel:
            self.status = BeurteilungsStatus.ABGELEHNT
            count = len(self.analyse.kritische_maengel)
            self.meldungen.append(
                f"{count} kritische Mängel — Nachbesserung erforderlich"
            )
            return

        from brandschutz.gebaeudeklasse import Gebaeudeklasse

        if (
            self.gebaeudeklasse
            and self.gebaeudeklasse.gebaeudeklasse
            == Gebaeudeklasse.UNBEKANNT
        ):
            self.status = BeurteilungsStatus.NICHT_BEURTEILBAR
            self.meldungen.append(
                "Gebäudeklasse nicht ermittelbar"
                " — Beurteilung eingeschränkt"
            )
            return

        self.status = BeurteilungsStatus.VORPRUEFUNG
        self.meldungen.append(
            "Vorprüfung abgeschlossen"
            " — fachliche Bestätigung ausstehend"
        )

    def berechne_hash(self) -> str:
        """SHA256 über serialisierte Eingabedaten."""
        data = {
            "gk": (
                self.gebaeudeklasse.to_dict()
                if self.gebaeudeklasse
                else None
            ),
            "analyse": (
                self.analyse.to_dict() if self.analyse else None
            ),
            "esd": (
                self.explosionsschutz.to_dict()
                if self.explosionsschutz
                else None
            ),
        }
        raw = json.dumps(data, sort_keys=True, default=str)
        self.report_hash = hashlib.sha256(raw.encode()).hexdigest()
        return self.report_hash

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "erstellt_am": self.erstellt_am,
            "report_hash": self.report_hash,
            "meldungen": self.meldungen,
            "gebaeudeklasse": (
                self.gebaeudeklasse.to_dict()
                if self.gebaeudeklasse
                else None
            ),
            "analyse": (
                self.analyse.to_dict() if self.analyse else None
            ),
            "explosionsschutz": (
                self.explosionsschutz.to_dict()
                if self.explosionsschutz
                else None
            ),
        }
