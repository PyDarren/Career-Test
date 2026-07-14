# 画己职测 — assessment Admin 视图
#
# 本模块实现后台题库管理相关的 Admin API 视图（DRF APIView）：
#   - AdminQuestionListView:    GET    /api/admin/questions/         — 题目列表（筛选/分页/统计）
#   - AdminQuestionCreateView:  POST   /api/admin/questions/         — 新增题目
#   - AdminQuestionUpdateView:  PUT    /api/admin/questions/<id>/    — 更新题目
#   - AdminQuestionDeleteView:  DELETE /api/admin/questions/<id>/    — 删除题目
#   - AdminQuestionExportView:  GET    /api/admin/questions/export/  — 导出 CSV
#
# 说明：M4 阶段 Admin API 不需要认证，通过 URL 路径区分。
#       由于题目列表(GET)与新增(POST)共用同一路径、更新(PUT)与删除(DELETE)共用
#       同一路径，Django URL 解析仅按路径匹配，因此使用组合视图同时承载多个方法。

import csv
import logging
from collections.abc import Sequence
from datetime import datetime

from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import AdminPermission
from assessment.models import Question
from stats.models import TrackingEvent

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE: int = 10
MAX_PAGE_SIZE: int = 100

# 维度前缀中文名映射
DIMENSION_LABELS: dict[str, str] = {
    "BO": "开放性 (BO)",
    "BC": "尽责性 (BC)",
    "BE": "外向性 (BE)",
    "BA": "宜人性 (BA)",
    "BN": "神经质 (BN)",
    "RR": "现实型 (RR)",
    "RI": "研究型 (RI)",
    "RA": "艺术型 (RA)",
    "RS": "社会型 (RS)",
    "RE": "企业型 (RE)",
    "RC": "常规型 (RC)",
}

# 题目状态中文映射
QUESTION_STATUS_LABELS: dict[str, str] = {
    "active": "启用中",
    "inactive": "已停用",
    "grayscale": "灰度中",
}


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


def _format_dt(dt: datetime | None) -> str:
    """格式化时间为字符串。"""
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _derive_question_type(dimension_prefix: str) -> str:
    """根据维度前缀推导题目类型。"""
    if not dimension_prefix:
        return Question.QuestionType.OCEAN
    first: str = dimension_prefix[0].upper()
    if first == "R":
        return Question.QuestionType.RIASEC
    if first == "B":
        return Question.QuestionType.OCEAN
    return Question.QuestionType.VALIDITY


def _derive_status(is_active: bool) -> str:
    """根据 is_active 推导状态字符串。"""
    return "active" if is_active else "inactive"


def _serialize_question(q: Question) -> dict[str, object]:
    """序列化题目为前端所需结构。"""
    return {
        "id": q.id,
        "question": q.question_text,
        "optionA": "非常不符合",
        "optionB": "非常符合",
        "weight": 3,
        "category": q.dimension_prefix,
        "categoryLabel": DIMENSION_LABELS.get(q.dimension_prefix, q.dimension_prefix),
        "questionType": q.question_type,
        "isReverse": q.is_reverse,
        "order": q.order,
        "status": _derive_status(q.is_active),
        "createdAt": _format_dt(q.created_at),
        "updatedAt": _format_dt(q.updated_at),
        "logs": _build_question_logs(q),
    }


def _build_question_logs(q: Question) -> list[dict[str, str]]:
    """构建题目操作日志（基于创建/更新时间）。"""
    logs: list[dict[str, str]] = [
        {
            "time": _format_dt(q.created_at),
            "author": "系统",
            "action": "创建题目",
        }
    ]
    if q.updated_at and q.updated_at != q.created_at:
        logs.append(
            {
                "time": _format_dt(q.updated_at),
                "author": "管理员",
                "action": "编辑题目",
            }
        )
    return logs


def _apply_filters(queryset: QuerySet[Question], params) -> QuerySet[Question]:
    """应用筛选条件。"""
    search: str = params.get("search", "")
    category: str = params.get("category", "")
    q_status: str = params.get("status", "")

    if search:
        queryset = queryset.filter(question_text__icontains=search)
    if category:
        queryset = queryset.filter(dimension_prefix=category)
    if q_status == "active":
        queryset = queryset.filter(is_active=True)
    elif q_status == "inactive":
        queryset = queryset.filter(is_active=False)
    elif q_status == "grayscale":
        # 当前模型不支持灰度状态，灰度题集合为空
        queryset = queryset.none()
    return queryset


def _compute_stats(queryset: QuerySet[Question]) -> dict[str, int]:
    """计算题目统计概览（总数、启用数、灰度数）。"""
    total_qs = Question.objects.all()
    total: int = total_qs.count()
    active: int = total_qs.filter(is_active=True).count()
    # 当前模型不支持灰度状态，灰度数为 0
    grayscale: int = 0
    return {"total": total, "active": active, "grayscale": grayscale}


class AdminQuestionListView(APIView):
    """GET /api/admin/questions/ — 题目列表。

    支持筛选：search, category, status
    支持分页：page, page_size
    返回：list + total + stats（总数、启用数、灰度数）
    """

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> Response:
        """获取题目列表。"""
        try:
            params = request.query_params
            queryset = Question.objects.all().order_by("order", "id")
            queryset = _apply_filters(queryset, params)

            stats_data: dict[str, int] = _compute_stats(queryset)
            total: int = queryset.count()

            page: int = max(int(params.get("page", 1) or 1), 1)
            page_size: int = int(params.get("page_size", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE)
            page_size = max(min(page_size, MAX_PAGE_SIZE), 1)

            start_idx: int = (page - 1) * page_size
            page_questions: Sequence[Question] = list(queryset[start_idx : start_idx + page_size])
            question_list: list[dict[str, object]] = [_serialize_question(q) for q in page_questions]

            data: dict[str, object] = {
                "list": question_list,
                "total": total,
                "page": page,
                "pageSize": page_size,
                "stats": stats_data,
            }
            logger.info("题目列表请求成功 | total=%d | page=%d", total, page)
            return _success_response(data)
        except Exception as exc:
            logger.exception("题目列表请求失败 | error=%s", str(exc))
            return _error_response(
                "QUESTION_LIST_ERROR",
                "获取题目列表失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminQuestionCreateView(APIView):
    """POST /api/admin/questions/ — 新增题目。"""

    permission_classes = [AdminPermission]

    def post(self, request: Request) -> Response:
        """新增题目。"""
        try:
            data = request.data
            question_text: str = (data.get("question") or data.get("question_text") or "").strip()
            category: str = (data.get("category") or "").strip()
            q_status: str = (data.get("status") or "active").strip()

            if not question_text:
                return _error_response("MISSING_QUESTION_TEXT", "题目内容不能为空")
            if not category:
                return _error_response("MISSING_CATEGORY", "维度前缀不能为空")

            # 计算排序序号
            max_order = Question.objects.all().order_by("-order").first()
            next_order: int = (max_order.order + 1) if max_order else 1

            question = Question.objects.create(
                question_text=question_text,
                dimension_prefix=category,
                is_reverse=bool(data.get("isReverse", False)),
                question_type=_derive_question_type(category),
                order=int(data.get("order", next_order) or next_order),
                is_active=(q_status != "inactive"),
            )

            # 记录埋点
            TrackingEvent.objects.create(
                device_fingerprint=request.META.get("HTTP_X_DEVICE_FINGERPRINT", "admin"),
                session_token=request.META.get("HTTP_X_SESSION_TOKEN", "admin"),
                event_type="admin_operation",
                event_data={"action": "create_question", "question_id": question.id},
            )

            logger.info("题目新增成功 | id=%d", question.id)
            return _success_response(
                _serialize_question(question),
                message="新增题目成功",
            )
        except Exception as exc:
            logger.exception("题目新增失败 | error=%s", str(exc))
            return _error_response(
                "QUESTION_CREATE_ERROR",
                "新增题目失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminQuestionUpdateView(APIView):
    """PUT /api/admin/questions/<id>/ — 更新题目。"""

    permission_classes = [AdminPermission]

    def put(self, request: Request, question_id: int) -> Response:
        """更新题目。"""
        try:
            try:
                question: Question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                logger.warning("题目不存在 | id=%s", question_id)
                return _error_response(
                    "QUESTION_NOT_FOUND",
                    "题目不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            data = request.data
            if "question" in data or "question_text" in data:
                question.question_text = (data.get("question") or data.get("question_text") or "").strip()
            if "category" in data:
                new_category: str = (data.get("category") or "").strip()
                if new_category:
                    question.dimension_prefix = new_category
                    question.question_type = _derive_question_type(new_category)
            if "isReverse" in data:
                question.is_reverse = bool(data.get("isReverse"))
            if "order" in data:
                question.order = int(data.get("order") or question.order)
            if "status" in data:
                q_status: str = (data.get("status") or "active").strip()
                question.is_active = q_status != "inactive"

            question.save()

            TrackingEvent.objects.create(
                device_fingerprint=request.META.get("HTTP_X_DEVICE_FINGERPRINT", "admin"),
                session_token=request.META.get("HTTP_X_SESSION_TOKEN", "admin"),
                event_type="admin_operation",
                event_data={"action": "update_question", "question_id": question.id},
            )

            logger.info("题目更新成功 | id=%d", question.id)
            return _success_response(
                _serialize_question(question),
                message="更新题目成功",
            )
        except Exception as exc:
            logger.exception("题目更新失败 | id=%s | error=%s", question_id, str(exc))
            return _error_response(
                "QUESTION_UPDATE_ERROR",
                "更新题目失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminQuestionDeleteView(APIView):
    """DELETE /api/admin/questions/<id>/ — 删除题目。"""

    permission_classes = [AdminPermission]

    def delete(self, request: Request, question_id: int) -> Response:
        """删除题目。"""
        try:
            try:
                question: Question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                logger.warning("题目不存在 | id=%s", question_id)
                return _error_response(
                    "QUESTION_NOT_FOUND",
                    "题目不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            TrackingEvent.objects.create(
                device_fingerprint=request.META.get("HTTP_X_DEVICE_FINGERPRINT", "admin"),
                session_token=request.META.get("HTTP_X_SESSION_TOKEN", "admin"),
                event_type="admin_operation",
                event_data={"action": "delete_question", "question_id": question.id},
            )

            question.delete()

            logger.info("题目删除成功 | id=%d", question_id)
            return _success_response({"id": question_id}, message="删除题目成功")
        except Exception as exc:
            logger.exception("题目删除失败 | id=%s | error=%s", question_id, str(exc))
            return _error_response(
                "QUESTION_DELETE_ERROR",
                "删除题目失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# 组合视图：同时处理列表(GET)与新增(POST)
class AdminQuestionListCreateView(AdminQuestionListView, AdminQuestionCreateView):
    """GET/POST /api/admin/questions/ — 题目列表与新增的组合视图。"""

    permission_classes = [AdminPermission]

    pass


# 组合视图：同时处理更新(PUT)与删除(DELETE)
class AdminQuestionItemView(AdminQuestionUpdateView, AdminQuestionDeleteView):
    """PUT/DELETE /api/admin/questions/<id>/ — 更新与删除的组合视图。"""

    permission_classes = [AdminPermission]

    pass


class AdminQuestionExportView(APIView):
    """GET /api/admin/questions/export/ — 导出题目 CSV。"""

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> HttpResponse:
        """导出题目 CSV 文件。"""
        try:
            params = request.query_params
            queryset = Question.objects.all().order_by("order", "id")
            queryset = _apply_filters(queryset, params)

            response: HttpResponse = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = (
                'attachment; filename="questions_export_' + timezone.now().strftime("%Y%m%d") + '.csv"'
            )
            # UTF-8 BOM，兼容 Excel
            response.write("\ufeff")
            writer = csv.writer(response)

            writer.writerow(["序号", "维度", "题目陈述", "题目类型", "是否反向", "是否启用", "创建时间", "更新时间"])
            for q in queryset:
                writer.writerow(
                    [
                        q.order,
                        q.dimension_prefix,
                        q.question_text,
                        q.get_question_type_display(),
                        "是" if q.is_reverse else "否",
                        "是" if q.is_active else "否",
                        _format_dt(q.created_at),
                        _format_dt(q.updated_at),
                    ]
                )

            logger.info("题目导出成功 | count=%d", queryset.count())
            return response
        except Exception as exc:
            logger.exception("题目导出失败 | error=%s", str(exc))
            return _error_response(
                "QUESTION_EXPORT_ERROR",
                "导出题目失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
