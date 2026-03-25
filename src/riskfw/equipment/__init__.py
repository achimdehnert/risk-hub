"""ATEX equipment suitability checks per ATEX 2014/34/EU."""

from riskfw.equipment.checker import check_equipment_suitability
from riskfw.equipment.models import ATEXCheckResult

__all__ = ["ATEXCheckResult", "check_equipment_suitability"]
