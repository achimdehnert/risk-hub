"""Detail Card Component (ADR-041 Phase 1).

Renders a key-value detail card for single-entity views.
Used 6× (VVT detail, TOM detail, AVV detail, etc.).
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_detail_card.html"


def get_context(
    *,
    title: str,
    icon: str = "",
    fields: list[dict[str, Any]] | None = None,
    badge_value: str = "",
    badge_display: str = "",
    actions: list[dict[str, str]] | None = None,
    testid: str = "detail-card",
) -> dict[str, Any]:
    """Single source of truth for detail card context.

    Args:
        title: Card heading.
        icon: Lucide icon name.
        fields: List of dicts with 'label', 'value',
                optional 'type' (text|badge|date|link).
        badge_value: Status badge raw value.
        badge_display: Status badge display text.
        actions: List of dicts with 'url', 'label', 'icon'.
        testid: data-testid attribute value.
    """
    return {
        "title": title,
        "icon": icon,
        "fields": fields or [],
        "badge_value": badge_value,
        "badge_display": badge_display,
        "actions": actions or [],
        "testid": testid,
        "template_name": TEMPLATE,
    }
