# src/substances/exports/__init__.py
"""Export-Module für Substances."""

from .hazard_register_excel import generate_hazard_register_excel

__all__ = ["generate_hazard_register_excel"]
