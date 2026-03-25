"""
ATEX equipment suitability check per ATEX 2014/34/EU.

Checks whether a device's Ex marking suits the target zone
based on equipment category requirements (IEC 60079-0, ATEX Annex I).
"""

import logging

from riskfw.constants import NORM_ATEX
from riskfw.equipment.models import ATEXCheckResult
from riskfw.exceptions import ATEXCheckError

logger = logging.getLogger(__name__)

_ZONE_REQUIREMENTS: dict[str, dict] = {
    "0":  {"min_category": "1G", "allowed": ["1G"]},
    "1":  {"min_category": "2G", "allowed": ["1G", "2G"]},
    "2":  {"min_category": "3G", "allowed": ["1G", "2G", "3G"]},
    "20": {"min_category": "1D", "allowed": ["1D"]},
    "21": {"min_category": "2D", "allowed": ["1D", "2D"]},
    "22": {"min_category": "3D", "allowed": ["1D", "2D", "3D"]},
}


def check_equipment_suitability(ex_marking: str, zone: str) -> ATEXCheckResult:
    """
    Checks ATEX equipment suitability for a given zone.

    Args:
        ex_marking: Ex marking string, e.g. "II 2G Ex d IIB T4"
        zone: Target zone, e.g. "1", "Zone 1", "21"

    Returns:
        ATEXCheckResult

    Raises:
        ATEXCheckError: Unknown zone identifier
    """
    zone_normalized = zone.strip().lower().replace("zone", "").strip()

    if zone_normalized not in _ZONE_REQUIREMENTS:
        raise ATEXCheckError(
            f"Unknown zone: {zone!r}. Valid: {list(_ZONE_REQUIREMENTS.keys())}"
        )

    requirements = _ZONE_REQUIREMENTS[zone_normalized]
    marking_upper = ex_marking.upper()

    detected_category: str | None = None
    for cat in ["1G", "2G", "3G", "1D", "2D", "3D"]:
        if cat in marking_upper:
            detected_category = cat
            break

    detected_temp_class: str | None = None
    for tc in ["T6", "T5", "T4", "T3", "T2", "T1"]:
        if tc in marking_upper:
            detected_temp_class = tc
            break

    detected_exp_group: str | None = None
    for eg in ["IIC", "IIB", "IIA"]:
        if eg in marking_upper:
            detected_exp_group = eg
            break

    issues: list[str] = []
    recommendations: list[str] = []

    if not detected_category:
        issues.append("Keine Geraetekategorie in Kennzeichnung erkannt")
        recommendations.append(
            f"Erforderliche Kategorie fuer Zone {zone_normalized}: {requirements['allowed']}"
        )
    elif detected_category not in requirements["allowed"]:
        issues.append(
            f"Kategorie {detected_category} nicht fuer Zone {zone_normalized} geeignet"
        )
        recommendations.append(
            f"Mindestens Kategorie {requirements['min_category']} erforderlich"
        )

    if not detected_temp_class:
        issues.append("Keine Temperaturklasse in Kennzeichnung erkannt")

    if not detected_exp_group:
        issues.append("Keine Explosionsgruppe in Kennzeichnung erkannt")

    is_suitable = (
        detected_category is not None
        and detected_category in requirements["allowed"]
        and len(issues) == 0
    )

    logger.info(
        "[ATEXCheck] marking=%s zone=%s suitable=%s category=%s",
        ex_marking, zone_normalized, is_suitable, detected_category,
    )

    return ATEXCheckResult(
        is_suitable=is_suitable,
        equipment_marking=ex_marking,
        target_zone=zone_normalized,
        detected_category=detected_category,
        detected_temp_class=detected_temp_class,
        detected_exp_group=detected_exp_group,
        issues=issues,
        recommendations=recommendations,
        basis_norm=NORM_ATEX,
    )
