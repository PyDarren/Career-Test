# 画己职测 — careers 视图
#
# 本模块实现职业相关的 API 视图（DRF APIView）：
#   - CareerListView: GET /api/careers/?archetype=<id>&riasec=<code> — 职业推荐

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from careers.models import Career
from careers.serializers import CareerSerializer

logger = logging.getLogger(__name__)

# 职业推荐返回上限
CAREER_RECOMMEND_LIMIT: int = 10

# 职业推荐最少返回数量（不足时触发 fallback 逻辑）
CAREER_MIN_RECOMMEND: int = 5


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


class CareerListView(APIView):
    """GET /api/careers/?archetype=<id>&riasec=<code> — 职业推荐。

    不需要认证。
    根据 archetype_id 和 riasec_code 筛选匹配职业。
    返回 Top 10 匹配职业。
    """

    def get(self, request: Request) -> Response:
        """获取职业推荐列表。"""
        archetype_id: str = request.query_params.get("archetype", "")
        riasec_code: str = request.query_params.get("riasec", "")

        try:
            # SQLite 不支持 JSONField __contains 查询，统一用 Python 过滤
            # 使用 .only() 限制查询字段，避免拉取不必要的大字段
            all_careers: list[Career] = list(
                Career.objects.filter(is_active=True).only(
                    "id",
                    "career_name",
                    "career_category",
                    "description",
                    "matching_archetypes",
                    "matching_riasec_codes",
                    "salary_range",
                    "growth_prospect",
                )
            )

            # 转换 archetype_id 为整数
            archetype_id_int: int | None = None
            if archetype_id:
                try:
                    archetype_id_int = int(archetype_id)
                except ValueError:
                    return _error_response(
                        "INVALID_ARCHETYPE_ID",
                        "画像 ID 格式不正确",
                    )

            # 解析 RIASEC 码为列表
            riasec_codes: list[str] = []
            if riasec_code:
                riasec_codes = [c for c in riasec_code.upper() if c]

            # 第一轮：archetype + RIASEC 双重筛选
            filtered = all_careers
            if archetype_id_int is not None:
                filtered = [c for c in filtered if archetype_id_int in (c.matching_archetypes or [])]
            if riasec_codes:
                filtered = [
                    c for c in filtered if any(rc in (c.matching_riasec_codes or []) for rc in riasec_codes)
                ]

            # Fallback 1：若不足 5 个，放宽为仅 RIASEC 筛选（去掉 archetype 限制）
            if len(filtered) < CAREER_MIN_RECOMMEND and riasec_codes:
                filtered = [
                    c for c in all_careers if any(rc in (c.matching_riasec_codes or []) for rc in riasec_codes)
                ]

            # Fallback 2：若仍不足 5 个，返回全部活跃职业
            if len(filtered) < CAREER_MIN_RECOMMEND:
                filtered = all_careers

            # 取 Top 10
            careers: list[Career] = filtered[:CAREER_RECOMMEND_LIMIT]

            serializer = CareerSerializer(careers, many=True)
            data: dict[str, object] = {
                "list": serializer.data,
                "total": len(careers),
            }

            logger.info(
                "职业推荐请求成功 | archetype=%s | riasec=%s | total=%d",
                archetype_id,
                riasec_code,
                len(careers),
            )
            return _success_response(data)

        except Exception as exc:
            logger.exception("职业推荐请求失败 | error=%s", str(exc))
            return _error_response(
                "CAREER_LIST_ERROR",
                "获取职业推荐失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
