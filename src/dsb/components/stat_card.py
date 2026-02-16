"""Stat Card Component (ADR-041).

Reusable KPI card with icon, value, label and optional alert count.
Used 7× on DSB Dashboard (one per DSGVO section).
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_stat_card.html"

COLOR_MAP: dict[str, dict[str, str]] = {
    "blue": {
        "bg": "bg-blue-50",
        "text": "text-blue-600",
        "icon_bg": "bg-blue-100",
    },
    "green": {
        "bg": "bg-green-50",
        "text": "text-green-600",
        "icon_bg": "bg-green-100",
    },
    "red": {
        "bg": "bg-red-50",
        "text": "text-red-600",
        "icon_bg": "bg-red-100",
    },
    "amber": {
        "bg": "bg-amber-50",
        "text": "text-amber-600",
        "icon_bg": "bg-amber-100",
    },
    "purple": {
        "bg": "bg-purple-50",
        "text": "text-purple-600",
        "icon_bg": "bg-purple-100",
    },
    "orange": {
        "bg": "bg-orange-50",
        "text": "text-orange-600",
        "icon_bg": "bg-orange-100",
    },
    "gray": {
        "bg": "bg-gray-50",
        "text": "text-gray-600",
        "icon_bg": "bg-gray-100",
    },
}


def get_context(
    *,
    icon: str,
    label: str,
    value: int,
    color: str = "blue",
    alert_value: int | None = None,
    alert_label: str = "",
    url: str = "",
) -> dict[str, Any]:
    """Single source of truth for stat card data."""
    colors = COLOR_MAP.get(color, COLOR_MAP["blue"])
    return {
        "icon": icon,
        "label": label,
        "value": value,
        "color": color,
        "colors": colors,
        "alert_value": alert_value,
        "alert_label": alert_label,
        "url": url,
        "template_name": TEMPLATE,
    }
