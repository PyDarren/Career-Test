"""Views for the careers app.

Provides the career-matching API.
"""

from django.views import View
from django.http import JsonResponse


class CareerMatchView(View):
    """Return recommended careers for an MBTI type.

    Placeholder implementation; returns an empty match list.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            "matches": [],
            "message": "Career matching engine not implemented yet.",
        })
