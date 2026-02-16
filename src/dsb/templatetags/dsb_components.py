"""DSB Component inclusion tags (ADR-041 Phase 0)."""

from __future__ import annotations

from django import template

register = template.Library()


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
