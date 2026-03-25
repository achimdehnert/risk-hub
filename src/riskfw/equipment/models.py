"""Dataclasses for ATEX equipment check results."""

from dataclasses import dataclass, field


@dataclass
class ATEXCheckResult:
    """Result of an ATEX equipment suitability check per ATEX 2014/34/EU."""

    is_suitable: bool
    equipment_marking: str
    target_zone: str
    detected_category: str | None
    detected_temp_class: str | None
    detected_exp_group: str | None
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    basis_norm: str = "ATEX 2014/34/EU"
