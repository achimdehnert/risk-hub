# src/brandschutz/rules/din4102.py
"""
Regelwerk-Checks nach DIN 4102 / EN 13501 Feuerwiderstand.

Migriert aus nl2cad-brandschutz.rules.din4102.
"""

from __future__ import annotations

from brandschutz.constants import ALLE_FEUERWIDERSTANDSKLASSEN
from brandschutz.domain import BrandschutzAnalyse


class DIN4102Validator:
    """Prüft Brandabschnitte auf korrekte Feuerwiderstandsklassen."""

    VALID_KLASSEN: frozenset[str] = ALLE_FEUERWIDERSTANDSKLASSEN

    def validate(self, analyse: BrandschutzAnalyse) -> BrandschutzAnalyse:
        """Prüft Feuerwiderstandsklassen der erkannten Brandabschnitte."""
        for abschnitt in analyse.brandabschnitte:
            if abschnitt.feuerwiderstand:
                abschnitt.klasse_ausreichend = (
                    abschnitt.feuerwiderstand.upper() in self.VALID_KLASSEN
                )
                if not abschnitt.klasse_ausreichend:
                    analyse.warnungen.append(
                        f"Unbekannte Feuerwiderstandsklasse: "
                        f"'{abschnitt.feuerwiderstand}'"
                        f" bei '{abschnitt.name}'"
                    )
        return analyse
