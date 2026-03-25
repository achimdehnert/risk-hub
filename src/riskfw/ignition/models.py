"""Dataclasses and enums for ignition source assessment."""

from dataclasses import dataclass
from enum import StrEnum


class IgnitionRisk(StrEnum):
    """Ignition risk level per EN 1127-1:2019."""

    NONE = "none"
    LOW = "low"
    HIGH = "high"


@dataclass
class IgnitionAssessment:
    """Assessment result for a single ignition source per EN 1127-1:2019."""

    source_id: str
    source_name: str
    is_present: bool
    is_effective: bool
    risk_level: IgnitionRisk
    mitigation: str = ""
    norm_reference: str = "EN 1127-1:2019"
    norm_clause: str = ""
