"""Report dataclasses for structured export of calculation results."""

from dataclasses import dataclass, field

from riskfw.ignition.models import IgnitionAssessment, IgnitionRisk


@dataclass
class ZoneCalculationReport:
    """
    Structured proof document for a TRGS 721 zone calculation.
    Suitable for PDF export, archive, and compliance audit.
    """

    project_name: str
    zone_name: str
    substance_name: str
    substance_lel: float
    release_rate_kg_s: float
    ventilation_rate_m3_s: float
    release_type: str
    zone_type: str
    radius_m: float
    volume_m3: float
    dilution_factor: float
    safety_factor: float
    basis_norm: str
    riskfw_version: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class IgnitionAssessmentReport:
    """
    Structured ignition source assessment matrix per EN 1127-1:2019.
    """

    project_name: str
    zone_type: str
    assessments: list[IgnitionAssessment] = field(default_factory=list)
    basis_norm: str = "EN 1127-1:2019"
    riskfw_version: str = ""

    @property
    def has_unmitigated_high_risk(self) -> bool:
        """True if any ignition source is HIGH risk without mitigation."""
        return any(
            a.risk_level == IgnitionRisk.HIGH and not a.mitigation
            for a in self.assessments
        )

    @property
    def high_risk_sources(self) -> list[IgnitionAssessment]:
        """All HIGH risk ignition sources without mitigation."""
        return [
            a for a in self.assessments
            if a.risk_level == IgnitionRisk.HIGH and not a.mitigation
        ]

    @property
    def sources_by_risk(self) -> dict[str, list[IgnitionAssessment]]:
        """Groups assessments by risk level."""
        result: dict[str, list[IgnitionAssessment]] = {"high": [], "low": [], "none": []}
        for a in self.assessments:
            result[str(a.risk_level)].append(a)
        return result
