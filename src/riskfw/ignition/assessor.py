"""
Ignition source assessment matrix per EN 1127-1:2019.

EN 1127-1 defines 13 ignition source types (Section 6).
"""

import logging

from riskfw.ignition.models import IgnitionAssessment, IgnitionRisk

logger = logging.getLogger(__name__)

IGNITION_SOURCES: dict[str, dict] = {
    "S01": {"name": "Heisse Oberflaechen", "clause": "EN 1127-1:2019 Abschn. 6.1"},
    "S02": {"name": "Flammen und heisse Gase", "clause": "EN 1127-1:2019 Abschn. 6.2"},
    "S03": {"name": "Mechanisch erzeugte Funken", "clause": "EN 1127-1:2019 Abschn. 6.3"},
    "S04": {"name": "Elektrische Anlagen", "clause": "EN 1127-1:2019 Abschn. 6.4"},
    "S05": {"name": "Streustrom, kathodischer Korrosionsschutz", "clause": "EN 1127-1:2019 Abschn. 6.5"},
    "S06": {"name": "Statische Elektrizitaet", "clause": "EN 1127-1:2019 Abschn. 6.6"},
    "S07": {"name": "Blitzschlag", "clause": "EN 1127-1:2019 Abschn. 6.7"},
    "S08": {"name": "Elektromagnetische Felder (Hochfrequenz)", "clause": "EN 1127-1:2019 Abschn. 6.8"},
    "S09": {"name": "Elektromagnetische Strahlung (opt.)", "clause": "EN 1127-1:2019 Abschn. 6.9"},
    "S10": {"name": "Ionisierende Strahlung", "clause": "EN 1127-1:2019 Abschn. 6.10"},
    "S11": {"name": "Ultraschall", "clause": "EN 1127-1:2019 Abschn. 6.11"},
    "S12": {"name": "Adiabatische Kompression, Stosswellen", "clause": "EN 1127-1:2019 Abschn. 6.12"},
    "S13": {"name": "Exotherme Reaktionen", "clause": "EN 1127-1:2019 Abschn. 6.13"},
}


class IgnitionSourceMatrix:
    """
    Assessment matrix for all 13 ignition sources per EN 1127-1:2019.
    Stateless -- create once, call assess() multiple times.
    """

    def assess(
        self,
        source_id: str,
        is_present: bool,
        is_effective: bool,
        mitigation: str = "",
    ) -> IgnitionAssessment:
        """
        Assesses a single ignition source.

        Args:
            source_id: Source identifier, e.g. "S01"
            is_present: Whether source exists at location
            is_effective: Whether source can effectively ignite the atmosphere
            mitigation: Description of mitigation measure

        Returns:
            IgnitionAssessment with risk level
        """
        if source_id not in IGNITION_SOURCES:
            raise ValueError(
                f"Unknown ignition source: {source_id!r}. Valid: {list(IGNITION_SOURCES.keys())}"
            )

        source_meta = IGNITION_SOURCES[source_id]

        if not is_present:
            risk_level = IgnitionRisk.NONE
        elif is_effective and not mitigation:
            risk_level = IgnitionRisk.HIGH
        else:
            risk_level = IgnitionRisk.LOW

        logger.debug(
            "[Ignition] source=%s present=%s effective=%s risk=%s",
            source_id, is_present, is_effective, risk_level,
        )

        return IgnitionAssessment(
            source_id=source_id,
            source_name=source_meta["name"],
            is_present=is_present,
            is_effective=is_effective,
            risk_level=risk_level,
            mitigation=mitigation,
            norm_reference="EN 1127-1:2019",
            norm_clause=source_meta["clause"],
        )

    def assess_all(self, assessments: list[dict]) -> list[IgnitionAssessment]:
        """Assesses all provided ignition sources in batch."""
        return [self.assess(**a) for a in assessments]

    @property
    def all_sources(self) -> dict[str, dict]:
        """Returns all 13 ignition source definitions."""
        return IGNITION_SOURCES
