"""Custom template tags and filters for the caretest project."""

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def split(value, separator: str = ","):
    """Split a string into a list using the given separator.

    If the value is already a list or tuple, it is returned as-is so the
    filter can be safely chained with ``default`` even when a real list
    is passed from the view context.

    Usage in templates::

        {% for item in "a,b,c"|split:"," %}
            {{ item }}
        {% endfor %}

    Args:
        value: The string to split (or an existing list/tuple).
        separator: The delimiter to split on (default: comma).

    Returns:
        A list of substrings. Returns an empty list if value is falsy.
    """
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return value
    return str(value).split(separator)
