"""Module catalogue — defines available modules, their metadata, and pricing.

The catalogue is a plain Python dict (no DB model) configured via
``settings.MODULE_SHOP_CATALOGUE``. Apps register their modules there.

Each entry:
    code        str     Unique module code, e.g. "risk", "dsb", "ex"
    name        str     Display name
    description str     Short description (1-2 sentences)
    icon        str     Lucide icon name
    price_month float   Monthly price in EUR (0 = free)
    price_year  float   Yearly price in EUR (0 = free)
    stripe_price_id_month  str | None   Stripe Price ID (monthly)
    stripe_price_id_year   str | None   Stripe Price ID (yearly)
    category    str     Grouping: "safety", "legal", "operations", "core"
    dependencies list[str]  Module codes that must also be active

Example settings::

    MODULE_SHOP_CATALOGUE = {
        "risk": {
            "name": "Risikobewertung",
            "description": "Gefährdungsbeurteilungen und Maßnahmenverwaltung.",
            "icon": "shield-alert",
            "price_month": 29.0,
            "price_year": 290.0,
            "stripe_price_id_month": "price_xxx",
            "stripe_price_id_year": "price_yyy",
            "category": "safety",
            "dependencies": [],
        },
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class ModuleDefinition:
    """Immutable definition of a bookable module."""

    code: str
    name: str
    description: str = ""
    icon: str = "box"
    price_month: float = 0.0
    price_year: float = 0.0
    stripe_price_id_month: str | None = None
    stripe_price_id_year: str | None = None
    category: str = "core"
    dependencies: list[str] = field(default_factory=list)

    @property
    def is_free(self) -> bool:
        return self.price_month == 0.0 and self.price_year == 0.0

    @property
    def yearly_discount_pct(self) -> int:
        """Percentage discount when paying yearly vs monthly * 12."""
        if self.price_month == 0 or self.price_year == 0:
            return 0
        monthly_annual = self.price_month * 12
        if monthly_annual == 0:
            return 0
        return round((1 - self.price_year / monthly_annual) * 100)


def get_catalogue() -> dict[str, ModuleDefinition]:
    """Return all registered modules from settings.MODULE_SHOP_CATALOGUE."""
    raw: dict[str, dict[str, Any]] = getattr(settings, "MODULE_SHOP_CATALOGUE", {})
    result: dict[str, ModuleDefinition] = {}
    for code, data in raw.items():
        result[code] = ModuleDefinition(code=code, **data)
    return result


def get_module(code: str) -> ModuleDefinition | None:
    """Look up a single module by code. Returns None if not registered."""
    return get_catalogue().get(code)


def get_modules_by_category() -> dict[str, list[ModuleDefinition]]:
    """Group modules by category. Preserves insertion order within groups."""
    by_cat: dict[str, list[ModuleDefinition]] = {}
    for mod in get_catalogue().values():
        by_cat.setdefault(mod.category, []).append(mod)
    return by_cat
