# 画己职测 — 全局中间件

import logging
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from common.utils import generate_device_fingerprint

logger = logging.getLogger(__name__)

DEVICE_FINGERPRINT_COOKIE: str = "device_fingerprint"
SESSION_TOKEN_COOKIE: str = "session_token"
DEVICE_FINGERPRINT_HEADER: str = "X-Device-Fingerprint"
SESSION_TOKEN_HEADER: str = "X-Session-Token"


class DeviceFingerprintMiddleware:
    """设备指纹中间件：从请求头或 Cookie 获取 device_fingerprint，
    若不存在则生成并设置到 Cookie；同时将 device_fingerprint 和
    session_token 添加到 request 对象。"""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response: Callable[[HttpRequest], HttpResponse] = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 获取或生成 device_fingerprint
        device_fingerprint: str = (
            request.headers.get(DEVICE_FINGERPRINT_HEADER)
            or request.COOKIES.get(DEVICE_FINGERPRINT_COOKIE)
            or generate_device_fingerprint()
        )

        # 获取 session_token（优先请求头，其次 Cookie）
        session_token: str = request.headers.get(SESSION_TOKEN_HEADER) or request.COOKIES.get(SESSION_TOKEN_COOKIE, "")

        # 挂载到 request 对象
        request.device_fingerprint = device_fingerprint
        request.session_token = session_token

        response: HttpResponse = self.get_response(request)

        # 若 Cookie 中不存在 device_fingerprint，则设置
        if DEVICE_FINGERPRINT_COOKIE not in request.COOKIES:
            response.set_cookie(
                DEVICE_FINGERPRINT_COOKIE,
                device_fingerprint,
                max_age=365 * 24 * 3600,
                httponly=True,
                samesite="Lax",
            )

        return response


class ExceptionHandlerMiddleware:
    """全局异常处理中间件：捕获未处理异常，返回统一 JSON 错误格式。"""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response: Callable[[HttpRequest], HttpResponse] = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        # 上报到 Sentry（如果已初始化）
        try:
            import sentry_sdk

            sentry_sdk.capture_exception(exception)
        except ImportError:
            pass

        # 现有日志逻辑
        logger.exception(
            "未处理的异常 | path=%s | error=%s",
            request.path,
            str(exception),
        )

        from django.conf import settings

        detail: str = ""
        if not settings.DEBUG:
            detail = ""
        else:
            detail = str(exception)

        return JsonResponse(
            {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": detail,
            },
            status=500,
        )


class LoggingMiddleware:
    """请求日志中间件：记录请求方法和路径（INFO 级别）。"""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response: Callable[[HttpRequest], HttpResponse] = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        logger.info(
            "请求 | method=%s | path=%s",
            request.method,
            request.path,
        )
        return self.get_response(request)
