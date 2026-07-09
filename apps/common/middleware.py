"""Custom middleware for the caretest project."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger(__name__)

# Fallback in-memory store used when Redis is unavailable (e.g. local dev).
_local_rate_limit_store: dict[str, list[float]] = {}

# Rate limit configuration.
RATE_LIMIT_PATH_PREFIX = "/api/"
RATE_LIMIT_MAX_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60


class RateLimitMiddleware:
    """Limit the number of API requests a single IP can make per minute.

    Requests to paths starting with ``/api/`` are rate-limited to
    ``RATE_LIMIT_MAX_REQUESTS`` requests within a sliding window of
    ``RATE_LIMIT_WINDOW_SECONDS`` seconds. When the limit is exceeded a
    ``429 Too Many Requests`` JSON response is returned.

    The middleware prefers a Redis backend for counting requests but falls
    back to a simple in-memory dictionary when Redis is not configured, which
    is convenient for local development.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """Store the next handler in the chain.

        Args:
            get_response: The next middleware/view callable.
        """
        self.get_response = get_response
        self._redis_client = self._get_redis_client()

    @staticmethod
    def _get_redis_client() -> Any:
        """Return a Redis client if available, otherwise ``None``.

        The Redis client is only used when the default cache backend is a
        Redis backend so that development (LocMemCache) uses the local store.

        Returns:
            A configured Redis client or ``None`` when Redis is unavailable.
        """
        try:
            from django.conf import settings
            from django_redis import get_redis_connection  # type: ignore[import-untyped]

            backend = settings.CACHES.get("default", {}).get("BACKEND", "")
            if "redis" in backend.lower():
                return get_redis_connection("default")
        except Exception:
            # Redis is optional; fall back to the local store on any error.
            return None
        return None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process an incoming request and enforce the rate limit.

        Non-API requests (paths not starting with ``/api/``) are passed
        through without checking the rate limit.

        Args:
            request: The incoming HTTP request.

        Returns:
            The HTTP response from the next handler, or a ``429`` response
            when the rate limit is exceeded.
        """
        if not request.path.startswith(RATE_LIMIT_PATH_PREFIX):
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        allowed, remaining, reset_at = self._check_rate_limit(client_ip)

        if not allowed:
            return JsonResponse(
                {
                    "success": False,
                    "code": "rate_limit_exceeded",
                    "message": "请求过于频繁，请稍后再试。",
                    "detail": (
                        f"每 {RATE_LIMIT_WINDOW_SECONDS} 秒最多 "
                        f"{RATE_LIMIT_MAX_REQUESTS} 次请求。"
                    ),
                    "retry_after": max(int(reset_at - time.time()), 1),
                },
                status=429,
            )

        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(RATE_LIMIT_MAX_REQUESTS)
        response["X-RateLimit-Remaining"] = str(remaining)
        response["X-RateLimit-Reset"] = str(int(reset_at))
        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract the client IP address from the request.

        Honours ``X-Forwarded-For`` when present so the middleware works
        correctly behind a reverse proxy.

        Args:
            request: The incoming HTTP request.

        Returns:
            The client IP address string.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    def _check_rate_limit(self, client_ip: str) -> tuple[bool, int, float]:
        """Determine whether the client IP is within the rate limit.

        Uses a sliding window algorithm. When Redis is available the count
        is stored there; otherwise the in-memory fallback store is used.

        Args:
            client_ip: The IP address of the client.

        Returns:
            A tuple of ``(allowed, remaining, reset_at)`` where ``allowed``
            is ``True`` when the request is permitted, ``remaining`` is the
            number of requests left in the current window and ``reset_at``
            is the unix timestamp when the window resets.
        """
        if self._redis_client is not None:
            return self._check_rate_limit_redis(client_ip)
        return self._check_rate_limit_local(client_ip)

    def _check_rate_limit_redis(self, client_ip: str) -> tuple[bool, int, float]:
        """Check the rate limit using Redis as the backing store.

        A sorted set keyed by the client IP stores request timestamps. The
        window is implemented by removing timestamps older than
        ``RATE_LIMIT_WINDOW_SECONDS`` before counting.

        Args:
            client_ip: The IP address of the client.

        Returns:
            A tuple of ``(allowed, remaining, reset_at)``.
        """
        key = f"rate_limit:api:{client_ip}"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        pipe = self._redis_client.pipeline()
        # Drop timestamps that fell out of the sliding window.
        pipe.zremrangebyscore(key, 0, window_start)
        # Record the current request.
        pipe.zadd(key, {str(now): now})
        # Count requests still inside the window.
        pipe.zcard(key)
        # Expire the key so stale entries are cleaned up automatically.
        pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
        results = pipe.execute()
        count = results[2]

        remaining = max(RATE_LIMIT_MAX_REQUESTS - count, 0)
        allowed = count <= RATE_LIMIT_MAX_REQUESTS
        reset_at = now + RATE_LIMIT_WINDOW_SECONDS
        return allowed, remaining, reset_at

    def _check_rate_limit_local(self, client_ip: str) -> tuple[bool, int, float]:
        """Check the rate limit using an in-memory store (dev fallback).

        Args:
            client_ip: The IP address of the client.

        Returns:
            A tuple of ``(allowed, remaining, reset_at)``.
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        timestamps = _local_rate_limit_store.get(client_ip, [])
        # Keep only timestamps inside the current sliding window.
        timestamps = [ts for ts in timestamps if ts > window_start]
        timestamps.append(now)
        _local_rate_limit_store[client_ip] = timestamps

        count = len(timestamps)
        remaining = max(RATE_LIMIT_MAX_REQUESTS - count, 0)
        allowed = count <= RATE_LIMIT_MAX_REQUESTS
        reset_at = now + RATE_LIMIT_WINDOW_SECONDS
        return allowed, remaining, reset_at


class ExceptionMiddleware:
    """Global exception handling middleware.

    Catches :class:`APIError` raised inside views and returns a JSON
    error response with the appropriate status code. Any unhandled
    exception is caught, logged, and returned as a generic ``code=5001``
    error so the front-end receives a consistent JSON payload instead
    of a 500 HTML traceback.

    Only JSON API paths (``/api/``) receive JSON error responses; other
    paths fall through to Django's default error handling.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            return self.get_response(request)
        except Exception as exc:
            return self.process_exception(request, exc)

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> HttpResponse | None:
        """Convert exceptions into JSON error responses for API paths.

        Args:
            request: The incoming HTTP request.
            exception: The raised exception.

        Returns:
            A :class:`~django.http.JsonResponse` for API paths, or
            ``None`` to let Django's default handler take over.
        """
        from apps.common.responses import APIError, api_error_response

        # Only intercept API paths
        if not request.path.startswith('/api/'):
            return None

        # APIError → structured error response
        if isinstance(exception, APIError):
            logger.warning(
                'APIError on %s %s: code=%s message=%s',
                request.method, request.path,
                exception.code, exception.message,
            )
            return api_error_response(exception)

        # Unhandled exception → generic 5001 error
        logger.error(
            'Unhandled exception on %s %s: %s',
            request.method, request.path, exception,
            exc_info=True,
        )
        return JsonResponse(
            {
                'success': False,
                'code': 'internal_error',
                'message': '服务器内部错误，请稍后重试',
            },
            status=500,
        )
