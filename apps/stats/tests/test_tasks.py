"""Celery 定时任务测试。

直接调用任务函数（不走 celery worker），覆盖 4 个定时任务：
1. expire_pending_orders —— 过期 pending 订单
2. cleanup_old_assessments —— 清理 30 天前记录
3. generate_daily_stats —— 生成前日统计
4. refresh_completed_count —— 刷新已完成人数缓存

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.assessment.models import Assessment
from apps.payment.models import Order
from apps.stats.models import StatsDaily, TrackingEvent
from apps.stats.tasks import (
    cleanup_old_assessments,
    expire_pending_orders,
    generate_daily_stats,
    refresh_completed_count,
)


class ExpirePendingOrdersTest(TestCase):
    """expire_pending_orders 任务测试套件。"""

    def setUp(self):
        cache.clear()
        self.assessment = Assessment.objects.create(
            uuid='task-expire-uuid',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )

    def _make_pending_order(self, order_no, expired=False):
        """创建一条 pending 订单。"""
        delta = timedelta(minutes=1) if expired else timedelta(minutes=15)
        return Order.objects.create(
            order_no=order_no,
            uuid='task-expire-uuid',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='pending',
            expires_at=timezone.now() - delta if expired else timezone.now() + delta,
        )

    def test_expire_pending_orders(self):
        """创建过期 pending 订单 -> 调用后 status='expired'。"""
        order = self._make_pending_order('CT-TASK-EXP-001', expired=True)
        self.assertEqual(order.status, 'pending')

        result = expire_pending_orders()
        self.assertEqual(result, 1)
        order.refresh_from_db()
        self.assertEqual(order.status, 'expired')

    def test_expire_pending_orders_no_pending(self):
        """无 pending 订单 -> 返回 0。"""
        result = expire_pending_orders()
        self.assertEqual(result, 0)

    def test_expire_pending_orders_skips_active(self):
        """未过期的 pending 订单不被过期。"""
        order = self._make_pending_order('CT-TASK-EXP-002', expired=False)
        result = expire_pending_orders()
        self.assertEqual(result, 0)
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending')


class CleanupOldAssessmentsTest(TestCase):
    """cleanup_old_assessments 任务测试套件。"""

    def setUp(self):
        cache.clear()

    def test_cleanup_old_assessments(self):
        """30 天前记录被清理。"""
        old = Assessment.objects.create(
            uuid='cleanup-old-uuid',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )
        # 手动将 created_at 设为 31 天前
        Assessment.objects.filter(id=old.id).update(
            created_at=timezone.now() - timedelta(days=31)
        )

        result = cleanup_old_assessments()
        self.assertEqual(result, 1)
        self.assertFalse(Assessment.objects.filter(id=old.id).exists())

    def test_cleanup_keeps_recent(self):
        """30 天内记录不被清理。"""
        recent = Assessment.objects.create(
            uuid='cleanup-recent-uuid',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )
        result = cleanup_old_assessments()
        self.assertEqual(result, 0)
        self.assertTrue(Assessment.objects.filter(id=recent.id).exists())

    def test_cleanup_keeps_paid_orders(self):
        """有 paid 订单的旧记录不被清理。"""
        assessment = Assessment.objects.create(
            uuid='cleanup-paid-uuid',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )
        Assessment.objects.filter(id=assessment.id).update(
            created_at=timezone.now() - timedelta(days=31)
        )
        Order.objects.create(
            order_no='CT-CLEANUP-PAID-001',
            uuid='cleanup-paid-uuid',
            assessment_id=assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )

        result = cleanup_old_assessments()
        self.assertEqual(result, 0)
        self.assertTrue(Assessment.objects.filter(id=assessment.id).exists())


class RefreshCompletedCountTest(TestCase):
    """refresh_completed_count 任务测试套件。"""

    def setUp(self):
        cache.clear()

    def test_refresh_completed_count(self):
        """调用后 Redis 缓存更新为 Assessment 记录数。"""
        Assessment.objects.create(
            uuid='refresh-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )
        Assessment.objects.create(
            uuid='refresh-uuid-002',
            mbti_type_code='ENTP',
            dimension_scores={'EI': {'label': 'E'}},
            facet_scores=[],
            consistency_flag='normal',
        )

        result = refresh_completed_count()
        self.assertEqual(result, 2)
        cached = cache.get('stats:completed_count')
        self.assertEqual(cached, 2)

    def test_refresh_completed_count_empty(self):
        """无记录时缓存为 0。"""
        result = refresh_completed_count()
        self.assertEqual(result, 0)
        cached = cache.get('stats:completed_count')
        self.assertEqual(cached, 0)


class GenerateDailyStatsTest(TestCase):
    """generate_daily_stats 任务测试套件。"""

    def setUp(self):
        cache.clear()

    def test_generate_daily_stats(self):
        """生成前日统计记录。"""
        yesterday = (timezone.now() - timedelta(days=1)).date()
        day_start = timezone.make_aware(
            timezone.datetime.combine(yesterday, timezone.datetime.min.time())
        )

        # 创建昨日的埋点事件
        TrackingEvent.objects.create(
            uuid='stats-uuid-001',
            event_name='page_view',
            event_data={'page': '/'},
        )
        # 手动设置 created_at 为昨天
        TrackingEvent.objects.filter().update(created_at=day_start + timedelta(hours=2))

        result = generate_daily_stats()
        self.assertEqual(result, 1)
        stats = StatsDaily.objects.get(date=yesterday)
        self.assertEqual(stats.pv, 1)
        self.assertEqual(stats.uv, 1)

    def test_generate_daily_stats_idempotent(self):
        """重复调用不报错（update_or_create 幂等）。"""
        yesterday = (timezone.now() - timedelta(days=1)).date()
        # 首次生成
        result1 = generate_daily_stats()
        self.assertEqual(result1, 1)

        # 再次调用不报错
        result2 = generate_daily_stats()
        self.assertEqual(result2, 0)

        # 仍只有一条记录
        self.assertEqual(StatsDaily.objects.filter(date=yesterday).count(), 1)

    def test_generate_daily_stats_with_revenue(self):
        """有付费订单时统计收入。"""
        yesterday = (timezone.now() - timedelta(days=1)).date()
        day_start = timezone.make_aware(
            timezone.datetime.combine(yesterday, timezone.datetime.min.time())
        )

        assessment = Assessment.objects.create(
            uuid='stats-rev-uuid',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )
        Order.objects.create(
            order_no='CT-STATS-REV-001',
            uuid='stats-rev-uuid',
            assessment_id=assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=day_start + timedelta(hours=3),
        )

        result = generate_daily_stats()
        self.assertEqual(result, 1)
        stats = StatsDaily.objects.get(date=yesterday)
        self.assertEqual(stats.revenue, Decimal('2.99'))
        self.assertEqual(stats.payment_successes, 0)
