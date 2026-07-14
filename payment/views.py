# 画己职测 — payment 视图
#
# 本模块实现支付订单相关的 API 视图（DRF APIView）：
#   - CreateOrderView:        POST   /api/orders/                        — 创建订单
#   - OrderStatusView:        GET    /api/orders/<order_id>/status/      — 查询订单状态（前端轮询）
#   - OrderListView:          GET    /api/orders/                        — 订单列表
#   - OrderDetailView:        GET    /api/orders/<order_id>/             — 订单详情
#   - WeChatCallbackView:     POST   /api/payment/wechat/callback/       — 微信支付回调
#   - AlipayCallbackView:     POST   /api/payment/alipay/callback/       — 支付宝回调
#   - CouponValidateView:     POST   /api/orders/coupon/                 — 优惠券验证

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.constants import DEEP_REPORT_PRICE
from common.utils import generate_session_token, mask_token
from payment.serializers import (
    CouponSerializer,
    CreateOrderSerializer,
)
from payment.services.callback_handler import handle_payment_callback
from payment.services.order_service import (
    create_order,
    get_order_detail,
    get_order_status,
    get_orders_by_session,
)
from payment.services.report_service import get_full_report

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


class CreateOrderView(APIView):
    """POST /api/orders/ — 创建支付订单。

    不需要认证。
    从中间件获取 device_fingerprint 和 session_token。
    接收 payment_channel, assessment_id（可选）, coupon_code（可选）。
    返回订单详情。
    """

    def post(self, request: Request) -> Response:
        """创建订单。"""
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("创建订单参数校验失败 | errors=%s", serializer.errors)
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

        payment_channel: str = serializer.validated_data["payment_channel"]
        assessment_id: int | None = serializer.validated_data.get("assessment_id")

        try:
            order_data: dict[str, object] = create_order(
                session_token=session_token,
                device_fingerprint=device_fingerprint,
                assessment_id=assessment_id,
                payment_channel=payment_channel,
            )

            response: Response = _success_response(order_data, message="订单创建成功")

            # 设置 session_token 到 Cookie
            response.set_cookie(
                "session_token",
                session_token,
                max_age=30 * 24 * 3600,
                httponly=True,
                samesite="Lax",
            )

            logger.info("订单创建成功 | order_id=%s", order_data.get("order_id"))
            return response

        except ValueError as exc:
            logger.warning("创建订单业务校验失败 | error=%s", str(exc))
            return _error_response("ORDER_CREATE_ERROR", str(exc))
        except Exception as exc:
            logger.exception("创建订单失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_CREATE_ERROR",
                "创建订单失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderStatusView(APIView):
    """GET /api/orders/<order_id>/status/ — 查询订单状态（前端轮询用）。

    不需要认证。
    返回订单状态、交易号等。
    """

    def get(self, request: Request, order_id: str) -> Response:
        """查询订单状态。"""
        if not order_id:
            return _error_response("MISSING_ORDER_ID", "缺少订单号")

        try:
            order_status_data: dict[str, object] | None = get_order_status(order_id)

            if order_status_data is None:
                logger.warning("订单状态查询失败 | 订单不存在 | order_id=%s", order_id)
                return _error_response(
                    "ORDER_NOT_FOUND",
                    "订单不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            return _success_response(order_status_data)

        except Exception as exc:
            logger.exception("查询订单状态失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_STATUS_ERROR",
                "查询订单状态失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderListView(APIView):
    """GET /api/orders/ — 订单列表。

    不需要认证。
    从中间件获取 session_token，查询该用户的订单列表。
    """

    def get(self, request: Request) -> Response:
        """查询订单列表。"""
        session_token: str = getattr(request, "session_token", "")

        if not session_token:
            return _error_response("MISSING_SESSION_TOKEN", "缺少会话令牌")

        try:
            orders: list[dict[str, object]] = get_orders_by_session(session_token)
            data: dict[str, object] = {
                "list": orders,
                "total": len(orders),
            }
            return _success_response(data)

        except Exception as exc:
            logger.exception("查询订单列表失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_LIST_ERROR",
                "查询订单列表失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OrderDetailView(APIView):
    """GET /api/orders/<order_id>/ — 订单详情。

    不需要认证。
    返回订单完整信息。
    """

    def get(self, request: Request, order_id: str) -> Response:
        """查询订单详情。"""
        if not order_id:
            return _error_response("MISSING_ORDER_ID", "缺少订单号")

        try:
            order_detail: dict[str, object] | None = get_order_detail(order_id)

            if order_detail is None:
                logger.warning("订单详情查询失败 | 订单不存在 | order_id=%s", order_id)
                return _error_response(
                    "ORDER_NOT_FOUND",
                    "订单不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            return _success_response(order_detail)

        except Exception as exc:
            logger.exception("查询订单详情失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_DETAIL_ERROR",
                "查询订单详情失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WeChatCallbackView(APIView):
    """POST /api/payment/wechat/callback/ — 微信支付回调。

    接收微信支付服务器发送的支付结果通知。
    调用 callback_handler.handle_payment_callback 处理。
    """

    def post(self, request: Request) -> Response:
        """处理微信支付回调。"""
        try:
            raw_data: dict[str, object] = request.data
            result: dict[str, object] = handle_payment_callback(
                raw_callback=raw_data,
                channel="wechat_pay",
            )

            if result.get("success"):
                logger.info(
                    "微信回调处理成功 | order_id=%s | duplicated=%s",
                    raw_data.get("out_trade_no", ""),
                    result.get("duplicated"),
                )
                # 微信要求返回 success
                return Response({"code": "SUCCESS", "message": "成功"})
            else:
                logger.warning(
                    "微信回调处理失败 | reason=%s",
                    result.get("reason", ""),
                )
                return Response(
                    {"code": "FAIL", "message": result.get("reason", "失败")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as exc:
            logger.exception("微信回调处理异常 | error=%s", str(exc))
            return Response(
                {"code": "FAIL", "message": "服务器内部错误"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AlipayCallbackView(APIView):
    """POST /api/payment/alipay/callback/ — 支付宝回调。

    接收支付宝服务器发送的支付结果通知。
    调用 callback_handler.handle_payment_callback 处理。
    """

    def post(self, request: Request) -> Response:
        """处理支付宝回调。"""
        try:
            raw_data: dict[str, object] = request.data
            result: dict[str, object] = handle_payment_callback(
                raw_callback=raw_data,
                channel="alipay",
            )

            if result.get("success"):
                logger.info(
                    "支付宝回调处理成功 | order_id=%s | duplicated=%s",
                    raw_data.get("out_trade_no", ""),
                    result.get("duplicated"),
                )
                # 支付宝要求返回 success
                return Response("success", content_type="text/plain")
            else:
                logger.warning(
                    "支付宝回调处理失败 | reason=%s",
                    result.get("reason", ""),
                )
                return Response(
                    "fail",
                    content_type="text/plain",
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as exc:
            logger.exception("支付宝回调处理异常 | error=%s", str(exc))
            return Response(
                "fail",
                content_type="text/plain",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CouponValidateView(APIView):
    """POST /api/orders/coupon/ — 优惠券验证。

    验证优惠券码是否有效。
    M3 阶段仅做格式校验，M4 阶段接入完整优惠券系统。
    """

    def post(self, request: Request) -> Response:
        """验证优惠券。"""
        serializer = CouponSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("优惠券验证参数校验失败 | errors=%s", serializer.errors)
            return _error_response(
                "VALIDATION_ERROR",
                "参数校验失败",
                detail=str(serializer.errors),
            )

        coupon_code: str = serializer.validated_data["coupon_code"]

        # M3 阶段：仅格式校验通过，返回无效优惠券
        # M4 阶段：接入完整优惠券系统
        logger.info("优惠券验证 | code=%s | 结果=暂未开放", coupon_code)

        data: dict[str, object] = {
            "valid": False,
            "discount": 0.0,
            "final_price": DEEP_REPORT_PRICE,
            "message": "优惠券功能暂未开放",
        }
        return _success_response(data, message="优惠券验证完成")


class DeepReportView(APIView):
    """GET /api/reports/<int:assessment_id>/ — 返回深度报告。

    不需要认证。
    先检查支付状态：
      - 已付费：返回完整 12 章报告内容
      - 未付费：返回 403 及预览数据（第 1 章完整 + 其余章节预览片段）
    """

    def get(self, request: Request, assessment_id: int) -> Response:
        """获取深度报告。"""
        if not assessment_id:
            return _error_response("MISSING_ASSESSMENT_ID", "缺少测评 ID")

        try:
            report_data: dict[str, object] = get_full_report(assessment_id)

            is_unlocked: bool = bool(report_data.get("is_unlocked", False))

            if is_unlocked:
                logger.info(
                    "深度报告请求成功（已解锁） | assessment_id=%d",
                    assessment_id,
                )
                return _success_response(report_data, message="深度报告获取成功")
            else:
                logger.info(
                    "深度报告请求（未解锁，返回预览） | assessment_id=%d",
                    assessment_id,
                )
                return Response(
                    {
                        "code": "PAYMENT_REQUIRED",
                        "message": "请先支付解锁完整深度报告",
                        "data": report_data,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        except ValueError as exc:
            logger.warning("深度报告请求失败 | assessment_id=%d | error=%s", assessment_id, str(exc))
            return _error_response(
                "ASSESSMENT_NOT_FOUND",
                str(exc),
                http_status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            logger.exception("深度报告请求异常 | assessment_id=%d | error=%s", assessment_id, str(exc))
            return _error_response(
                "REPORT_ERROR",
                "获取深度报告失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
