# 画己职测 — stats Admin 视图
#
# 本模块实现后台数据看板相关的 Admin API 视图（DRF APIView）：
#   - DashboardView:        GET /api/admin/dashboard/         — 看板数据（KPI/趋势/漏斗/告警）
#   - DashboardExportView:  GET /api/admin/dashboard/export/  — 导出看板数据（CSV）
#
# 说明：M4 阶段 Admin API 不需要认证，通过 URL 路径区分。

import csv
import logging
from collections.abc import Sequence
from datetime import date, timedelta

from django.db.models import Avg, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import AdminPermission
from assessment.models import Assessment
from payment.models import Order
from stats.models import StatsDaily, TrackingEvent

logger = logging.getLogger(__name__)

# 图表配色（与前端 admin-dashboard.js CONFIG.colors 保持一致）
COLOR_GREEN: str = "#5ea67e"
COLOR_BLUE: str = "#5a96b1"
COLOR_PURPLE: str = "#9B7ED8"
COLOR_GOLD: str = "#deb45c"
COLOR_TEAL: str = "#7DD3C0"
COLOR_RED: str = "#e17055"

# 漏斗步骤颜色标识（与前端 CSS funnel-step__bar--N 对应）
FUNNEL_COLORS: list[str] = ["1", "2", "3", "4", "5"]

# 支付渠道中文名映射
PAYMENT_CHANNEL_LABELS: dict[str, str] = {
    "wechat_pay": "微信支付",
    "alipay": "支付宝",
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


def _get_date_range(range_param: str) -> tuple[date, date, int]:
    """根据 range 参数返回 (start_date, end_date, days)。

    :param range_param: yesterday / 7d / 30d
    :return: 起始日期、结束日期、天数
    """
    today: date = timezone.now().date()
    if range_param == "yesterday":
        start: date = today - timedelta(days=1)
        end: date = today - timedelta(days=1)
        return start, end, 1
    if range_param == "30d":
        return today - timedelta(days=29), today, 30
    # 默认 7d
    return today - timedelta(days=6), today, 7


def _format_int(value: float) -> str:
    """格式化整数（千分位）。"""
    return f"{int(round(value)):,}"


def _format_percent(value: float) -> str:
    """格式化百分比（保留 1 位小数）。"""
    return f"{value:.1f}%"


def _format_yuan(value: float) -> str:
    """格式化金额。"""
    return f"¥{value:.2f}"


def _compute_change(current: float, previous: float) -> tuple[str, str]:
    """计算环比变化，返回 (change 文本, direction)。"""
    if previous == 0:
        if current == 0:
            return "0%", "flat"
        return "+100%", "up"
    diff: float = (current - previous) / previous * 100
    if abs(diff) < 0.05:
        return "0%", "flat"
    sign: str = "+" if diff > 0 else ""
    direction: str = "up" if diff > 0 else "down"
    return f"{sign}{diff:.1f}%", direction


def _d7_retention(target_date: date) -> float:
    """计算目标日期的 D7 留存率。

    D7 留存 = 在 target_date 活跃且在 target_date-7 也活跃的设备数
    / target_date-7 活跃设备数。
    """
    base_date: date = target_date - timedelta(days=7)
    base_devices: set[str] = set(
        TrackingEvent.objects.filter(created_at__date=base_date).values_list("device_fingerprint", flat=True)
    )
    if not base_devices:
        return 0.0
    target_devices: set[str] = set(
        TrackingEvent.objects.filter(created_at__date=target_date).values_list("device_fingerprint", flat=True)
    )
    retained: int = len(base_devices & target_devices)
    return retained / len(base_devices) * 100


def _build_kpi_item(
    label: str,
    value: str,
    current: float,
    previous: float,
    icon: str,
    sparkline: Sequence[float],
) -> dict[str, object]:
    """构建单个 KPI 卡片数据。"""
    change, direction = _compute_change(current, previous)
    return {
        "label": label,
        "value": value,
        "change": change,
        "direction": direction,
        "icon": icon,
        "sparkline": list(sparkline),
    }


def _build_kpi(range_param: str) -> dict[str, dict[str, object]]:
    """构建 KPI 数据。"""
    start, end, days = _get_date_range(range_param)
    stats_qs = StatsDaily.objects.filter(date__gte=start, date__lte=end)

    agg = stats_qs.aggregate(
        avg_dau=Avg("dau"),
        avg_completion=Avg("completion_rate"),
        avg_conversion=Avg("conversion_rate"),
        sum_revenue=Sum("revenue"),
        sum_payment=Sum("payment_count"),
        avg_share=Avg("share_rate"),
    )
    avg_dau: float = float(agg["avg_dau"] or 0)
    avg_completion: float = float(agg["avg_completion"] or 0)
    avg_conversion: float = float(agg["avg_conversion"] or 0)
    sum_revenue: float = float(agg["sum_revenue"] or 0)
    sum_payment: int = int(agg["sum_payment"] or 0)
    avg_share: float = float(agg["avg_share"] or 0)
    avg_order: float = sum_revenue / sum_payment if sum_payment else 0.0
    d7_ret: float = _d7_retention(end)

    # 上一周期
    prev_start: date = start - timedelta(days=days)
    prev_end: date = start - timedelta(days=1)
    prev_qs = StatsDaily.objects.filter(date__gte=prev_start, date__lte=prev_end)
    prev_agg = prev_qs.aggregate(
        avg_dau=Avg("dau"),
        avg_completion=Avg("completion_rate"),
        avg_conversion=Avg("conversion_rate"),
        sum_revenue=Sum("revenue"),
        sum_payment=Sum("payment_count"),
        avg_share=Avg("share_rate"),
    )
    prev_dau: float = float(prev_agg["avg_dau"] or 0)
    prev_completion: float = float(prev_agg["avg_completion"] or 0)
    prev_conversion: float = float(prev_agg["avg_conversion"] or 0)
    prev_revenue: float = float(prev_agg["sum_revenue"] or 0)
    prev_payment: int = int(prev_agg["sum_payment"] or 0)
    prev_share: float = float(prev_agg["avg_share"] or 0)
    prev_order: float = prev_revenue / prev_payment if prev_payment else 0.0
    prev_d7: float = _d7_retention(prev_end)

    # sparkline：区间内每日数值
    daily_map: dict[date, StatsDaily] = {s.date: s for s in stats_qs}
    spark_dau: list[float] = []
    spark_completion: list[float] = []
    spark_conversion: list[float] = []
    spark_order: list[float] = []
    spark_share: list[float] = []
    cur: date = start
    while cur <= end:
        s = daily_map.get(cur)
        if s:
            spark_dau.append(float(s.dau))
            spark_completion.append(float(s.completion_rate))
            spark_conversion.append(float(s.conversion_rate))
            spark_order.append(float(s.revenue) / float(s.payment_count) if s.payment_count else float(s.revenue))
            spark_share.append(float(s.share_rate))
        else:
            spark_dau.append(0.0)
            spark_completion.append(0.0)
            spark_conversion.append(0.0)
            spark_order.append(0.0)
            spark_share.append(0.0)
        cur += timedelta(days=1)
    spark_d7: list[float] = [d7_ret]

    return {
        "dau": _build_kpi_item("DAU", _format_int(avg_dau), avg_dau, prev_dau, "purple", spark_dau),
        "completionRate": _build_kpi_item(
            "完成率", _format_percent(avg_completion), avg_completion, prev_completion, "green", spark_completion
        ),
        "conversionRate": _build_kpi_item(
            "付费转化率", _format_percent(avg_conversion), avg_conversion, prev_conversion, "blue", spark_conversion
        ),
        "avgOrder": _build_kpi_item("客单价", _format_yuan(avg_order), avg_order, prev_order, "gold", spark_order),
        "shareRate": _build_kpi_item("分享率", _format_percent(avg_share), avg_share, prev_share, "teal", spark_share),
        "d7Retention": _build_kpi_item("D7 留存", _format_percent(d7_ret), d7_ret, prev_d7, "red", spark_d7),
    }


def _build_trend() -> dict[str, list[object]]:
    """构建最近 7 天趋势数据。"""
    today: date = timezone.now().date()
    start: date = today - timedelta(days=6)

    stats_map: dict[date, StatsDaily] = {s.date: s for s in StatsDaily.objects.filter(date__gte=start, date__lte=today)}

    # 每日新增设备数（首次出现日期 == 当日）
    first_seen: dict[date, int] = {}
    for fp in (
        TrackingEvent.objects.filter(created_at__date__gte=start, created_at__date__lte=today)
        .values_list("device_fingerprint", flat=True)
        .distinct()
    ):
        first_event = TrackingEvent.objects.filter(device_fingerprint=fp).order_by("created_at").first()
        if first_event is not None:
            first_date: date = first_event.created_at.date()
            if start <= first_date <= today:
                first_seen[first_date] = first_seen.get(first_date, 0) + 1

    labels: list[str] = []
    dau_series: list[int] = []
    new_users_series: list[int] = []
    completions_series: list[int] = []

    cur = start
    while cur <= today:
        labels.append(cur.strftime("%m-%d"))
        s = stats_map.get(cur)
        dau_series.append(int(s.dau) if s else 0)
        new_users_series.append(first_seen.get(cur, 0))
        completions_series.append(int(s.assessment_count) if s else 0)
        cur += timedelta(days=1)

    return {
        "labels": labels,
        "dau": dau_series,
        "newUsers": new_users_series,
        "completions": completions_series,
    }


def _build_bar(range_param: str) -> dict[str, list[object]]:
    """构建支付渠道分布柱状图数据。"""
    start, end, _ = _get_date_range(range_param)
    paid_orders = Order.objects.filter(
        status=Order.OrderStatus.PAID,
        paid_at__date__gte=start,
        paid_at__date__lte=end,
    )
    counts: dict[str, int] = {}
    for order in paid_orders:
        channel: str = order.payment_channel or "unknown"
        counts[channel] = counts.get(channel, 0) + 1

    # 固定展示顺序：微信支付、支付宝
    labels: list[str] = []
    values: list[int] = []
    colors: list[str] = []
    channel_order: list[str] = ["wechat_pay", "alipay"]
    for idx, ch in enumerate(channel_order):
        labels.append(PAYMENT_CHANNEL_LABELS.get(ch, ch))
        values.append(counts.get(ch, 0))
        colors.append(COLOR_GREEN if idx == 0 else COLOR_BLUE)

    return {"labels": labels, "values": values, "colors": colors}


def _build_funnel(range_param: str) -> list[dict[str, object]]:
    """构建 5 步转化漏斗数据。"""
    start, end, _ = _get_date_range(range_param)

    def _count_events(event_type: str) -> int:
        return TrackingEvent.objects.filter(
            event_type=event_type,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()

    visit_count: int = _count_events("page_view")
    start_count: int = _count_events("start_assessment")
    complete_count: int = Assessment.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    ).count()
    view_result_count: int = _count_events("generate_card")
    paid_count: int = Order.objects.filter(
        status=Order.OrderStatus.PAID,
        paid_at__date__gte=start,
        paid_at__date__lte=end,
    ).count()

    steps: list[tuple[str, int]] = [
        ("访问页面", visit_count),
        ("开始测评", start_count),
        ("完成测评", complete_count),
        ("查看结果", view_result_count),
        ("付费", paid_count),
    ]
    return [{"name": name, "value": value, "color": FUNNEL_COLORS[i]} for i, (name, value) in enumerate(steps)]


def _build_alerts() -> list[dict[str, object]]:
    """构建异常告警数据。"""
    alerts: list[dict[str, object]] = []
    now_str: str = timezone.now().strftime("%Y-%m-%d %H:%M")

    # 异常订单：已支付但无交易号
    abnormal_orders = Order.objects.filter(
        status=Order.OrderStatus.PAID,
    ).filter(Q(transaction_id__isnull=True) | Q(transaction_id=""))
    abnormal_count: int = abnormal_orders.count()
    if abnormal_count > 0:
        alerts.append(
            {
                "level": "critical",
                "title": "存在异常订单",
                "desc": f"有 {abnormal_count} 笔已支付订单缺少交易号，请核查支付回调",
                "time": now_str,
            }
        )

    # 过期订单数
    expired_count: int = Order.objects.filter(status=Order.OrderStatus.EXPIRED).count()
    if expired_count > 0:
        alerts.append(
            {
                "level": "warning",
                "title": "过期订单待清理",
                "desc": f"当前有 {expired_count} 笔过期订单，可考虑批量清理",
                "time": now_str,
            }
        )

    # 转化率告警
    today: date = timezone.now().date()
    recent = StatsDaily.objects.filter(date__gte=today - timedelta(days=6), date__lte=today).order_by("-date")
    if recent.exists():
        latest: StatsDaily = recent.first()
        if latest and latest.conversion_rate < 16.0 and latest.conversion_rate > 0:
            alerts.append(
                {
                    "level": "warning",
                    "title": "付费转化率偏低",
                    "desc": f"最近转化率为 {latest.conversion_rate:.1f}%，低于阈值 16%",
                    "time": latest.date.strftime("%Y-%m-%d"),
                }
            )

    return alerts


class DashboardView(APIView):
    """GET /api/admin/dashboard/ — 后台数据看板。

    返回 KPI、趋势、漏斗、告警数据。
    支持 range 参数：yesterday / 7d / 30d。
    """

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> Response:
        """获取看板数据。"""
        range_param: str = request.query_params.get("range", "7d").strip() or "7d"
        if range_param not in ("yesterday", "7d", "30d"):
            range_param = "7d"

        try:
            data: dict[str, object] = {
                "range": range_param,
                "kpi": _build_kpi(range_param),
                "trend": _build_trend(),
                "bar": _build_bar(range_param),
                "funnel": _build_funnel(range_param),
                "alerts": _build_alerts(),
            }
            logger.info("看板数据请求成功 | range=%s", range_param)
            return _success_response(data)
        except Exception as exc:
            logger.exception("看板数据请求失败 | error=%s", str(exc))
            return _error_response(
                "DASHBOARD_ERROR",
                "获取看板数据失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DashboardExportView(APIView):
    """GET /api/admin/dashboard/export/ — 导出看板数据（CSV）。"""

    permission_classes = [AdminPermission]

    def get(self, request: Request) -> HttpResponse:
        """导出看板 CSV。"""
        range_param: str = request.query_params.get("range", "7d").strip() or "7d"
        if range_param not in ("yesterday", "7d", "30d"):
            range_param = "7d"

        try:
            kpi = _build_kpi(range_param)
            trend = _build_trend()
            funnel = _build_funnel(range_param)

            response: HttpResponse = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="dashboard_{range_param}.csv"'
            # UTF-8 BOM，兼容 Excel
            response.write("\ufeff")
            writer = csv.writer(response)

            writer.writerow(["画己职测 数据看板"])
            writer.writerow([f"时间范围: {range_param}"])
            writer.writerow([f"生成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"])
            writer.writerow([])

            # KPI
            writer.writerow(["=== KPI ==="])
            writer.writerow(["指标", "数值", "环比", "趋势"])
            for key in ("dau", "completionRate", "conversionRate", "avgOrder", "shareRate", "d7Retention"):
                item = kpi[key]
                writer.writerow(
                    [
                        item["label"],
                        item["value"],
                        item["change"],
                        ",".join(str(int(v)) for v in item["sparkline"]),
                    ]
                )
            writer.writerow([])

            # 趋势
            writer.writerow(["=== 最近 7 天趋势 ==="])
            writer.writerow(["日期", "DAU", "新增用户", "完成测评数"])
            labels = trend["labels"]
            for i, label in enumerate(labels):
                writer.writerow(
                    [
                        label,
                        trend["dau"][i],
                        trend["newUsers"][i],
                        trend["completions"][i],
                    ]
                )
            writer.writerow([])

            # 漏斗
            writer.writerow(["=== 转化漏斗 ==="])
            writer.writerow(["步骤", "数值"])
            for step in funnel:
                writer.writerow([step["name"], step["value"]])

            logger.info("看板数据导出成功 | range=%s", range_param)
            return response
        except Exception as exc:
            logger.exception("看板数据导出失败 | error=%s", str(exc))
            return _error_response(
                "DASHBOARD_EXPORT_ERROR",
                "导出看板数据失败",
                detail=str(exc),
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
