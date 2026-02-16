"""Empty State Component (ADR-041).

Consistent "no data yet" placeholder for DSB list views.
Used 6× (one per DSGVO list view).
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_empty_state.html"


def get_context(
    *,
    icon: str = "inbox",
    title: str = "Keine Einträge",
    message: str = "",
    action_url: str = "",
    action_label: str = "",
) -> dict[str, Any]:
    """Single source of truth for empty state data."""
    return {
        "icon": icon,
        "title": title,
        "message": message,
        "action_url": action_url,
        "action_label": action_label,
        "template_name": TEMPLATE,
    }
