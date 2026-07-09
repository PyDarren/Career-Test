"""支付安全测试套件。

覆盖 6 道支付安全防线及订单生命周期：
1. 金额服务端硬编码（防篡改）
2. 防重复支付（数据库唯一约束 + 应用层检查）
3. Referer 校验
4. assessment_id 存在性校验
5. 订单号使用 UUID 防篡改
6. 15 分钟自动过期

同时覆盖订单状态查询、报告访问控制、报告找回等端点。

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.8
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, Client
from django.utils import timezone

from apps.assessment.models import Assessment
from apps.mbti_types.models import MBTIType
from apps.payment.models import Order


class PaymentSecurityTest(TestCase):
    """支付安全测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()
        self.assessment = Assessment.objects.create(
            uuid='test-uuid-1234',
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

    def _create_payment(self, assessment_id=None, uuid='test-uuid-1234',
                        method='wechat', referer=None, amount=None):
        """辅助方法：创建支付。"""
        client = Client()
        body = {
            'assessment_id': assessment_id or self.assessment.id,
            'uuid': uuid,
            'method': method,
        }
        if amount:
            body['amount'] = amount
        kwargs = {'content_type': 'application/json', 'data': json.dumps(body)}
        if referer:
            kwargs['HTTP_REFERER'] = referer
        return client.post('/api/payment/create/', **kwargs)

    def _make_paid_order(self, order_no='CT-PAID-001'):
        """创建一条已支付订单。"""
        return Order.objects.create(
            order_no=order_no,
            uuid='test-uuid-1234',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )

    def _make_order(self, order_no, status='pending', amount=Decimal('2.99'),
                    assessment_id=None):
        """创建一条指定状态的订单。"""
        return Order.objects.create(
            order_no=order_no,
            uuid='test-uuid-1234',
            assessment_id=assessment_id or self.assessment.id,
            amount=amount,
            status=status,
            expires_at=(
                timezone.now() + timedelta(minutes=15)
                if status == 'pending' else timezone.now()
            ),
            paid_at=timezone.now() if status == 'paid' else None,
        )

    def _wechat_notify(self, body):
        """模拟微信支付回调。"""
        return self.client.post(
            '/payment/wechat/notify/',
            data=body if isinstance(body, str) else json.dumps(body),
            content_type='application/json',
        )

    def _alipay_notify(self, order_no):
        """模拟支付宝支付回调（form 表单）。"""
        return self.client.post(
            '/payment/alipay/notify/',
            data={'out_trade_no': order_no, 'trade_no': 'ali_tx'},
        )

    # ------------------------------------------------------------------
    # 创建支付订单（6 道防线）
    # ------------------------------------------------------------------

    def test_create_payment_normal(self):
        """正常创建订单 → 200，返回 order_no 和 pay_info。"""
        response = self._create_payment()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('order_no', data)
        self.assertIn('pay_info', data)
        self.assertTrue(data['order_no'])
        # 订单已写入数据库
        self.assertTrue(Order.objects.filter(order_no=data['order_no']).exists())

    def test_amount_cannot_be_tampered(self):
        """前端传入 amount='0.01'，但订单 amount 仍为 2.99。"""
        response = self._create_payment(amount='0.01')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # 返回的金额仍为服务端硬编码值
        self.assertEqual(data['amount'], '2.99')
        # 数据库中订单金额未被篡改
        order = Order.objects.get(order_no=data['order_no'])
        self.assertEqual(order.amount, Decimal('2.99'))

    def test_duplicate_payment_prevented(self):
        """同一 assessment 已有 paid 订单 → 400。"""
        self._make_paid_order(order_no='CT-PAID-DUP-001')
        response = self._create_payment()
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_invalid_referer_rejected(self):
        """非本站 Referer → 403。"""
        response = self._create_payment(referer='http://evil.com/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())

    def test_invalid_payment_method(self):
        """不支持的支付方式 → 400。"""
        response = self._create_payment(method='bitcoin')
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_missing_params(self):
        """缺少 assessment_id 或 uuid → 400。"""
        # 缺少 assessment_id
        body = {'uuid': 'test-uuid-1234', 'method': 'wechat'}
        response = self.client.post(
            '/api/payment/create/',
            data=json.dumps(body),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

        # 缺少 uuid
        body = {'assessment_id': self.assessment.id, 'method': 'wechat'}
        response = self.client.post(
            '/api/payment/create/',
            data=json.dumps(body),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_assessment(self):
        """assessment 不存在 → 404。"""
        response = self._create_payment(
            assessment_id=999999, uuid='not-exist-uuid'
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())

    def test_order_expires_after_15min(self):
        """创建订单后检查 expires_at 为创建后 15 分钟。"""
        response = self._create_payment()
        data = response.json()
        order = Order.objects.get(order_no=data['order_no'])
        delta = order.expires_at - order.created_at
        # 15 分钟 = 900 秒，允许 60 秒误差（auto_now_add 与 expires_at 计算的时间差）
        self.assertLess(abs(delta.total_seconds() - 900), 60)

    # ------------------------------------------------------------------
    # 订单状态查询
    # ------------------------------------------------------------------

    def test_order_status_view(self):
        """查询订单状态 → 200。"""
        response = self._create_payment()
        order_no = response.json()['order_no']
        status_response = self.client.get(f'/api/order/status/{order_no}/')
        self.assertEqual(status_response.status_code, 200)
        data = status_response.json()
        self.assertEqual(data['order_no'], order_no)
        self.assertEqual(data['status'], 'pending')

    def test_order_status_not_found(self):
        """查询不存在的订单 → 404。"""
        response = self.client.get('/api/order/status/NONEXISTENT-ORDER/')
        self.assertEqual(response.status_code, 404)

    def test_order_auto_expire(self):
        """pending 订单过期后查询 → status='expired'。"""
        order = Order.objects.create(
            order_no='CT-EXPIRE-001',
            uuid='test-uuid-1234',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='pending',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(f'/api/order/status/{order.order_no}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'expired')
        # 数据库状态已更新
        order.refresh_from_db()
        self.assertEqual(order.status, 'expired')

    # ------------------------------------------------------------------
    # 报告访问控制
    # ------------------------------------------------------------------

    def test_report_view_requires_paid_order(self):
        """未支付订单访问报告 → 404。"""
        order = Order.objects.create(
            order_no='CT-PENDING-REPORT-001',
            uuid='test-uuid-1234',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = self.client.get(f'/report/{order.order_no}/')
        self.assertEqual(response.status_code, 404)

    def test_report_view_paid_order(self):
        """已支付订单访问报告 → 200。"""
        order = self._make_paid_order(order_no='CT-PAID-REPORT-001')
        response = self.client.get(f'/report/{order.order_no}/')
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # 报告找回
    # ------------------------------------------------------------------

    def test_report_recover_no_orders(self):
        """无已支付订单 → 404。"""
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({'uuid': 'no-orders-uuid'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_report_recover_with_orders(self):
        """有已支付订单 → 200，返回报告列表。"""
        self._make_paid_order(order_no='CT-RECOVER-001')
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({'uuid': 'test-uuid-1234'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        report = data['reports'][0]
        self.assertEqual(report['mbti_type'], 'INTJ')
        self.assertEqual(report['order_no'], 'CT-RECOVER-001')
        self.assertIn('report_url', report)

    # ------------------------------------------------------------------
    # 创建支付订单异常分支
    # ------------------------------------------------------------------

    def test_create_payment_invalid_body(self):
        """请求体非法 JSON → 400。"""
        response = self.client.post(
            '/api/payment/create/',
            data='not-valid-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_create_payment_alipay(self):
        """支付宝下单 → 200，pay_info 含 pay_url。"""
        response = self._create_payment(method='alipay')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['method'], 'alipay')
        self.assertIn('pay_url', data['pay_info'])

    def test_pending_order_reused(self):
        """存在未过期的 pending 订单时复用，不重复创建。"""
        Order.objects.create(
            order_no='CT-PENDING-REUSE',
            uuid='test-uuid-1234',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='pending',
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self._create_payment()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['order_no'], 'CT-PENDING-REUSE')
        # 未重复创建 pending 订单
        self.assertEqual(
            Order.objects.filter(
                assessment_id=self.assessment.id, status='pending'
            ).count(),
            1,
        )

    def test_expired_pending_order_replaced(self):
        """过期的 pending 订单被标记 expired，并创建新订单。"""
        expired = Order.objects.create(
            order_no='CT-PENDING-EXPIRED',
            uuid='test-uuid-1234',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='pending',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self._create_payment()
        self.assertEqual(response.status_code, 200)
        new_order_no = response.json()['order_no']
        self.assertNotEqual(new_order_no, 'CT-PENDING-EXPIRED')
        expired.refresh_from_db()
        self.assertEqual(expired.status, 'expired')

    # ------------------------------------------------------------------
    # 微信支付回调
    # ------------------------------------------------------------------

    def test_wechat_notify_success(self):
        """微信回调成功 → 订单标记已支付。"""
        order = self._make_order('CT-WX-OK')
        body = {'resource': {
            'out_trade_no': 'CT-WX-OK', 'transaction_id': 'wx_tx_001',
        }}
        response = self._wechat_notify(body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 'SUCCESS')
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_method, 'wechat')
        self.assertEqual(order.payment_id, 'wx_tx_001')

    def test_wechat_notify_invalid(self):
        """微信回调验签失败（非法 JSON）→ 400。"""
        response = self._wechat_notify('not-valid-json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'FAIL')

    def test_wechat_notify_idempotent(self):
        """微信回调幂等：已支付订单再次回调 → SUCCESS。"""
        self._make_order('CT-WX-IDEM', status='paid')
        body = {'resource': {
            'out_trade_no': 'CT-WX-IDEM', 'transaction_id': 'wx_tx_002',
        }}
        response = self._wechat_notify(body)
        self.assertEqual(response.status_code, 200)

    def test_wechat_notify_order_not_found(self):
        """微信回调订单不存在 → 404。"""
        body = {'resource': {
            'out_trade_no': 'CT-NOT-EXIST', 'transaction_id': 'wx_tx',
        }}
        response = self._wechat_notify(body)
        self.assertEqual(response.status_code, 404)

    def test_wechat_notify_amount_mismatch(self):
        """微信回调金额不一致 → 400。"""
        self._make_order('CT-WX-AMT', amount=Decimal('1.00'))
        body = {'resource': {
            'out_trade_no': 'CT-WX-AMT', 'transaction_id': 'wx_tx',
        }}
        response = self._wechat_notify(body)
        self.assertEqual(response.status_code, 400)

    def test_wechat_notify_status_invalid(self):
        """微信回调订单状态异常 → 400。"""
        self._make_order('CT-WX-STATUS', status='failed')
        body = {'resource': {
            'out_trade_no': 'CT-WX-STATUS', 'transaction_id': 'wx_tx',
        }}
        response = self._wechat_notify(body)
        self.assertEqual(response.status_code, 400)

    # ------------------------------------------------------------------
    # 支付宝支付回调
    # ------------------------------------------------------------------

    def test_alipay_notify_success(self):
        """支付宝回调成功 → 订单标记已支付。"""
        order = self._make_order('CT-ALI-OK')
        response = self._alipay_notify('CT-ALI-OK')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['code'], 'success')
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_method, 'alipay')

    def test_alipay_notify_idempotent(self):
        """支付宝回调幂等：已支付订单再次回调 → 200。"""
        self._make_order('CT-ALI-IDEM', status='paid')
        response = self._alipay_notify('CT-ALI-IDEM')
        self.assertEqual(response.status_code, 200)

    def test_alipay_notify_amount_mismatch(self):
        """支付宝回调金额不一致 → 400。"""
        self._make_order('CT-ALI-AMT', amount=Decimal('1.00'))
        response = self._alipay_notify('CT-ALI-AMT')
        self.assertEqual(response.status_code, 400)

    def test_alipay_notify_status_invalid(self):
        """支付宝回调订单状态异常 → 400。"""
        self._make_order('CT-ALI-STATUS', status='failed')
        response = self._alipay_notify('CT-ALI-STATUS')
        self.assertEqual(response.status_code, 400)

    def test_alipay_notify_order_not_found(self):
        """支付宝回调订单不存在 → 404。"""
        response = self._alipay_notify('CT-ALI-NOT-EXIST')
        self.assertEqual(response.status_code, 404)

    def test_alipay_notify_json_body(self):
        """支付宝回调以 JSON 请求体提交 → 200。"""
        order = self._make_order('CT-ALI-JSON')
        response = self.client.post(
            '/payment/alipay/notify/',
            data=json.dumps({'out_trade_no': 'CT-ALI-JSON', 'trade_no': 'ali_json'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')

    # ------------------------------------------------------------------
    # 报告找回异常分支
    # ------------------------------------------------------------------

    def test_report_recover_invalid_body(self):
        """报告找回请求体非法 JSON → 400。"""
        response = self.client.post(
            '/api/report/recover/',
            data='not-valid-json',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_report_recover_missing_uuid(self):
        """报告找回缺少 uuid → 400。"""
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_report_recover_assessment_not_found(self):
        """报告找回订单对应测评不存在 → 跳过该订单，返回空报告列表。"""
        Order.objects.create(
            order_no='CT-RECOVER-ORPHAN',
            uuid='orphan-uuid',
            assessment_id=999999,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({'uuid': 'orphan-uuid'}),
            content_type='application/json',
        )
        # 存在已支付订单但测评记录丢失 → 跳过，返回空列表
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reports'], [])

    # ------------------------------------------------------------------
    # 订单模型方法
    # ------------------------------------------------------------------

    def test_order_mark_as_paid(self):
        """mark_as_paid 正常流程。"""
        order = self._make_order('CT-MODEL-PAID')
        order.mark_as_paid('pay_001', 'wechat')
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.payment_id, 'pay_001')
        self.assertEqual(order.payment_method, 'wechat')
        self.assertIsNotNone(order.paid_at)

    def test_order_mark_as_paid_invalid_status(self):
        """非 pending 状态调用 mark_as_paid → ValueError。"""
        order = self._make_order('CT-MODEL-FAIL', status='failed')
        with self.assertRaises(ValueError):
            order.mark_as_paid('pay_002', 'wechat')

    def test_order_mark_as_expired(self):
        """mark_as_expired 正常流程。"""
        order = self._make_order('CT-MODEL-EXP')
        order.mark_as_expired()
        self.assertEqual(order.status, 'expired')

    def test_order_mark_as_expired_non_pending(self):
        """非 pending 状态调用 mark_as_expired → 无操作。"""
        order = self._make_order('CT-MODEL-PAID2', status='paid')
        order.mark_as_expired()
        self.assertEqual(order.status, 'paid')

    def test_order_is_expired_is_paid_properties(self):
        """is_expired / is_paid 属性及 __str__。"""
        active = self._make_order('CT-PROP-ACTIVE')
        self.assertFalse(active.is_expired)
        self.assertFalse(active.is_paid)

        expired_pending = Order.objects.create(
            order_no='CT-PROP-EXP', uuid='test-uuid-1234',
            assessment_id=self.assessment.id, amount=Decimal('2.99'),
            status='pending', expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertTrue(expired_pending.is_expired)
        self.assertFalse(expired_pending.is_paid)

        paid = self._make_order('CT-PROP-PAID', status='paid')
        self.assertTrue(paid.is_paid)
        self.assertFalse(paid.is_expired)

        # __str__ 返回 "订单号 (状态)"
        self.assertIn('CT-PROP-PAID', str(paid))
        self.assertIn('paid', str(paid))
