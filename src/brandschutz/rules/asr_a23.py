# src/brandschutz/rules/asr_a23.py
"""
Regelwerk-Checks nach ASR A2.3 "Fluchtwege und Notausgänge".

Migriert aus nl2cad-brandschutz.rules.asr_a23.

Quellen:
- ASR A2.3 (2022): Technische Regeln für Arbeitsstätten
- § 4: Mindestbreiten von Fluchtwegen
- § 5: Länge von Fluchtwegen (max. 35m, Richtungsänderung max. +25m)
"""

from __future__ import annotations

import logging

from brandschutz.constants import (
    ASR_A23_VERSION,
    MAX_FLUCHTWEG_LAENGE_M,
    MAX_FLUCHTWEG_LAENGE_MIT_ABZWEIG_M,
    MIN_BREITE_AB_5_PERSONEN_M,
    MIN_BREITE_STANDARD_M,
)
from brandschutz.domain import (
    BrandschutzAnalyse,
    BrandschutzKategorie,
    BrandschutzMangel,
    Fluchtweg,
    MaengelSchwere,
)

logger = logging.getLogger(__name__)


class ASRA23Validator:
    """
    Prüft Fluchtwege gegen ASR A2.3.

    Checks:
    1. Fluchtweglänge <= 35m (ohne Richtungsänderung)
    2. Fluchtweglänge <= 60m (mit Richtungsänderung)
    3. Mindestbreite 0.875m / 1.0m / 1.2m
    4. Mindestens ein Notausgang pro Fluchtweg
    """

    def validate(self, analyse: BrandschutzAnalyse) -> BrandschutzAnalyse:
        """Führt alle ASR A2.3 Checks durch und ergänzt analyse.maengel."""

        for fluchtweg in analyse.fluchtwege:
            self._check_laenge(fluchtweg, analyse)
            self._check_breite(fluchtweg, analyse)

        self._check_notausgang(analyse)

        if not analyse.fluchtwege:
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.WARNUNG,
                    kategorie=BrandschutzKategorie.FLUCHTWEG,
                    beschreibung="Keine Fluchtwege erkannt",
                    regelwerk=f"ASR A2.3 § 3 ({ASR_A23_VERSION})",
                    empfehlung=(
                        "Fluchtwege in CAD-Datei als"
                        " dedizierte Layer kennzeichnen"
                    ),
                )
            )

        return analyse

    def _check_laenge(
        self, fluchtweg: Fluchtweg, analyse: BrandschutzAnalyse
    ) -> None:
        """§ 5 ASR A2.3: Maximale Weglänge."""
        if fluchtweg.laenge_m <= 0:
            fluchtweg.laenge_ok = None
            return

        if fluchtweg.laenge_m > MAX_FLUCHTWEG_LAENGE_MIT_ABZWEIG_M:
            fluchtweg.laenge_ok = False
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.KRITISCH,
                    kategorie=BrandschutzKategorie.FLUCHTWEG,
                    beschreibung=(
                        f"Fluchtweg '{fluchtweg.name}':"
                        f" Länge {fluchtweg.laenge_m:.1f}m "
                        f"überschreitet max."
                        f" {MAX_FLUCHTWEG_LAENGE_MIT_ABZWEIG_M}m"
                    ),
                    regelwerk=(
                        f"ASR A2.3 § 5 Abs. 2 ({ASR_A23_VERSION})"
                    ),
                    empfehlung=(
                        "Zusätzlichen Notausgang innerhalb"
                        " von 35m einplanen"
                    ),
                )
            )
        elif fluchtweg.laenge_m > MAX_FLUCHTWEG_LAENGE_M:
            fluchtweg.laenge_ok = True
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.WARNUNG,
                    kategorie=BrandschutzKategorie.FLUCHTWEG,
                    beschreibung=(
                        f"Fluchtweg '{fluchtweg.name}':"
                        f" Länge {fluchtweg.laenge_m:.1f}m "
                        f"> {MAX_FLUCHTWEG_LAENGE_M}m"
                        " — Richtungsänderung erforderlich"
                    ),
                    regelwerk=(
                        f"ASR A2.3 § 5 Abs. 1 ({ASR_A23_VERSION})"
                    ),
                    empfehlung=(
                        "Richtungsänderung dokumentieren"
                        " oder Weglänge kürzen"
                    ),
                )
            )
        else:
            fluchtweg.laenge_ok = True

    def _check_breite(
        self, fluchtweg: Fluchtweg, analyse: BrandschutzAnalyse
    ) -> None:
        """§ 4 ASR A2.3: Mindestbreite."""
        if fluchtweg.breite_m <= 0:
            fluchtweg.breite_ok = None
            return

        if fluchtweg.breite_m < MIN_BREITE_STANDARD_M:
            fluchtweg.breite_ok = False
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.KRITISCH,
                    kategorie=BrandschutzKategorie.FLUCHTWEG,
                    beschreibung=(
                        f"Fluchtweg '{fluchtweg.name}':"
                        f" Breite {fluchtweg.breite_m:.2f}m "
                        f"unterschreitet Mindestmaß"
                        f" {MIN_BREITE_STANDARD_M}m"
                    ),
                    regelwerk=(
                        f"ASR A2.3 § 4 Abs. 2 ({ASR_A23_VERSION})"
                    ),
                    empfehlung=(
                        f"Fluchtweg auf mind."
                        f" {MIN_BREITE_STANDARD_M}m verbreitern"
                    ),
                )
            )
        elif fluchtweg.breite_m < MIN_BREITE_AB_5_PERSONEN_M:
            fluchtweg.breite_ok = True
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.WARNUNG,
                    kategorie=BrandschutzKategorie.FLUCHTWEG,
                    beschreibung=(
                        f"Fluchtweg '{fluchtweg.name}':"
                        f" Breite {fluchtweg.breite_m:.2f}m "
                        f"— bei >5 Personen mind."
                        f" {MIN_BREITE_AB_5_PERSONEN_M}m"
                        " erforderlich"
                    ),
                    regelwerk=(
                        f"ASR A2.3 § 4 Abs. 3 ({ASR_A23_VERSION})"
                    ),
                    empfehlung=(
                        "Personenzahl prüfen"
                        " und ggf. verbreitern"
                    ),
                )
            )
        else:
            fluchtweg.breite_ok = True

    def _check_notausgang(
        self, analyse: BrandschutzAnalyse
    ) -> None:
        """§ 6 ASR A2.3: Mindestens ein Notausgang."""
        notausgaenge = [
            e for e in analyse.fluchtwege if e.hat_notausgang
        ]
        if not notausgaenge:
            analyse.maengel.append(
                BrandschutzMangel(
                    schwere=MaengelSchwere.KRITISCH,
                    kategorie=BrandschutzKategorie.NOTAUSGANG,
                    beschreibung="Kein Notausgang erkannt",
                    regelwerk=(
                        f"ASR A2.3 § 6 Abs. 1 ({ASR_A23_VERSION})"
                    ),
                    empfehlung=(
                        "Mindestens einen Notausgang"
                        " je Nutzungseinheit einplanen"
                    ),
                )
            )
