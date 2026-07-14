# 画己职测 — payment Admin 视图
#
# 本模块实现后台订单管理相关的 Admin API 视图（DRF APIView）：
#   - AdminOrderListView:    GET /api/admin/orders/           — 订单列表（筛选/分页/统计）
#   - AdminOrderDetailView:  GET /api/admin/orders/<order_id>/ — 订单详情 + 操作日志
#   - AdminOrderExportView:  GET /api/admin/orders/export/    — 导出 CSV
#
# 说明：M4 阶段 Admin API 不需要认证，通过 URL 路径区分。

import csv
import logging
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from django.db.models import QuerySet, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import AdminPermission
from payment.models import Order
from stats.models import TrackingEvent

logger = logging.getLogger(__name__)

# 订单状态中文映射
ORDER_STATUS_LABELS: dict[str, str] = {
    "pending": "待支付",
    "paid": "已支付",
    "expired": "已过期",
    "failed": "支付失败",
    "refunded": "已退款",
}

# 支付渠道中文名映射
PAYMENT_CHANNEL_LABELS: dict[str, str] = {
    "wechat_pay": "微信支付",
    "alipay": "支付宝",
}

DEFAULT_PAGE_SIZE: int = 10
MAX_PAGE_SIZE: int = 100


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


def _serialize_order(order: Order) -> dict[str, object]:
    """序列化订单为前端所需结构。"""
    channel_label: str = PAYMENT_CHANNEL_LABELS.get(order.payment_channel or "", order.payment_channel or "")
    return {
        "orderNo": order.order_id,
        "time": _format_dt(order.created_at),
        "amount": float(order.amount),
        "product": order.product_name,
        "status": order.status,
        "statusLabel": ORDER_STATUS_LABELS.get(order.status, order.status),
        "txnNo": order.transaction_id or "",
        "payMethod": channel_label,
        "payTime": _format_dt(order.paid_at),
        "user": order.session_token[:12] if order.session_token else "",
        "sessionToken": order.session_token,
        "assessmentId": order.assessment_id,
        "expiredAt": _format_dt(order.expired_at),
        "updatedAt": _format_dt(order.updated_at),
    }


def _apply_filters(queryset: QuerySet[Order], params) -> QuerySet[Order]:
    """应用筛选条件。"""
    date_start: str = params.get("date_start", "")
    date_end: str = params.get("date_end", "")
    order_status: str = params.get("status", "")
    amount_min: str = params.get("amount_min", "")
    amount_max: str = params.get("amount_max", "")
    order_no: str = params.get("order_no", "")

    if date_start:
        queryset = queryset.filter(created_at__date__gte=date_start)
    if date_end:
        queryset = queryset.filter(created_at__date__lte=date_end)
    if order_status:
        queryset = queryset.filter(status=order_status)
    if amount_min:
        try:
            queryset = queryset.filter(amount__gte=Decimal(amount_min))
        except (ValueError, TypeError):
            pass
    if amount_max:
        try:
            queryset = queryset.filter(amount__lte=Decimal(amount_max))
        except (ValueError, TypeError):
            pass
    if order_no:
        queryset = queryset.filter(order_id__icontains=order_no)
    return queryset


def _compute_stats(queryset) -> dict[str, object]:
    """计算订单统计概览。"""
    total_orders: int = queryset.count()
    paid_qs = queryset.filter(status=Order.OrderStatus.PAID)
    paid_count: int = paid_qs.count()
    total_amount: Decimal = paid_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    refunded_qs = queryset.filter(status=Order.OrderStatus.REFUNDED)
    refund_amount: Decimal = refunded_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    success_rate: float = (paid_count / total_orders * 100) if total_orders > 0 else 0.0

    return {
        "totalOrders": total_orders,
        "totalAmount": float(total_amount),
        "successRate": round(success_rate, 1),
        "refundAmount": float(refund_amount),
    }


def _build_order_logs(order: Order) -> list[dict[str, str]]:
    """构建订单操作日志（M4 阶段从 TrackingEvent 查询）。"""
    logs: list[dict[str, str]] = []

    # 订单创建
    logs.append(
        {
            "time": _format_dt(order.created_at),
            "author": "系统",
            "action": "创建订单",
        }
    )

    # 支付回调埋点
    pay_events: Sequence[TrackingEvent] = list(
        TrackingEvent.objects.filter(
            session_token=order.session_token,
            event_type__in=["click_pay", "pay_success"],
        ).order_by("created_at")
    )
    for ev in pay_events:
        action: str = "支付成功" if ev.event_type == "pay_success" else "点击支付"
        logs.append(
            {
                "time": _format_dt(ev.created_at),
                "author": "支付回调" if ev.event_type == "pay_success" else "用户",
                "action": action,
            }
        )

    # 支付时间
    if order.paid_at and order.status == Order.OrderStatus.PAID:
        if not any(l["action"] == "支付成功" for l in logs):
            logs.append(
                {
                    "time": _format_dt(order.paid_at),
                    "author": "支付回调",
                    "action": "支付成功",
                }
            )

    # 退款
    if order.status == Order.OrderStatus.REFUNDED:
        logs.append(
            {
                "time": _format_dt(order.updated_at),
                "author": "系统",
                "action": "退款完成",
            }
        )

    # 过期
    if order.status == Order.OrderStatus.EXPIRED:
        logs.append(
            {
                "time": _format_dt(order.expired_at or order.updated_at),
                "author": "系统",
                "action": "订单过期",
            }
        )

    # 失败
    if order.status == Order.OrderStatus.FAILED:
        logs.append(
            {
                "time": _format_dt(order.updated_at),
                "author": "支付回调",
                "action": "支付失败",
            }
        )

    # 按时间排序
    logs.sort(key=lambda x: x["time"])
    return logs


class AdminOrderListView(APIView):
    """GET /api/admin/orders/ — 订单列表。

    支持筛选：date_start, date_end, status, amount_min, amount_max, order_no
    支持分页：page, page_size
    返回：list + total + stats（总订单数、总金额、成功率、退款总额）
    """

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> Response:
        """获取订单列表。"""
        try:
            params = request.query_params
            queryset = Order.objects.all().order_by("-created_at")
            queryset = _apply_filters(queryset, params)

            # 统计基于筛选后的全集
            stats_data: dict[str, object] = _compute_stats(queryset)

            total: int = queryset.count()

            # 分页
            page: int = max(int(params.get("page", 1) or 1), 1)
            page_size: int = int(params.get("page_size", DEFAULT_PAGE_SIZE) or DEFAULT_PAGE_SIZE)
            page_size = max(min(page_size, MAX_PAGE_SIZE), 1)

            start_idx: int = (page - 1) * page_size
            page_orders: Sequence[Order] = list(queryset[start_idx : start_idx + page_size])
            order_list: list[dict[str, object]] = [_serialize_order(o) for o in page_orders]

            data: dict[str, object] = {
                "list": order_list,
                "total": total,
                "page": page,
                "pageSize": page_size,
                "stats": stats_data,
            }
            logger.info("订单列表请求成功 | total=%d | page=%d", total, page)
            return _success_response(data)
        except Exception as exc:
            logger.exception("订单列表请求失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_LIST_ERROR",
                "获取订单列表失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminOrderDetailView(APIView):
    """GET /api/admin/orders/<order_id>/ — 订单详情。

    返回订单完整信息 + 操作日志（M4 阶段操作日志从 TrackingEvent 查询）。
    """

    permission_classes = [AdminPermission]

    def get(self, request: Request, order_id: str) -> Response:
        """获取订单详情。"""
        if not order_id:
            return _error_response("MISSING_ORDER_ID", "缺少订单号")

        try:
            try:
                order: Order = Order.objects.get(order_id=order_id)
            except Order.DoesNotExist:
                logger.warning("订单不存在 | order_id=%s", order_id)
                return _error_response(
                    "ORDER_NOT_FOUND",
                    "订单不存在",
                    http_status=status.HTTP_404_NOT_FOUND,
                )

            order_data: dict[str, object] = _serialize_order(order)
            order_data["logs"] = _build_order_logs(order)

            logger.info("订单详情请求成功 | order_id=%s", order_id)
            return _success_response(order_data)
        except Exception as exc:
            logger.exception("订单详情请求失败 | order_id=%s | error=%s", order_id, str(exc))
            return _error_response(
                "ORDER_DETAIL_ERROR",
                "获取订单详情失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AdminOrderExportView(APIView):
    """GET /api/admin/orders/export/ — 导出订单 CSV。"""

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> HttpResponse:
        """导出订单 CSV 文件。"""
        try:
            params = request.query_params
            queryset = Order.objects.all().order_by("-created_at")
            queryset = _apply_filters(queryset, params)

            response: HttpResponse = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = (
                'attachment; filename="orders_export_' + timezone.now().strftime("%Y%m%d") + '.csv"'
            )
            # UTF-8 BOM，兼容 Excel
            response.write("\ufeff")
            writer = csv.writer(response)

            writer.writerow(
                [
                    "商户订单号",
                    "下单时间",
                    "支付金额",
                    "商品名称",
                    "订单状态",
                    "支付方式",
                    "交易号",
                    "支付时间",
                    "用户标识",
                ]
            )
            for order in queryset:
                writer.writerow(
                    [
                        order.order_id,
                        _format_dt(order.created_at),
                        f"{order.amount:.2f}",
                        order.product_name,
                        ORDER_STATUS_LABELS.get(order.status, order.status),
                        PAYMENT_CHANNEL_LABELS.get(order.payment_channel or "", order.payment_channel or ""),
                        order.transaction_id or "",
                        _format_dt(order.paid_at),
                        order.session_token[:12] if order.session_token else "",
                    ]
                )

            logger.info("订单导出成功 | count=%d", queryset.count())
            return response
        except Exception as exc:
            logger.exception("订单导出失败 | error=%s", str(exc))
            return _error_response(
                "ORDER_EXPORT_ERROR",
                "导出订单失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
