"""Context processors for the caretest project."""

from __future__ import annotations

from typing import Any

from django.conf import settings


def site_settings(request) -> dict[str, Any]:
    """Expose the site configuration to all templates.

    The site configuration is read from ``settings.SITE_CONFIG`` and made
    available in the template context under the ``site_config`` key.
    A convenience ``site_name`` key is also exposed for direct use in
    templates (e.g. ``{{ site_name }}``).

    Args:
        request: The incoming HTTP request (unused, but required by the
            Django context processor contract).

    Returns:
        A dictionary with ``site_config`` and ``site_name`` keys.
    """
    config = getattr(settings, "SITE_CONFIG", {})
    return {
        "site_config": config,
        "site_name": config.get("site_name", "职探"),
    }
