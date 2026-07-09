"""对账任务测试。

覆盖 apps/payment/tasks.py 中的 daily_reconciliation 任务：
1. 开发环境（无支付配置）-> 返回 summary，missing=0, extra=0
2. 有本地 paid 订单但平台无记录 -> extra_orders > 0

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.assessment.models import Assessment
from apps.payment.models import Order
from apps.payment.tasks import daily_reconciliation


class DailyReconciliationTest(TestCase):
    """daily_reconciliation 任务测试套件。"""

    def setUp(self):
        cache.clear()
        self.assessment = Assessment.objects.create(
            uuid='recon-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )

    def _make_paid_order_yesterday(self, order_no):
        """创建一条昨日已支付订单。"""
        yesterday = (timezone.now() - timedelta(days=1)).date()
        day_start = timezone.make_aware(
            timezone.datetime.combine(yesterday, timezone.datetime.min.time())
        )
        return Order.objects.create(
            order_no=order_no,
            uuid='recon-uuid-001',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=day_start + timedelta(hours=2),
        )

    def test_reconciliation_no_transactions(self):
        """开发环境（无支付配置）-> 返回 summary，missing=0, extra=0。"""
        result = daily_reconciliation()
        self.assertIsInstance(result, dict)
        self.assertIn('date', result)
        self.assertIn('local_paid_count', result)
        self.assertIn('platform_transaction_count', result)
        self.assertIn('missing_orders', result)
        self.assertIn('extra_orders', result)
        self.assertEqual(result['missing_orders'], 0)
        self.assertEqual(result['extra_orders'], 0)
        self.assertEqual(result['platform_transaction_count'], 0)
        self.assertEqual(result['local_paid_count'], 0)

    def test_reconciliation_with_local_orders(self):
        """有本地 paid 订单但平台无记录 -> extra_orders > 0。"""
        self._make_paid_order_yesterday('CT-RECON-001')

        result = daily_reconciliation()
        self.assertEqual(result['local_paid_count'], 1)
        self.assertEqual(result['platform_transaction_count'], 0)
        self.assertEqual(result['missing_orders'], 0)
        self.assertEqual(result['extra_orders'], 1)

    def test_reconciliation_summary_date(self):
        """summary 中 date 字段为昨日日期。"""
        yesterday = (timezone.now() - timedelta(days=1)).date()
        result = daily_reconciliation()
        self.assertEqual(result['date'], yesterday.isoformat())

    def test_reconciliation_no_local_orders(self):
        """无本地 paid 订单 -> local_paid_count=0。"""
        result = daily_reconciliation()
        self.assertEqual(result['local_paid_count'], 0)
        self.assertEqual(result['extra_orders'], 0)
