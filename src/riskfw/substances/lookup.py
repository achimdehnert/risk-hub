"""Substance lookup with alias resolution and stdlib fuzzy matching."""

import difflib
import logging

from riskfw.exceptions import SubstanceNotFoundError
from riskfw.substances.database import SUBSTANCE_ALIASES, SUBSTANCE_DATABASE, SubstanceProperties

logger = logging.getLogger(__name__)


def get_substance_properties(name: str) -> SubstanceProperties:
    """
    Returns SubstanceProperties for the given substance name.
    Resolves aliases, then exact match, then difflib fuzzy fallback.

    Raises:
        SubstanceNotFoundError: If substance is not found
    """
    key = name.lower().strip()

    if key in SUBSTANCE_ALIASES:
        key = SUBSTANCE_ALIASES[key]
        logger.debug("[Substances] Alias resolved: %s -> %s", name, key)

    if key in SUBSTANCE_DATABASE:
        return SUBSTANCE_DATABASE[key]

    match = fuzzy_lookup(key)
    if match:
        logger.info("[Substances] Fuzzy match: %s -> %s", name, match)
        return SUBSTANCE_DATABASE[match]

    raise SubstanceNotFoundError(
        f"Substance '{name}' not found. Known: {list(SUBSTANCE_DATABASE.keys())}"
    )


def fuzzy_lookup(name: str, threshold: float = 0.6) -> str | None:
    """
    Finds closest substance key via difflib (stdlib only, O(n) for n~100).

    Returns:
        Matching key or None
    """
    candidates = list(SUBSTANCE_DATABASE.keys())
    matches = difflib.get_close_matches(name, candidates, n=1, cutoff=threshold)
    return matches[0] if matches else None


def list_substances() -> list[SubstanceProperties]:
    """Returns all substances in the database."""
    return list(SUBSTANCE_DATABASE.values())
