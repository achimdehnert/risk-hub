"""Custom exceptions for riskfw."""


class RiskfwError(Exception):
    """Base exception for all riskfw errors."""


class SubstanceNotFoundError(RiskfwError):
    """Raised when a substance is not found in the database."""


class ZoneCalculationError(RiskfwError):
    """Raised when zone calculation fails due to invalid input."""


class ATEXCheckError(RiskfwError):
    """Raised when ATEX equipment check fails due to invalid input."""
