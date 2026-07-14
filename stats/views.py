# 画己职测 — stats 视图
#
# 本模块实现埋点相关的 API 视图（DRF APIView）：
#   - TrackingEventView: POST /api/tracking-events/ — 埋点上报

import logging

from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import mask_token

logger = logging.getLogger(__name__)


def _success_response(data: dict[str, object] | list[object], message: str = "success") -> Response:
    """构建统一成功响应。"""
    return Response(
        {"code": 0, "data": data, "message": message},
        status=status.HTTP_200_OK,
    )


def _error_response(
    error_code: str,
    message: str,
    detail: str = "",
    http_status: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """构建统一错误响应。"""
    return Response(
        {"code": error_code, "message": message, "detail": detail},
        status=http_status,
    )


class TrackingEventSerializer(serializers.Serializer):
    """埋点事件序列化器。"""

    event_type = serializers.CharField(max_length=30)
    event_data = serializers.DictField(required=False, default=dict)
    page_name = serializers.CharField(max_length=50, required=False, allow_blank=True)


class TrackingEventView(APIView):
    """POST /api/tracking-events/ — 埋点上报。

    不需要认证。
    接收 event_type, event_data, page_name。
    存储 TrackingEvent 记录。
    """

    def post(self, request: Request) -> Response:
        """上报埋点事件。"""
        serializer = TrackingEventSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("埋点上报参数校验失败 | errors=%s", serializer.errors)
            return _error_response(
                "VALIDATION_ERROR",
                "参数校验失败",
                detail=str(serializer.errors),
            )

        # 从中间件获取设备指纹和会话令牌
        device_fingerprint: str = getattr(request, "device_fingerprint", "")
        session_token: str = getattr(request, "session_token", "")

        try:
            from stats.models import TrackingEvent

            validated: dict[str, object] = serializer.validated_data

            event: TrackingEvent = TrackingEvent.objects.create(
                session_token=session_token,
                device_fingerprint=device_fingerprint,
                event_type=str(validated["event_type"]),
                event_data=validated.get("event_data", {}),
                page_name=str(validated.get("page_name", "")) or None,
            )

            logger.info(
                "埋点上报成功 | event_id=%d | event_type=%s | session=%s",
                event.id,
                event.event_type,
                mask_token(session_token),
            )

            return _success_response({"event_id": event.id})

        except Exception as exc:
            logger.exception("埋点上报失败 | error=%s", str(exc))
            return _error_response(
                "TRACKING_ERROR",
                "埋点上报失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
