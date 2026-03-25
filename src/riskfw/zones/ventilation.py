"""Ventilation effectiveness analysis per TRGS 722:2012-08."""

import logging

from riskfw.constants import NORM_TRGS_722
from riskfw.zones.models import VentilationEffectiveness, VentilationResult

logger = logging.getLogger(__name__)


def analyze_ventilation_effectiveness(
    room_volume_m3: float,
    air_flow_m3_h: float,
    ventilation_type: str = "technisch",
    has_ex_zone: bool = True,
) -> VentilationResult:
    """
    Analyzes ventilation effectiveness per TRGS 722:2012-08.

    Args:
        room_volume_m3: Room volume in m3
        air_flow_m3_h: Air flow rate in m3/h
        ventilation_type: "technisch" | "natuerlich" | "keine"
        has_ex_zone: Whether an ex zone is present

    Returns:
        VentilationResult
    """
    air_changes = air_flow_m3_h / room_volume_m3 if room_volume_m3 > 0 else 0.0

    if ventilation_type == "technisch":
        if air_changes >= 12:
            effectiveness = VentilationEffectiveness.HIGH
            can_reduce_zone = True
            recommendation = "Lueftung ausreichend fuer Zonenreduzierung nach TRGS 722"
        elif air_changes >= 6:
            effectiveness = VentilationEffectiveness.MEDIUM
            can_reduce_zone = has_ex_zone
            recommendation = "Zonenverkleinerung moeglich bei vorhandener Ex-Zone"
        else:
            effectiveness = VentilationEffectiveness.LOW
            can_reduce_zone = False
            recommendation = "Lueftung auf mindestens 6 Luftwechsel/h erhoehen (TRGS 722)"
    elif ventilation_type == "natuerlich":
        effectiveness = VentilationEffectiveness.VARIABLE
        can_reduce_zone = False
        recommendation = "Natuerliche Lueftung: keine Anrechnung fuer Zonenreduzierung (TRGS 722)"
    else:
        effectiveness = VentilationEffectiveness.NONE
        can_reduce_zone = False
        recommendation = "Technische Lueftung erforderlich"

    logger.info(
        "[Ventilation] type=%s air_changes=%.1f/h effectiveness=%s",
        ventilation_type, air_changes, effectiveness,
    )

    return VentilationResult(
        room_volume_m3=room_volume_m3,
        air_flow_m3_h=air_flow_m3_h,
        air_changes_per_hour=round(air_changes, 1),
        ventilation_type=ventilation_type,
        effectiveness=effectiveness,
        can_reduce_zone=can_reduce_zone,
        recommendation=recommendation,
        basis_norm=NORM_TRGS_722,
    )
