"""支付沙箱全链路测试。

测试支付全链路（使用开发环境 mock）：
- 微信/支付宝下单
- 回调通知
- 防重复支付
- 订单状态查询
- 订单过期
- 金额防篡改
- 报告访问控制
- 报告找回

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.8
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.assessment.models import Assessment
from apps.payment.models import Order


class PaymentSandboxTest(TestCase):
    """支付沙箱全链路测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    PAYMENT_REFERER = 'http://127.0.0.1:8000/result/'

    def setUp(self):
        cache.clear()
        self.assessment = Assessment.objects.create(
            uuid='sandbox-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={
                'EI': {'percentage': 33, 'label': 'I', 'score_a': 12, 'score_b': 24, 'strength': 'moderate'},
                'SN': {'percentage': 25, 'label': 'N', 'score_a': 9, 'score_b': 27, 'strength': 'distinct'},
                'TF': {'percentage': 75, 'label': 'T', 'score_a': 27, 'score_b': 9, 'strength': 'distinct'},
                'JP': {'percentage': 70, 'label': 'J', 'score_a': 25, 'score_b': 11, 'strength': 'distinct'},
            },
            facet_scores=[],
            consistency_flag='normal',
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _create_payment(self, assessment_id=None, uuid='sandbox-uuid-001',
                        method='wechat', amount=None, **extra):
        """创建支付订单。"""
        body = {
            'assessment_id': assessment_id or self.assessment.id,
            'uuid': uuid,
            'method': method,
        }
        if amount is not None:
            body['amount'] = amount
        kwargs = {
            'content_type': 'application/json',
            'data': json.dumps(body),
            'HTTP_REFERER': self.PAYMENT_REFERER,
        }
        kwargs.update(extra)
        return self.client.post('/api/payment/create/', **kwargs)

    def _make_order(self, order_no, status='pending', amount=Decimal('2.99'),
                    assessment_id=None):
        """创建指定状态的订单。"""
        return Order.objects.create(
            order_no=order_no,
            uuid='sandbox-uuid-001',
            assessment_id=assessment_id or self.assessment.id,
            amount=amount,
            status=status,
            expires_at=(
                timezone.now() + timedelta(minutes=15)
                if status == 'pending' else timezone.now()
            ),
            paid_at=timezone.now() if status == 'paid' else None,
        )

    def _wechat_notify(self, order_no):
        """模拟微信支付回调。"""
        body = {
            'resource': {
                'out_trade_no': order_no,
                'transaction_id': f'wx_tx_{order_no[-8:]}',
            }
        }
        return self.client.post(
            '/payment/wechat/notify/',
            data=json.dumps(body),
            content_type='application/json',
        )

    def _alipay_notify(self, order_no, use_json=False):
        """模拟支付宝支付回调。"""
        if use_json:
            return self.client.post(
                '/payment/alipay/notify/',
                data=json.dumps({'out_trade_no': order_no, 'trade_no': 'ali_tx'}),
                content_type='application/json',
            )
        return self.client.post(
            '/payment/alipay/notify/',
            data={'out_trade_no': order_no, 'trade_no': 'ali_tx'},
        )

    # ------------------------------------------------------------------
    # 下单
    # ------------------------------------------------------------------

    def test_wechat_create_order(self):
        """微信下单 → 200 含 pay_info.code_url。"""
        response = self._create_payment(method='wechat')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('order_no', data)
        self.assertIn('pay_info', data)
        self.assertIn('code_url', data['pay_info'])
        self.assertEqual(data['method'], 'wechat')

    def test_alipay_create_order(self):
        """支付宝下单 → 200 含 pay_info.pay_url。"""
        response = self._create_payment(method='alipay')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('order_no', data)
        self.assertIn('pay_info', data)
        self.assertIn('pay_url', data['pay_info'])
        self.assertEqual(data['method'], 'alipay')

    # ------------------------------------------------------------------
    # 回调通知
    # ------------------------------------------------------------------

    def test_wechat_notify_success(self):
        """微信回调 → 订单变为 paid。"""
        order = self._make_order('CT-SB-WX-001')
        response = self._wechat_notify(order.order_no)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 'SUCCESS')
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_method, 'wechat')

    def test_alipay_notify_success(self):
        """支付宝回调 → 订单变为 paid。"""
        order = self._make_order('CT-SB-ALI-001')
        response = self._alipay_notify(order.order_no)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 'success')
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_method, 'alipay')

    # ------------------------------------------------------------------
    # 防重复支付
    # ------------------------------------------------------------------

    def test_duplicate_payment_prevention(self):
        """同一 assessment 已有 paid → 400。"""
        self._make_order('CT-SB-DUP-001', status='paid')
        response = self._create_payment()
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    # ------------------------------------------------------------------
    # 订单状态查询
    # ------------------------------------------------------------------

    def test_order_status_pending(self):
        """创建订单后 status=paid 前查询 → status=pending。"""
        response = self._create_payment()
        order_no = response.json()['order_no']
        status_response = self.client.get(f'/api/order/status/{order_no}/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()['status'], 'pending')

    def test_order_status_paid(self):
        """支付后查询 → status=paid。"""
        order = self._make_order('CT-SB-PAID-001')
        self._wechat_notify(order.order_no)
        status_response = self.client.get(f'/api/order/status/{order.order_no}/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()['status'], 'paid')

    # ------------------------------------------------------------------
    # 订单过期
    # ------------------------------------------------------------------

    def test_order_expiry(self):
        """创建过期订单 → 调用 Order.mark_as_expired() → status=expired。"""
        order = self._make_order('CT-SB-EXP-001')
        # 模拟过期：设置 expires_at 为过去时间
        order.expires_at = timezone.now() - timedelta(minutes=1)
        order.save()
        # 调用 mark_as_expired
        order.mark_as_expired()
        self.assertEqual(order.status, 'expired')

    # ------------------------------------------------------------------
    # 金额防篡改
    # ------------------------------------------------------------------

    def test_amount_tamper_proof(self):
        """前端传 amount=0.01 → 服务端仍创建 2.99 订单。"""
        response = self._create_payment(amount='0.01')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['amount'], '2.99')
        order = Order.objects.get(order_no=data['order_no'])
        self.assertEqual(order.amount, Decimal('2.99'))

    # ------------------------------------------------------------------
    # 报告访问控制
    # ------------------------------------------------------------------

    def test_report_access_unpaid(self):
        """未支付访问 /report/{order_no}/ → 404。"""
        order = self._make_order('CT-SB-UNPAID-001')
        response = self.client.get(f'/report/{order.order_no}/')
        self.assertEqual(response.status_code, 404)

    def test_report_access_paid(self):
        """已支付访问 /report/{order_no}/ → 200 含报告内容。"""
        order = self._make_order('CT-SB-REPORT-001', status='paid')
        response = self.client.get(f'/report/{order.order_no}/')
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # 报告找回
    # ------------------------------------------------------------------

    def test_report_recover(self):
        """POST /api/report/recover/ → 返回已购买报告列表。"""
        self._make_order('CT-SB-RECOVER-001', status='paid')
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({'uuid': 'sandbox-uuid-001'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        report = data['reports'][0]
        self.assertEqual(report['mbti_type'], 'INTJ')
        self.assertIn('report_url', report)
