"""Views for the stats app.

Provides the homepage, about, help, settings and report pages together
with a set of small JSON APIs used by the front-end (completed-count,
feedback, customer-service and analytics tracking).
"""

from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse


class HomeView(View):
    """Homepage of the site.

    Renders the landing page ``pages/home.html``.
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'pages/home.html')


class AboutView(View):
    """About page.

    Renders ``pages/about.html`` if it exists, otherwise falls back to
    ``pages/home.html``.
    """

    def get(self, request, *args, **kwargs):
        from django.template.loader import select_template
        template = select_template(['pages/about.html', 'pages/home.html'])
        return HttpResponse(template.render({}, request))


class HelpView(View):
    """Help / FAQ page.

    Renders ``pages/help.html``.
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'pages/help.html')


class SettingsView(View):
    """Settings page.

    Renders ``pages/settings.html``.
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'pages/settings.html')


class ReportView(View):
    """Deep report page.

    Renders ``pages/report.html``. In production this would be gated
    behind a payment check; for now it renders the template directly
    so the page layout can be previewed.
    """

    def get(self, request, *args, **kwargs):
        return render(request, 'pages/report.html')


class CompletedCountView(View):
    """Return the number of completed assessments.

    Placeholder implementation; returns ``{"count": 0}``.
    """

    def get(self, request, *args, **kwargs):
        return JsonResponse({"count": 0})


class FeedbackView(View):
    """Receive user feedback submitted from the front-end.

    Placeholder implementation; always returns ``{"success": True}``.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({"success": True})


class CustomerServiceView(View):
    """Customer-service contact endpoint.

    Placeholder implementation; always returns ``{"success": True}``.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({"success": True})


class TrackView(View):
    """Analytics tracking endpoint.

    Receives front-end tracking events. Placeholder implementation;
    always returns ``{"success": True}``.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({"success": True})
