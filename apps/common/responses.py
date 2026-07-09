"""Standardised API response helpers for the caretest project."""

from __future__ import annotations

from typing import Any

from django.http import JsonResponse


class APIError(Exception):
    """An application-level API error.

    Raised inside views or services to signal an error that should be
    translated into a JSON error response by the caller.

    Attributes:
        code: A machine-readable error code (e.g. ``"invalid_params"``).
        message: A human-readable error message.
        http_status: The HTTP status code to return.
        extra: Optional extra data to include in the response payload.
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the API error.

        Args:
            code: A machine-readable error code.
            message: A human-readable error message.
            http_status: The HTTP status code (default 400).
            extra: Optional extra data to include in the response.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}


def api_error_response(api_error: APIError) -> JsonResponse:
    """Build a JSON response for an :class:`APIError`.

    Args:
        api_error: The :class:`APIError` describing the error.

    Returns:
        A :class:`~django.http.JsonResponse` with the error payload and the
        appropriate HTTP status code.
    """
    payload: dict[str, Any] = {
        "success": False,
        "code": api_error.code,
        "message": api_error.message,
    }
    if api_error.extra:
        payload["data"] = api_error.extra
    return JsonResponse(payload, status=api_error.http_status)


def api_success_response(data: Any, extra: dict[str, Any] | None = None) -> JsonResponse:
    """Build a success JSON response.

    Args:
        data: The primary data to return to the client.
        extra: Optional additional fields merged into the payload.

    Returns:
        A :class:`~django.http.JsonResponse` with a success payload.
    """
    payload: dict[str, Any] = {
        "success": True,
        "code": "ok",
        "data": data,
    }
    if extra:
        payload.update(extra)
    return JsonResponse(payload)
