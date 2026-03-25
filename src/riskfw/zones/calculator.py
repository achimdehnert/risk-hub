"""
Zone extent calculation per TRGS 721:2017-09, Annex 1.

Dilution factor from ventilation vs. release rate.
Zone type from dilution thresholds (TRGS 721 Table 1).
Zone radius from spherical approximation.
"""

import logging
import math

from riskfw.constants import NORM_TRGS_721, SAFETY_FACTORS
from riskfw.exceptions import ZoneCalculationError
from riskfw.substances.lookup import get_substance_properties
from riskfw.zones.models import ReleaseType, ZoneExtentResult, ZoneType

logger = logging.getLogger(__name__)


def calculate_zone_extent(
    release_rate_kg_s: float,
    ventilation_rate_m3_s: float,
    release_type: str = "jet",
    substance_name: str | None = None,
    lel_percent: float = 1.5,
    room_volume_m3: float | None = None,
) -> ZoneExtentResult:
    """
    Calculates zone extent per TRGS 721:2017-09 Annex 1.

    Args:
        release_rate_kg_s: Release rate in kg/s
        ventilation_rate_m3_s: Ventilation air flow in m3/s
        release_type: "jet" | "pool" | "diffuse"
        substance_name: Optional name for automatic LEL lookup
        lel_percent: Lower explosion limit in Vol-% (overridden by substance_name)
        room_volume_m3: Optional room volume for context warnings

    Returns:
        ZoneExtentResult

    Raises:
        ZoneCalculationError: Invalid input
        SubstanceNotFoundError: Substance not in database
    """
    if release_rate_kg_s < 0:
        raise ZoneCalculationError(f"release_rate_kg_s must be >= 0, got {release_rate_kg_s}")
    if ventilation_rate_m3_s < 0:
        raise ZoneCalculationError(
            f"ventilation_rate_m3_s must be >= 0, got {ventilation_rate_m3_s}"
        )

    try:
        release_type_enum = ReleaseType(release_type)
    except ValueError:
        raise ZoneCalculationError(
            f"Unknown release_type: {release_type!r}. Allowed: {[r.value for r in ReleaseType]}"
        )

    safety_factor = SAFETY_FACTORS[release_type]
    warnings: list[str] = []

    if substance_name:
        substance = get_substance_properties(substance_name)
        lel_percent = substance.lower_explosion_limit
        logger.debug("[ZoneCalc] LEL from %s: %.1f Vol-%%", substance_name, lel_percent)

    if lel_percent <= 0:
        raise ZoneCalculationError(f"lel_percent must be > 0, got {lel_percent}")

    lel_fraction = lel_percent / 100.0

    if ventilation_rate_m3_s > 0:
        dilution_factor = ventilation_rate_m3_s / (release_rate_kg_s + 1e-9)
        zone_volume_m3 = (release_rate_kg_s / lel_fraction) * safety_factor
        zone_radius_m = (zone_volume_m3 * 3.0 / (4.0 * math.pi)) ** (1.0 / 3.0)

        if dilution_factor >= 1000:
            zone_type = ZoneType.ZONE_2
        elif dilution_factor >= 100:
            zone_type = ZoneType.ZONE_1
        else:
            zone_type = ZoneType.ZONE_0
    else:
        dilution_factor = 0.0
        zone_type = ZoneType.ZONE_0
        zone_volume_m3 = room_volume_m3 if room_volume_m3 else 0.0
        zone_radius_m = (
            (zone_volume_m3 * 3.0 / (4.0 * math.pi)) ** (1.0 / 3.0)
            if zone_volume_m3 > 0 else 0.0
        )
        warnings.append("No ventilation -- entire room classified as Zone 0 per TRGS 721")

    if room_volume_m3 and zone_volume_m3 > room_volume_m3:
        warnings.append(
            f"Calculated zone volume ({zone_volume_m3:.1f} m3) exceeds room volume"
            f" ({room_volume_m3:.1f} m3)"
        )

    logger.info(
        "[ZoneCalc] substance=%s type=%s zone=%s radius=%.2fm",
        substance_name, release_type, zone_type, zone_radius_m,
    )

    return ZoneExtentResult(
        zone_type=zone_type,
        release_type=release_type_enum,
        radius_m=round(zone_radius_m, 3),
        volume_m3=round(zone_volume_m3, 3),
        dilution_factor=round(dilution_factor, 2),
        safety_factor=safety_factor,
        lel_percent=lel_percent,
        basis_norm=NORM_TRGS_721,
        warnings=warnings,
    )
