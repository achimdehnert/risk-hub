# src/explosionsschutz/services/zone_classification.py
"""
Regelbasierte Zoneneinteilung nach TRGS 721, Abschnitt 4.

Eingabe: Freisetzungsgrad + Lüftungsart + Atmosphären-Typ
Ausgabe: ZoneProposal mit Zonentyp, Konfidenz und Begründung.

Erweiterbar: Regeln können in der DB (ZoneClassificationRule) gepflegt werden.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class ReleaseGrade(StrEnum):
    CONTINUOUS = "continuous"
    PRIMARY = "primary"
    SECONDARY = "secondary"


class VentilationType(StrEnum):
    NATURAL = "natural"
    TECHNICAL_DILUTION = "technical_dilution"
    LOCAL_EXHAUST = "local_exhaust"
    INERTIZATION = "inertization"
    NONE = "none"


class AtmosphereType(StrEnum):
    GAS = "gas"
    DUST = "dust"


@dataclass(frozen=True)
class ZoneProposal:
    zone_type: str  # "0","1","2","20","21","22","none"
    confidence: Literal["high", "medium", "low"]
    justification: str
    trgs_reference: str
    ventilation_reduction: bool = False


# ---------------------------------------------------------------------------
# Regelmatrix nach TRGS 721 Abschnitt 4 (vereinfacht)
# Schlüssel: (release_grade, ventilation_type)
# ---------------------------------------------------------------------------

_GAS_RULES: dict[tuple[str, str], ZoneProposal] = {
    # Kontinuierliche Freisetzung
    ("continuous", "none"): ZoneProposal(
        zone_type="0",
        confidence="high",
        justification="Ständige Freisetzung ohne Lüftung → Zone 0 unvermeidbar.",
        trgs_reference="TRGS 721 Abschnitt 4.2",
    ),
    ("continuous", "natural"): ZoneProposal(
        zone_type="0",
        confidence="high",
        justification=(
            "Ständige Freisetzung mit natürlicher Lüftung: Innenbereich Zone 0, "
            "Umgebung Zone 1."
        ),
        trgs_reference="TRGS 721 Abschnitt 4.2",
    ),
    ("continuous", "technical_dilution"): ZoneProposal(
        zone_type="1",
        confidence="medium",
        justification=(
            "Ständige Freisetzung mit technischer Lüftung kann Zone auf 1 reduzieren "
            "– Nachweis erforderlich."
        ),
        trgs_reference="TRGS 721 Abschnitt 4.2, TRGS 722",
        ventilation_reduction=True,
    ),
    ("continuous", "inertization"): ZoneProposal(
        zone_type="none",
        confidence="high",
        justification=(
            "Inertisierung vermeidet explosionsfähige Atmosphäre vollständig, "
            "sofern Wirksamkeit nachgewiesen (Gaswarnanlage + Monitoring)."
        ),
        trgs_reference="TRGS 722 Abschnitt 5",
        ventilation_reduction=True,
    ),
    # Primäre Freisetzung (gelegentlich im Normalbetrieb)
    ("primary", "none"): ZoneProposal(
        zone_type="1",
        confidence="high",
        justification="Gelegentliche Freisetzung ohne Lüftung → Zone 1.",
        trgs_reference="TRGS 721 Abschnitt 4.3",
    ),
    ("primary", "natural"): ZoneProposal(
        zone_type="1",
        confidence="high",
        justification="Gelegentliche Freisetzung mit natürlicher Lüftung → Zone 1.",
        trgs_reference="TRGS 721 Abschnitt 4.3",
    ),
    ("primary", "technical_dilution"): ZoneProposal(
        zone_type="2",
        confidence="high",
        justification=(
            "Gelegentliche Freisetzung mit guter technischer Lüftung → Zone 2. "
            "Lüftungswirksamkeit muss nachgewiesen werden."
        ),
        trgs_reference="TRGS 721 Abschnitt 4.3, TRGS 722",
        ventilation_reduction=True,
    ),
    ("primary", "local_exhaust"): ZoneProposal(
        zone_type="2",
        confidence="medium",
        justification=(
            "Objektabsaugung bei gelegentlicher Freisetzung: "
            "Zone 2 im verbleibenden Bereich, wenn Wirksamkeit belegt."
        ),
        trgs_reference="TRGS 721 Abschnitt 4.3",
        ventilation_reduction=True,
    ),
    ("primary", "inertization"): ZoneProposal(
        zone_type="none",
        confidence="high",
        justification="Inertisierung verhindert Zone bei gelegentlicher Freisetzung.",
        trgs_reference="TRGS 722 Abschnitt 5",
        ventilation_reduction=True,
    ),
    # Sekundäre Freisetzung (selten, nur bei Störungen)
    ("secondary", "none"): ZoneProposal(
        zone_type="2",
        confidence="high",
        justification="Seltene Freisetzung ohne Lüftung → Zone 2.",
        trgs_reference="TRGS 721 Abschnitt 4.4",
    ),
    ("secondary", "natural"): ZoneProposal(
        zone_type="2",
        confidence="high",
        justification="Seltene Freisetzung mit natürlicher Lüftung → Zone 2.",
        trgs_reference="TRGS 721 Abschnitt 4.4",
    ),
    ("secondary", "technical_dilution"): ZoneProposal(
        zone_type="none",
        confidence="medium",
        justification=(
            "Seltene Freisetzung mit guter technischer Lüftung: "
            "Zone kann auf ‚keine Zone' reduziert werden. Nachweis erforderlich."
        ),
        trgs_reference="TRGS 721 Abschnitt 4.4, TRGS 722",
        ventilation_reduction=True,
    ),
    ("secondary", "local_exhaust"): ZoneProposal(
        zone_type="none",
        confidence="medium",
        justification="Objektabsaugung bei seltener Freisetzung kann Zonenbildung vermeiden.",
        trgs_reference="TRGS 721 Abschnitt 4.4",
        ventilation_reduction=True,
    ),
    ("secondary", "inertization"): ZoneProposal(
        zone_type="none",
        confidence="high",
        justification="Inertisierung verhindert Zonenbildung bei seltener Freisetzung.",
        trgs_reference="TRGS 722 Abschnitt 5",
        ventilation_reduction=True,
    ),
}

# Staubzonen (vereinfacht nach TRGS 746)
_DUST_RULES: dict[tuple[str, str], ZoneProposal] = {
    ("continuous", "none"): ZoneProposal(
        zone_type="20",
        confidence="high",
        justification="Ständige Staubfreisetzung → Zone 20.",
        trgs_reference="TRGS 746 Abschnitt 4",
    ),
    ("primary", "none"): ZoneProposal(
        zone_type="21",
        confidence="high",
        justification="Gelegentliche Staubfreisetzung → Zone 21.",
        trgs_reference="TRGS 746 Abschnitt 4",
    ),
    ("primary", "technical_dilution"): ZoneProposal(
        zone_type="22",
        confidence="medium",
        justification="Gelegentliche Staubfreisetzung mit Absaugung → Zone 22.",
        trgs_reference="TRGS 746 Abschnitt 4",
        ventilation_reduction=True,
    ),
    ("secondary", "none"): ZoneProposal(
        zone_type="22",
        confidence="high",
        justification="Seltene Staubfreisetzung → Zone 22.",
        trgs_reference="TRGS 746 Abschnitt 4",
    ),
    ("secondary", "technical_dilution"): ZoneProposal(
        zone_type="none",
        confidence="medium",
        justification="Seltene Staubfreisetzung mit Absaugung: Zone kann entfallen.",
        trgs_reference="TRGS 746 Abschnitt 4",
        ventilation_reduction=True,
    ),
}


class ZoneClassificationEngine:
    """
    Schlägt eine Zoneneinteilung basierend auf Freisetzungsgrad und Lüftung vor.
    Ergebnis ist ein Vorschlag – der Sachverständige muss final entscheiden.
    """

    def propose(
        self,
        release_grade: str,
        ventilation_type: str,
        atmosphere_type: str = "gas",
    ) -> ZoneProposal:
        """
        Gibt ZoneProposal zurück.
        Falls keine exakte Regel: Fallback auf konservative Schätzung.
        """
        rules = _GAS_RULES if atmosphere_type == "gas" else _DUST_RULES
        key = (release_grade, ventilation_type)

        if key in rules:
            return rules[key]

        # Konservativer Fallback
        fallback_zone = "1" if atmosphere_type == "gas" else "21"
        return ZoneProposal(
            zone_type=fallback_zone,
            confidence="low",
            justification=(
                f"Keine exakte Regel für Kombination "
                f"(Freisetzungsgrad='{release_grade}', Lüftung='{ventilation_type}'). "
                "Konservativer Vorschlag – Überprüfung durch Sachverständigen erforderlich."
            ),
            trgs_reference="TRGS 721 allgemein",
        )

    def get_required_equipment_category(self, zone_type: str) -> str:
        """Mindest-ATEX-Kategorie für eine Zone."""
        mapping = {
            "0": "1G",
            "1": "2G",
            "2": "3G",
            "20": "1D",
            "21": "2D",
            "22": "3D",
            "none": "—",
        }
        return mapping.get(zone_type, "—")
