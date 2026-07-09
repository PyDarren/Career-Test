"""AlipayPay 扩展测试。

补充覆盖 apps/payment/alipay_pay.py 中尚未覆盖的方法：
1. create_order 开发环境
2. verify_notify 开发环境
3. query_daily_transactions 开发环境
4. is_configured 未配置时为 False

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

import datetime

from django.test import TestCase, override_settings

from apps.payment.alipay_pay import AlipayPay


class AlipayPayExtendedTest(TestCase):
    """AlipayPay 扩展测试套件。"""

    # ------------------------------------------------------------------
    # 开发环境（未配置）
    # ------------------------------------------------------------------

    def test_alipay_not_configured(self):
        """未配置时 is_configured=False。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)

    def test_alipay_create_order_dev(self):
        """开发环境返回 mock pay_url。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)
        result = alipay.create_order('CT-EXT-001')
        self.assertIn('pay_url', result)
        self.assertTrue(result.get('mock', False))
        self.assertIn('CT-EXT-001', result['pay_url'])

    def test_alipay_verify_notify_dev(self):
        """开发环境验签返回模拟数据（True）。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)
        params = {
            'out_trade_no': 'CT-EXT-002',
            'trade_no': 'ali_tx_ext_002',
        }
        result = alipay.verify_notify(params)
        self.assertIsNotNone(result)
        self.assertEqual(result['trade_status'], 'TRADE_SUCCESS')
        self.assertEqual(result['out_trade_no'], 'CT-EXT-002')

    def test_alipay_query_daily_transactions_dev(self):
        """开发环境返回空字典。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)
        today = datetime.date.today()
        result = alipay.query_daily_transactions(today)
        self.assertEqual(result, {})

    # ------------------------------------------------------------------
    # 已配置环境（通过 override_settings）
    # ------------------------------------------------------------------

    @override_settings(
        ALIPAY_APP_ID='alipay_app_ext',
        ALIPAY_PRIVATE_KEY='alipay_key_ext',
    )
    def test_alipay_configured_is_configured(self):
        """配置后 is_configured=True。"""
        alipay = AlipayPay()
        self.assertTrue(alipay.is_configured)

    @override_settings(
        ALIPAY_APP_ID='alipay_app_ext',
        ALIPAY_PRIVATE_KEY='alipay_key_ext',
    )
    def test_alipay_query_daily_transactions_configured(self):
        """已配置环境返回空字典（骨架实现）。"""
        alipay = AlipayPay()
        self.assertTrue(alipay.is_configured)
        today = datetime.date.today()
        result = alipay.query_daily_transactions(today)
        self.assertEqual(result, {})
