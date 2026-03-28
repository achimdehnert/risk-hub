"""Custom template filters for projects app."""

import json

from django import template

register = template.Library()


@register.filter
def parse_json(value):
    """Parse a JSON string into a Python object."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


@register.filter
def get_item(dictionary, key):
    """Get an item from a dict by key."""
    if not dictionary or not isinstance(dictionary, dict):
        return ""
    return dictionary.get(key, "")
