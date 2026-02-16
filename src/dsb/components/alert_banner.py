"""Alert Banner Component (ADR-041 Phase 1).

Renders a colored alert banner with icon, title and item list.
Used for overdue items, critical findings, pending actions.
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_alert_banner.html"

SEVERITY_MAP: dict[str, dict[str, str]] = {
    "error": {
        "bg": "bg-red-50",
        "border": "border-red-200",
        "icon_color": "text-red-600",
        "title_color": "text-red-800",
        "text_color": "text-red-700",
    },
    "warning": {
        "bg": "bg-amber-50",
        "border": "border-amber-200",
        "icon_color": "text-amber-600",
        "title_color": "text-amber-800",
        "text_color": "text-amber-700",
    },
    "info": {
        "bg": "bg-blue-50",
        "border": "border-blue-200",
        "icon_color": "text-blue-600",
        "title_color": "text-blue-800",
        "text_color": "text-blue-700",
    },
    "success": {
        "bg": "bg-green-50",
        "border": "border-green-200",
        "icon_color": "text-green-600",
        "title_color": "text-green-800",
        "text_color": "text-green-700",
    },
}


def get_context(
    *,
    severity: str = "warning",
    icon: str = "alert-triangle",
    title: str = "",
    items: list[str] | None = None,
    message: str = "",
    dismissible: bool = False,
    testid: str = "alert-banner",
) -> dict[str, Any]:
    """Single source of truth for alert banner context."""
    colors = SEVERITY_MAP.get(
        severity, SEVERITY_MAP["warning"],
    )
    return {
        "severity": severity,
        "icon": icon,
        "title": title,
        "items": items or [],
        "message": message,
        "dismissible": dismissible,
        "colors": colors,
        "testid": testid,
        "template_name": TEMPLATE,
    }
