# 画己职测 — assessment 视图
#
# 本模块实现测评相关的 API 视图（DRF APIView）：
#   - QuestionListView: GET /api/questions/ — 获取 80 题题库
#   - AssessmentSubmitView: POST /api/assessments/ — 提交测评答案
#   - AssessmentResultView: GET /api/assessments/<session_token>/ — 查询测评结果

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from assessment.models import Question as QuestionModel
from assessment.serializers import (
    AssessmentResultSerializer,
    AssessmentSubmitSerializer,
    QuestionSerializer,
)
from assessment.services.test_service import (
    get_assessment_result,
    submit_assessment,
)
from common.utils import generate_session_token, mask_token

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


class QuestionListView(APIView):
    """GET /api/questions/ — 获取 80 题题库。

    不需要认证，免登录。
    从 Redis 缓存读取，TTL 1 小时。
    返回统一格式 {"code": 0, "data": {"list": [...], "total": 80}, "message": "success"}
    """

    def get(self, request: Request) -> Response:
        """获取题库列表。"""
        try:
            # 直接查询 Django 模型（get_questions_for_scoring 返回 Pydantic 对象，仅供计分引擎用）
            # 使用 .only() 限制查询字段，避免拉取不必要的列
            questions = (
                QuestionModel.objects.filter(is_active=True)
                .only("id", "question_text", "question_type", "dimension_prefix", "order", "is_active")
                .order_by("order")
            )
            serializer = QuestionSerializer(questions, many=True)
            data: dict[str, object] = {
                "list": serializer.data,
                "total": len(serializer.data),
            }
            logger.info("题库列表请求成功 | total=%d", data["total"])
            return _success_response(data)
        except Exception as exc:
            logger.exception("题库列表请求失败 | error=%s", str(exc))
            return _error_response(
                "QUESTION_LIST_ERROR",
                "获取题库失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AssessmentSubmitView(APIView):
    """POST /api/assessments/ — 提交测评答案。

    不需要认证。
    从中间件获取 device_fingerprint 和 session_token。
    调用 test_service.submit_assessment()。
    返回 AssessmentResultSerializer 序列化结果。
    """

    def post(self, request: Request) -> Response:
        """提交测评答案。"""
        # 序列化验证
        serializer = AssessmentSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "测评提交参数校验失败 | errors=%s",
                serializer.errors,
            )
            return _error_response(
                "VALIDATION_ERROR",
                "参数校验失败",
                detail=str(serializer.errors),
            )

        # 从中间件获取设备指纹和会话令牌
        device_fingerprint: str = getattr(request, "device_fingerprint", "")
        session_token: str = getattr(request, "session_token", "")

        # 若无 session_token，生成新的
        if not session_token:
            session_token = generate_session_token()
            logger.info("生成新 session | masked=%s", mask_token(session_token))

        try:
            result: dict[str, object] = submit_assessment(
                serializer.validated_data,
                device_fingerprint,
                session_token,
            )

            # 序列化结果
            result_serializer = AssessmentResultSerializer(data=result)
            if not result_serializer.is_valid():
                logger.error(
                    "结果序列化失败 | errors=%s",
                    result_serializer.errors,
                )
                return _error_response(
                    "SERIALIZATION_ERROR",
                    "结果序列化失败",
                    detail=str(result_serializer.errors),
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            response: Response = _success_response(result_serializer.validated_data)

            # 设置 session_token 到 Cookie
            response.set_cookie(
                "session_token",
                session_token,
                max_age=30 * 24 * 3600,  # 30 天
                httponly=True,
                samesite="Lax",
            )

            logger.info("测评提交成功 | session=%s", mask_token(session_token))
            return response

        except ValueError as exc:
            logger.warning("测评提交业务校验失败 | error=%s", str(exc))
            return _error_response(
                "SUBMIT_VALIDATION_ERROR",
                str(exc),
            )
        except Exception as exc:
            logger.exception("测评提交失败 | error=%s", str(exc))
            return _error_response(
                "SUBMIT_ERROR",
                "测评提交失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AssessmentResultView(APIView):
    """GET /api/assessments/<session_token>/ — 查询测评结果。

    需要验证请求者身份：请求头 X-Session-Token 必须与 URL 中的 session_token 一致，
    不一致返回 403，防止越权访问他人测评结果。
    调用 test_service.get_assessment_result()。
    返回三层标签 + 五维度分数 + 色彩光谱。
    """

    def get(self, request: Request, session_token: str) -> Response:
        """查询测评结果。"""
        if not session_token:
            return _error_response(
                "MISSING_SESSION_TOKEN",
                "缺少会话令牌",
            )

        # 越权防护：验证请求头中的 session_token 与 URL 中的 token 一致
        request_session_token: str = getattr(request, "session_token", "")
        if not request_session_token or request_session_token != session_token:
            logger.warning(
                "越权访问拦截 | url_session=%s | request_session=%s",
                mask_token(session_token),
                mask_token(request_session_token),
            )
            return _error_response(
                "FORBIDDEN",
                "无权访问该测评结果",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result: dict[str, object] | None = get_assessment_result(session_token)

            if result is None:
                logger.warning("测评结果不存在 | session=%s", mask_token(session_token))
                return _error_response(
                    "RESULT_NOT_FOUND",
                    "测评结果不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            # 序列化结果
            result_serializer = AssessmentResultSerializer(data=result)
            if not result_serializer.is_valid():
                logger.error(
                    "结果序列化失败 | errors=%s",
                    result_serializer.errors,
                )
                return _error_response(
                    "SERIALIZATION_ERROR",
                    "结果序列化失败",
                    detail=str(result_serializer.errors),
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info("测评结果查询成功 | session=%s", mask_token(session_token))
            return _success_response(result_serializer.validated_data)

        except Exception as exc:
            logger.exception("测评结果查询失败 | error=%s", str(exc))
            return _error_response(
                "RESULT_QUERY_ERROR",
                "查询测评结果失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
