# 画己职测 — personality 视图
#
# 本模块实现人格原型相关的 API 视图（DRF APIView）：
#   - ArchetypeDetailView: GET /api/archetypes/<int:archetype_id>/ — 获取原型配置

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from personality.models import PersonalityArchetype

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


class ArchetypeDetailView(APIView):
    """GET /api/archetypes/<int:archetype_id>/ — 获取原型配置。

    不需要认证。
    从 Redis 缓存读取，key: personality:archetype:{id}:v1
    TTL 1 小时。
    """

    def get(self, request: Request, archetype_id: int) -> Response:
        """获取原型配置详情。"""
        try:
            # 复用 result_service 的缓存逻辑
            from assessment.services.result_service import get_archetype_config

            config: dict[str, object] = get_archetype_config(archetype_id)

            logger.info("原型配置请求成功 | archetype_id=%d", archetype_id)
            return _success_response(config)

        except PersonalityArchetype.DoesNotExist:
            logger.warning("原型不存在 | archetype_id=%d", archetype_id)
            return _error_response(
                "ARCHETYPE_NOT_FOUND",
                "人格原型不存在",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.exception("原型配置请求失败 | archetype_id=%d | error=%s", archetype_id, str(exc))
            return _error_response(
                "ARCHETYPE_QUERY_ERROR",
                "获取原型配置失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
