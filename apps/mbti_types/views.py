"""Views for the mbti_types app.

Provides the MBTI type detail API.
"""

from django.views import View
from django.http import JsonResponse


class MBTITypeView(View):
    """Return the detail of a single MBTI type.

    Looks up the type by its ``code`` (e.g. ``INTJ``). Placeholder
    implementation; returns a stub JSON payload.
    """

    def get(self, request, code, *args, **kwargs):
        return JsonResponse({
            "code": code,
            "title": "",
            "description": "MBTI type detail not implemented yet.",
        })
