"""Data Table Component (ADR-041 Phase 1).

Reusable sortable table for DSB list views.
Used 6× (VVT, TOM, AVV, Audit, Deletion, Breach lists).
"""

from __future__ import annotations

from typing import Any

TEMPLATE = "dsb/components/_data_table.html"


def get_context(
    *,
    columns: list[dict[str, str]],
    rows: list[Any],
    empty_icon: str = "inbox",
    empty_title: str = "Keine Einträge",
    empty_message: str = "",
    testid: str = "data-table",
) -> dict[str, Any]:
    """Single source of truth for data table context.

    Args:
        columns: List of dicts with keys 'key', 'label',
                 optional 'class' for th styling.
        rows: QuerySet or list of model instances.
        empty_icon: Lucide icon for empty state.
        empty_title: Title for empty state.
        empty_message: Message for empty state.
        testid: data-testid attribute value.
    """
    return {
        "columns": columns,
        "rows": rows,
        "has_rows": bool(rows),
        "empty_icon": empty_icon,
        "empty_title": empty_title,
        "empty_message": empty_message,
        "testid": testid,
        "template_name": TEMPLATE,
    }
