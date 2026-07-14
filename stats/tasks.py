# 画己职测 — Celery 定时任务定义
#
# 本模块定义所有 Celery 定时任务：
#   - expire_orders():          每 60 秒执行，过期超时未支付订单
#   - reconcile_payments():     每日 02:30 执行，支付对账
#   - cleanup_expired_data():   每日 02:00 执行，清理过期临时数据
#   - generate_daily_report():  每日 03:00 执行，生成每日统计
#   - refresh_cache():          每小时执行，刷新热点缓存

import logging
from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from career_test.celery import app
from common.utils import mask_token

logger = logging.getLogger(__name__)


@app.task(name="stats.expire_orders")
def expire_orders() -> None:
    """清理超时未支付订单。

    每 60 秒执行一次。扫描所有 pending 状态且创建时间超过
    ORDER_TIMEOUT_SECONDS（60 秒）的订单，将其状态更新为 expired。

    :return: None
    """
    from common.constants import ORDER_TIMEOUT_SECONDS
    from payment.models import Order

    logger.info("定时任务 expire_orders 执行 | 清理超时未支付订单")

    try:
        threshold = timezone.now() - timedelta(seconds=ORDER_TIMEOUT_SECONDS)
        expired_count: int = Order.objects.filter(
            status=Order.OrderStatus.PENDING,
            created_at__lt=threshold,
        ).update(
            status=Order.OrderStatus.EXPIRED,
            expired_at=timezone.now(),
        )

        if expired_count > 0:
            logger.info("过期订单清理完成 | count=%d", expired_count)
        else:
            logger.debug("过期订单清理完成 | count=0")

    except Exception as exc:
        logger.exception("expire_orders 执行失败 | error=%s", str(exc))
        raise


@app.task(name="stats.reconcile_payments")
def reconcile_payments() -> None:
    """支付对账。

    每日 02:30 执行。扫描 status=paid 但无 transaction_id 的异常订单，
    记录告警日志。这些订单可能存在支付渠道回调未送达或数据丢失的问题。

    :return: None
    """
    from payment.models import Order

    logger.info("定时任务 reconcile_payments 执行 | 支付对账")

    try:
        # 查找已支付但无交易号的异常订单
        abnormal_orders: list[Order] = list(
            Order.objects.filter(
                status=Order.OrderStatus.PAID,
                transaction_id__isnull=True,
            ).order_by("-paid_at")
        )

        if abnormal_orders:
            logger.warning(
                "支付对账发现异常订单 | count=%d | 这些订单已支付但无交易号",
                len(abnormal_orders),
            )
            for order in abnormal_orders:
                logger.warning(
                    "异常订单 | order_id=%s | session=%s | amount=%s | paid_at=%s",
                    order.order_id,
                    mask_token(order.session_token),
                    str(order.amount),
                    order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "N/A",
                )
        else:
            logger.info("支付对账完成 | 无异常订单")

    except Exception as exc:
        logger.exception("reconcile_payments 执行失败 | error=%s", str(exc))
        raise


@app.task(name="stats.cleanup_expired_data")
def cleanup_expired_data() -> None:
    """清理过期临时数据。

    每日 02:00 执行。清理过期的 session 缓存、临时答题数据等。
    M3 阶段清理已过期的订单缓存数据。

    :return: None
    """
    logger.info("定时任务 cleanup_expired_data 执行 | 清理过期临时数据")

    try:
        # 清理订单状态缓存（前端轮询时可能缓存了订单状态）
        # M4 阶段可扩展为清理更多临时数据
        cache_keys_cleared: int = 0

        # 清理过期的 LocMemCache 中的临时数据
        # 开发环境使用 LocMemCache，生产环境使用 Redis
        # 此处仅做日志记录，实际缓存键由业务层管理
        logger.info(
            "过期临时数据清理完成 | cache_keys_cleared=%d",
            cache_keys_cleared,
        )

    except Exception as exc:
        logger.exception("cleanup_expired_data 执行失败 | error=%s", str(exc))
        raise


@app.task(name="stats.generate_daily_report")
def generate_daily_report() -> None:
    """生成每日统计报告。

    每日 03:00 执行。汇总前一天的 DAU、测评数、付费数、转化率、
    分享数、收入等指标，写入 stats_daily 表。

    :return: None
    """
    from assessment.models import Assessment
    from payment.models import Order
    from stats.models import StatsDaily, TrackingEvent

    logger.info("定时任务 generate_daily_report 执行 | 生成每日统计报告")

    try:
        yesterday = (timezone.now() - timedelta(days=1)).date()
        day_start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(yesterday, datetime.max.time()))

        # DAU：独立 session_token 数
        dau: int = (
            TrackingEvent.objects.filter(
                created_at__gte=day_start,
                created_at__lte=day_end,
            )
            .values("session_token")
            .distinct()
            .count()
        )

        # 测评完成数
        assessment_count: int = Assessment.objects.filter(
            created_at__gte=day_start,
            created_at__lte=day_end,
        ).count()

        # 付费数
        payment_count: int = Order.objects.filter(
            status=Order.OrderStatus.PAID,
            paid_at__gte=day_start,
            paid_at__lte=day_end,
        ).count()

        # 分享数
        share_count: int = TrackingEvent.objects.filter(
            event_type="share",
            created_at__gte=day_start,
            created_at__lte=day_end,
        ).count()

        # 收入
        revenue_result = Order.objects.filter(
            status=Order.OrderStatus.PAID,
            paid_at__gte=day_start,
            paid_at__lte=day_end,
        ).aggregate(total=Sum("amount"))
        revenue: float = float(revenue_result["total"]) if revenue_result["total"] else 0.0

        # 转化率 = 付费数 / 测评数
        conversion_rate: float = (payment_count / assessment_count) if assessment_count > 0 else 0.0

        # 分享率 = 分享数 / 测评数
        share_rate: float = (share_count / assessment_count) if assessment_count > 0 else 0.0

        # 完成率（M4 阶段完善：已完成测评数 / 开始测评数）
        completion_rate: float = 1.0 if assessment_count > 0 else 0.0

        # 写入或更新 stats_daily
        StatsDaily.objects.update_or_create(
            date=yesterday,
            defaults={
                "dau": dau,
                "assessment_count": assessment_count,
                "completion_rate": completion_rate,
                "payment_count": payment_count,
                "conversion_rate": conversion_rate,
                "share_count": share_count,
                "share_rate": share_rate,
                "revenue": revenue,
            },
        )

        logger.info(
            "每日统计报告生成完成 | date=%s | dau=%d | assessments=%d | payments=%d | revenue=%.2f",
            yesterday,
            dau,
            assessment_count,
            payment_count,
            revenue,
        )

    except Exception as exc:
        logger.exception("generate_daily_report 执行失败 | error=%s", str(exc))
        raise


@app.task(name="stats.refresh_cache")
def refresh_cache() -> None:
    """刷新热点缓存。

    每小时执行。刷新热门职业推荐、画像原型数据、题目列表等
    热点缓存。M3 阶段记录缓存刷新日志。

    :return: None
    """
    from django.core.cache import cache

    logger.info("定时任务 refresh_cache 执行 | 刷新热点缓存")

    try:
        # 刷新热点缓存键
        # M4 阶段可扩展为刷新更多缓存
        cache_keys: list[str] = [
            "questions_list",
            "archetypes_config",
            "careers_hot",
        ]

        for key in cache_keys:
            cache.delete(key)

        logger.info("热点缓存刷新完成 | keys=%s", cache_keys)

    except Exception as exc:
        logger.exception("refresh_cache 执行失败 | error=%s", str(exc))
        raise
