"""Status Badge Component (ADR-041).

Renders a colored badge for MeasureStatus or SeverityLevel.
Used ~14× across DSB list and detail views.
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_status_badge.html"

BADGE_MAP: dict[str, dict[str, str]] = {
    "planned": {
        "bg": "bg-yellow-100",
        "text": "text-yellow-800",
        "dot": "bg-yellow-400",
    },
    "implemented": {
        "bg": "bg-green-100",
        "text": "text-green-800",
        "dot": "bg-green-400",
    },
    "verified": {
        "bg": "bg-blue-100",
        "text": "text-blue-800",
        "dot": "bg-blue-400",
    },
    "obsolete": {
        "bg": "bg-gray-100",
        "text": "text-gray-800",
        "dot": "bg-gray-400",
    },
    "low": {
        "bg": "bg-green-100",
        "text": "text-green-800",
        "dot": "bg-green-400",
    },
    "medium": {
        "bg": "bg-yellow-100",
        "text": "text-yellow-800",
        "dot": "bg-yellow-400",
    },
    "high": {
        "bg": "bg-orange-100",
        "text": "text-orange-800",
        "dot": "bg-orange-400",
    },
    "critical": {
        "bg": "bg-red-100",
        "text": "text-red-800",
        "dot": "bg-red-400",
    },
    "open": {
        "bg": "bg-red-100",
        "text": "text-red-800",
        "dot": "bg-red-400",
    },
    "in_progress": {
        "bg": "bg-blue-100",
        "text": "text-blue-800",
        "dot": "bg-blue-400",
    },
    "resolved": {
        "bg": "bg-green-100",
        "text": "text-green-800",
        "dot": "bg-green-400",
    },
    "accepted": {
        "bg": "bg-gray-100",
        "text": "text-gray-600",
        "dot": "bg-gray-400",
    },
    "active": {
        "bg": "bg-green-100",
        "text": "text-green-800",
        "dot": "bg-green-400",
    },
    "draft": {
        "bg": "bg-gray-100",
        "text": "text-gray-800",
        "dot": "bg-gray-400",
    },
    "expired": {
        "bg": "bg-red-100",
        "text": "text-red-800",
        "dot": "bg-red-400",
    },
    "terminated": {
        "bg": "bg-gray-100",
        "text": "text-gray-600",
        "dot": "bg-gray-400",
    },
    "completed": {
        "bg": "bg-green-100",
        "text": "text-green-800",
        "dot": "bg-green-400",
    },
    "cancelled": {
        "bg": "bg-gray-100",
        "text": "text-gray-600",
        "dot": "bg-gray-400",
    },
}

DEFAULT_BADGE: dict[str, str] = {
    "bg": "bg-gray-100",
    "text": "text-gray-800",
    "dot": "bg-gray-400",
}


def get_context(
    *,
    value: str,
    display: str = "",
) -> dict[str, Any]:
    """Single source of truth for status badge data."""
    badge = BADGE_MAP.get(value, DEFAULT_BADGE)
    return {
        "value": value,
        "display": display or value.replace("_", " ").title(),
        "badge": badge,
        "template_name": TEMPLATE,
    }
