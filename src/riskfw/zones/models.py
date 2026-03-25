"""Dataclasses and enums for zone calculation results."""

from dataclasses import dataclass, field
from enum import StrEnum


class ZoneType(StrEnum):
    """ATEX zone classification per TRGS 721."""

    ZONE_0 = "0"
    ZONE_1 = "1"
    ZONE_2 = "2"


class ReleaseType(StrEnum):
    """Type of substance release per TRGS 721."""

    JET = "jet"
    POOL = "pool"
    DIFFUSE = "diffuse"


class VentilationEffectiveness(StrEnum):
    """Ventilation effectiveness classification per TRGS 722."""

    HIGH = "hoch"
    MEDIUM = "mittel"
    LOW = "gering"
    VARIABLE = "variabel"
    NONE = "keine"


@dataclass
class ZoneExtentResult:
    """
    Result of a TRGS 721 zone extent calculation.
    Precision: float64. TRGS 721 specifies +/-0.1m accuracy -- float64 sufficient.
    """

    zone_type: ZoneType
    release_type: ReleaseType
    radius_m: float
    volume_m3: float
    dilution_factor: float
    safety_factor: float
    lel_percent: float
    basis_norm: str = "TRGS 721:2017-09"
    warnings: list[str] = field(default_factory=list)


@dataclass
class VentilationResult:
    """Result of a TRGS 722 ventilation effectiveness analysis."""

    room_volume_m3: float
    air_flow_m3_h: float
    air_changes_per_hour: float
    ventilation_type: str
    effectiveness: VentilationEffectiveness
    can_reduce_zone: bool
    recommendation: str
    basis_norm: str = "TRGS 722:2012-08"
