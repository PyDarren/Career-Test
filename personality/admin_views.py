# 画己职测 — personality Admin 视图
#
# 本模块实现后台内容配置相关的 Admin API 视图（DRF APIView）：
#   - AdminArchetypeListView:   GET /api/admin/content/archetypes/         — 画像列表
#   - AdminArchetypeUpdateView: PUT /api/admin/content/archetypes/<id>/    — 更新画像配置
#   - AdminCareerListView:      GET /api/admin/content/careers/            — 职业列表
#   - AdminCareerUpdateView:    PUT /api/admin/content/careers/<id>/       — 更新职业配置
#
# 说明：M4 阶段 Admin API 不需要认证，通过 URL 路径区分。

import logging
import re
from collections.abc import Sequence

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import AdminPermission
from careers.models import Career
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


def _range_label(value: str) -> str:
    """将区间值转换为中文标签。"""
    if value == PersonalityArchetype.DimensionRange.HIGH:
        return "高"
    if value == PersonalityArchetype.DimensionRange.LOW:
        return "低"
    return value or "-"


def _build_dimension_text(archetype: PersonalityArchetype) -> str:
    """构建维度组合文本，如 O高 C低 E高 A低 N低。"""
    parts: list[str] = [
        f"O{_range_label(archetype.o_range)}",
        f"C{_range_label(archetype.c_range)}",
        f"E{_range_label(archetype.e_range)}",
        f"A{_range_label(archetype.a_range)}",
        f"N{_range_label(archetype.n_range)}",
    ]
    return " ".join(parts)


def _strip_html(text: str) -> str:
    """去除 HTML 标签，保留纯文本。"""
    clean: str = re.sub(r"<[^>]+>", "", text or "")
    return clean.strip()


def _build_archetype_content(archetype: PersonalityArchetype) -> str:
    """根据画像字段生成可在富文本编辑器中展示的 HTML 内容。"""
    famous_str: str = "、".join(archetype.famous_people) if archetype.famous_people else "暂无"
    careers_str: str = "、".join(archetype.career_directions) if archetype.career_directions else "暂无"
    return (
        f"<h3>{archetype.archetype_name}</h3>"
        f"<p>{archetype.archetype_slogan}</p>"
        f"<p>维度组合：<strong>{_build_dimension_text(archetype)}</strong></p>"
        f"<p>稀有度：{archetype.rarity}（约 {archetype.rarity_percentage}%）</p>"
        f"<p>同型名人：{famous_str}</p>"
        f"<p>推荐职业方向：{careers_str}</p>"
    )


def _serialize_archetype(archetype: PersonalityArchetype) -> dict[str, object]:
    """序列化画像为前端所需结构。"""
    return {
        "id": archetype.archetype_id,
        "name": archetype.archetype_name,
        "code": archetype.archetype_code,
        "type": "archetype",
        "typeLabel": "人格画像",
        "status": "published",
        "content": _build_archetype_content(archetype),
        "slogan": archetype.archetype_slogan,
        "rarity": archetype.rarity,
        "rarityPercent": archetype.rarity_percentage,
        "famous": archetype.famous_people,
        "partners": archetype.best_partners,
        "careers": archetype.career_directions,
        "dimensions": {
            "O": archetype.o_range,
            "C": archetype.c_range,
            "E": archetype.e_range,
            "A": archetype.a_range,
            "N": archetype.n_range,
        },
        "dimensionText": _build_dimension_text(archetype),
        "mascot": archetype.mascot_url,
    }


def _serialize_career(career: Career) -> dict[str, object]:
    """序列化职业为前端所需结构。"""
    return {
        "id": career.id,
        "name": career.career_name,
        "desc": career.description,
        "category": career.career_category,
        "match": 0,
        "salary": career.salary_range or "",
        "growth": career.growth_prospect or "",
        "active": career.is_active,
    }


class AdminArchetypeListView(APIView):
    """GET /api/admin/content/archetypes/ — 画像列表。"""

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> Response:
        """获取画像列表。"""
        try:
            archetypes: Sequence[PersonalityArchetype] = list(
                PersonalityArchetype.objects.all().order_by("archetype_id")
            )
            data: list[dict[str, object]] = [_serialize_archetype(a) for a in archetypes]
            logger.info("画像列表请求成功 | count=%d", len(data))
            return _success_response({"list": data, "total": len(data)})
        except Exception as exc:
            logger.exception("画像列表请求失败 | error=%s", str(exc))
            return _error_response(
                "ARCHETYPE_LIST_ERROR",
                "获取画像列表失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminArchetypeUpdateView(APIView):
    """PUT /api/admin/content/archetypes/<id>/ — 更新画像配置。"""

    permission_classes = [AdminPermission]

    def put(self, request: Request, archetype_id: int) -> Response:
        """更新画像配置。"""
        try:
            try:
                archetype: PersonalityArchetype = PersonalityArchetype.objects.get(archetype_id=archetype_id)
            except PersonalityArchetype.DoesNotExist:
                logger.warning("画像不存在 | id=%s", archetype_id)
                return _error_response(
                    "ARCHETYPE_NOT_FOUND",
                    "画像不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            data = request.data
            if "name" in data:
                archetype.archetype_name = str(data.get("name") or archetype.archetype_name)
            if "slogan" in data:
                archetype.archetype_slogan = str(data.get("slogan") or archetype.archetype_slogan)[:200]
            elif "content" in data:
                # 富文本内容回写为纯文本一句话描述（截断 200 字）
                plain: str = _strip_html(str(data.get("content") or ""))
                if plain:
                    archetype.archetype_slogan = plain[:200]
            if "rarity" in data:
                archetype.rarity = str(data.get("rarity") or archetype.rarity)
            if "rarityPercent" in data:
                archetype.rarity_percentage = float(data.get("rarityPercent") or archetype.rarity_percentage)
            if "famous" in data and isinstance(data.get("famous"), list):
                archetype.famous_people = data.get("famous")
            if "partners" in data and isinstance(data.get("partners"), list):
                archetype.best_partners = data.get("partners")
            if "careers" in data and isinstance(data.get("careers"), list):
                archetype.career_directions = data.get("careers")
            if "mascot" in data:
                archetype.mascot_url = str(data.get("mascot") or archetype.mascot_url)

            archetype.save()

            logger.info("画像更新成功 | id=%d", archetype_id)
            return _success_response(
                _serialize_archetype(archetype),
                message="更新画像成功",
            )
        except Exception as exc:
            logger.exception("画像更新失败 | id=%s | error=%s", archetype_id, str(exc))
            return _error_response(
                "ARCHETYPE_UPDATE_ERROR",
                "更新画像失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminCareerListView(APIView):
    """GET /api/admin/content/careers/ — 职业列表。"""

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> Response:
        """获取职业列表。"""
        try:
            careers: Sequence[Career] = list(Career.objects.all().order_by("career_name"))
            data: list[dict[str, object]] = [_serialize_career(c) for c in careers]
            logger.info("职业列表请求成功 | count=%d", len(data))
            return _success_response({"list": data, "total": len(data)})
        except Exception as exc:
            logger.exception("职业列表请求失败 | error=%s", str(exc))
            return _error_response(
                "CAREER_LIST_ERROR",
                "获取职业列表失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminCareerUpdateView(APIView):
    """PUT /api/admin/content/careers/<id>/ — 更新职业配置。"""

    permission_classes = [AdminPermission]

    def put(self, request: Request, career_id: int) -> Response:
        """更新职业配置。"""
        try:
            try:
                career: Career = Career.objects.get(id=career_id)
            except Career.DoesNotExist:
                logger.warning("职业不存在 | id=%s", career_id)
                return _error_response(
                    "CAREER_NOT_FOUND",
                    "职业不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            data = request.data
            if "name" in data:
                career.career_name = str(data.get("name") or career.career_name)
            if "category" in data:
                career.career_category = str(data.get("category") or career.career_category)
            if "desc" in data or "description" in data:
                career.description = str(data.get("desc") or data.get("description") or career.description)
            if "salary" in data:
                career.salary_range = str(data.get("salary") or "")
            if "growth" in data:
                career.growth_prospect = str(data.get("growth") or "")
            if "active" in data:
                career.is_active = bool(data.get("active"))

            career.save()

            logger.info("职业更新成功 | id=%d", career_id)
            return _success_response(
                _serialize_career(career),
                message="更新职业成功",
            )
        except Exception as exc:
            logger.exception("职业更新失败 | id=%s | error=%s", career_id, str(exc))
            return _error_response(
                "CAREER_UPDATE_ERROR",
                "更新职业失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
