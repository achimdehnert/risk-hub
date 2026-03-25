"""Substance database and lookup utilities."""

from riskfw.substances.database import SUBSTANCE_ALIASES, SUBSTANCE_DATABASE, SubstanceProperties
from riskfw.substances.lookup import fuzzy_lookup, get_substance_properties, list_substances

__all__ = [
    "SUBSTANCE_DATABASE",
    "SUBSTANCE_ALIASES",
    "SubstanceProperties",
    "get_substance_properties",
    "fuzzy_lookup",
    "list_substances",
]
