"""DSB Component inclusion tags (ADR-041 Phase 0+1)."""

from __future__ import annotations

import re

from django import template
from django.utils.html import format_html, mark_safe

register = template.Library()


@register.filter
def abs_val(value):
    """Return absolute value of a number."""
    try:
        v = int(value)
        return v if v >= 0 else -v
    except (TypeError, ValueError):
        return value


@register.filter(is_safe=True)
def render_description(value: str) -> str:
    """Parse **Key:** Value lines into structured HTML dl/dt/dd blocks.

    Lines matching ``**Label:** content`` are rendered as definition list rows.
    Remaining plain-text lines are rendered as a prose paragraph.
    """
    if not value:
        return ""

    pattern = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
    structured = []
    prose_lines = []

    for line in value.splitlines():
        m = pattern.match(line.strip())
        if m:
            if prose_lines:
                structured.append(("__prose__", " ".join(prose_lines)))
                prose_lines = []
            structured.append((m.group(1).strip(), m.group(2).strip()))
        elif line.strip():
            prose_lines.append(line.strip())

    if prose_lines:
        structured.append(("__prose__", " ".join(prose_lines)))

    if not structured:
        return format_html(
            '<p class="text-sm text-gray-700 whitespace-pre-line">{}</p>',
            value,
        )

    rows_html = []
    for key, val in structured:
        if key == "__prose__":
            rows_html.append(format_html(
                '<p class="text-sm text-gray-700 col-span-2 mt-1">{}</p>',
                val,
            ))
        else:
            # Split comma-separated values into badges
            parts = [p.strip() for p in val.split(",") if p.strip()]
            if len(parts) > 1:
                badges = mark_safe("".join(
                    format_html(
                        '<span class="inline-block bg-gray-100 text-gray-700 '
                        'text-xs px-2 py-0.5 rounded mr-1 mb-1">{}</span>',
                        p,
                    )
                    for p in parts
                ))
                val_html = format_html('<div class="mt-0.5">{}</div>', badges)
            else:
                val_html = format_html(
                    '<span class="text-sm font-medium text-gray-900">{}</span>',
                    val or "—",
                )
            rows_html.append(format_html(
                '<div class="flex flex-col">'
                '<dt class="text-xs font-medium text-gray-500 uppercase tracking-wide">{}</dt>'
                '<dd class="mt-0.5">{}</dd>'
                '</div>',
                key,
                val_html,
            ))

    inner = mark_safe("".join(rows_html))
    return format_html(
        '<dl class="grid grid-cols-1 sm:grid-cols-2 gap-4">{}</dl>',
        inner,
    )


@register.inclusion_tag(
    "dsb/components/_stat_card.html",
)
def stat_card(
    icon: str,
    label: str,
    value: int,
    color: str = "blue",
    alert_value: int | None = None,
    alert_label: str = "",
    url: str = "",
) -> dict:
    """Render a KPI stat card.

    Usage:
        {% load dsb_components %}
        {% stat_card "file-text" "VVT" 12 "blue" %}
        {% stat_card "shield" "TOM" 8 "green" 3 "geplant" %}
    """
    from dsb.components.stat_card import get_context

    return get_context(
        icon=icon,
        label=label,
        value=value,
        color=color,
        alert_value=alert_value,
        alert_label=alert_label,
        url=url,
    )


@register.inclusion_tag(
    "dsb/components/_status_badge.html",
)
def status_badge(
    value: str,
    display: str = "",
) -> dict:
    """Render a colored status badge.

    Usage:
        {% load dsb_components %}
        {% status_badge "implemented" %}
        {% status_badge "critical" "Kritisch" %}
    """
    from dsb.components.status_badge import get_context

    return get_context(value=value, display=display)


@register.inclusion_tag(
    "dsb/components/_empty_state.html",
)
def empty_state(
    icon: str = "inbox",
    title: str = "Keine Einträge",
    message: str = "",
    action_url: str = "",
    action_label: str = "",
) -> dict:
    """Render an empty state placeholder.

    Usage:
        {% load dsb_components %}
        {% empty_state "file-text" "Keine VVT" "Erstellen Sie..." %}
    """
    from dsb.components.empty_state import get_context

    return get_context(
        icon=icon,
        title=title,
        message=message,
        action_url=action_url,
        action_label=action_label,
    )


@register.inclusion_tag(
    "dsb/components/_alert_banner.html",
)
def alert_banner(
    severity: str = "warning",
    icon: str = "alert-triangle",
    title: str = "",
    message: str = "",
) -> dict:
    """Render a colored alert banner.

    Usage:
        {% load dsb_components %}
        {% alert_banner "error" "alert-triangle" "Achtung" "72h!" %}
    """
    from dsb.components.alert_banner import get_context

    return get_context(
        severity=severity,
        icon=icon,
        title=title,
        message=message,
    )
