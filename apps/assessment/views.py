"""Views for the assessment app.

Handles the assessment (questionnaire) page, score submission, result
rendering and history lookup.
"""

from django.views import View
from django.shortcuts import render
from django.http import JsonResponse


class AssessmentView(View):
    """Assessment (questionnaire) page.

    Renders ``pages/assessment.html``.
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'pages/assessment.html')


class ScoreView(View):
    """Score submission endpoint.

    Accepts the user's answers and computes the MBTI result. The
    scoring engine is not implemented yet, so this returns a
    placeholder ``501 Not Implemented`` response with an error message.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse(
            {"error": "scoring engine not implemented"},
            status=501,
        )


class ResultView(View):
    """Assessment result page.

    Renders ``pages/result.html``. When a ``uuid`` is provided (via the
    URL path), the specific result for that assessment is looked up.
    Without a ``uuid``, a default/example result page is rendered so the
    page layout can be previewed.
    """

    def get(self, request, uuid=None, *args, **kwargs):
        context = {"uuid": uuid} if uuid else {}
        return render(request, 'pages/result.html', context)


class HistoryView(View):
    """Return the assessment history for a given ``uuid``.

    Placeholder implementation; returns ``{"history": []}``.
    """

    def get(self, request, uuid, *args, **kwargs):
        return JsonResponse({"history": []})
