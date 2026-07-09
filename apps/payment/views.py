"""Views for the payment app.

Handles payment creation, third-party payment callbacks (WeChat Pay /
Alipay), order-status polling, report-recovery and the paid-report
rendering page.

Note: the WeChat Pay and Alipay notify endpoints are invoked by the
payment platforms rather than the browser, so they are exempt from CSRF
protection. They will instead be secured through signature verification
of the callback payload, which is to be implemented later.
"""

from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class CreatePaymentView(View):
    """Create a payment order.

    Called by the front-end (CSRF token supplied by the browser).
    Placeholder implementation; returns a stub order payload.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({
            "success": False,
            "message": "Payment creation not implemented yet.",
        })


@method_decorator(csrf_exempt, name='dispatch')
class WechatNotifyView(View):
    """WeChat Pay asynchronous notify callback.

    Exempt from CSRF: it is called by WeChat Pay and will be verified
    through WeChat Pay's signature instead of a CSRF token.
    Placeholder implementation; returns ``"success"`` so the platform
    stops retrying the notification.
    """

    def post(self, request, *args, **kwargs):
        return HttpResponse("success")


@method_decorator(csrf_exempt, name='dispatch')
class AlipayNotifyView(View):
    """Alipay asynchronous notify callback.

    Exempt from CSRF: it is called by Alipay and will be verified
    through Alipay's signature instead of a CSRF token.
    Placeholder implementation; returns ``"success"`` so the platform
    stops retrying the notification.
    """

    def post(self, request, *args, **kwargs):
        return HttpResponse("success")


class OrderStatusView(View):
    """Return the status of a payment order.

    Placeholder implementation; returns a stub status payload for the
    given ``order_no``.
    """

    def get(self, request, order_no, *args, **kwargs):
        return JsonResponse({
            "order_no": order_no,
            "status": "unknown",
            "message": "Order status lookup not implemented yet.",
        })


class ReportRecoverView(View):
    """Recover / re-issue a previously purchased report.

    Called by the front-end (CSRF token supplied by the browser).
    Placeholder implementation; returns a stub payload.
    """

    def post(self, request, *args, **kwargs):
        return JsonResponse({
            "success": False,
            "message": "Report recovery not implemented yet.",
        })


class ReportView(View):
    """Paid report page.

    Renders ``pages/report.html`` for the given ``order_no``.
    """

    def get(self, request, order_no, *args, **kwargs):
        return render(request, 'pages/report.html', {"order_no": order_no})
