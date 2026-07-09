"""微信支付 / 支付宝封装单元测试。

覆盖支付 SDK 的核心流程：
1. 开发环境降级（未配置时返回 mock 链接 / 模拟数据）
2. 已配置环境下单（返回 code_url / pay_url）
3. 回调验签（有效 / 无效参数处理）

开发环境默认未配置商户证书，is_configured=False；已配置路径通过
``override_settings`` 注入测试密钥进行覆盖。

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.8
"""

import json
import time

from django.test import TestCase, override_settings

from apps.payment.alipay_pay import AlipayPay
from apps.payment.wechat_pay import WechatPay


class WechatPayTest(TestCase):
    """微信支付封装测试套件。"""

    # ------------------------------------------------------------------
    # create_order
    # ------------------------------------------------------------------

    def test_wechat_not_configured_returns_mock(self):
        """未配置时 create_order 返回 mock 链接。"""
        wx = WechatPay()
        self.assertFalse(wx.is_configured)
        result = wx.create_order('CT123')
        self.assertIn('code_url', result)
        self.assertTrue(result.get('mock', False))
        self.assertIn('CT123', result['code_url'])

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_create_order_returns_code_url(self):
        """create_order 返回含 code_url。"""
        wx = WechatPay()
        self.assertTrue(wx.is_configured)
        result = wx.create_order('CT123')
        self.assertIn('code_url', result)
        self.assertIn('CT123', result['code_url'])
        # 已配置路径不返回 mock 标记
        self.assertNotIn('mock', result)
        self.assertIn('timestamp', result)
        self.assertIn('nonce', result)
        self.assertIn('signature', result)

    # ------------------------------------------------------------------
    # verify_notify
    # ------------------------------------------------------------------

    def test_wechat_verify_notify_not_configured(self):
        """未配置时 verify_notify 返回模拟数据。"""
        wx = WechatPay()
        self.assertFalse(wx.is_configured)
        body = json.dumps({
            'resource': {
                'out_trade_no': 'CT123',
                'transaction_id': 'wx_tx_123',
            }
        })
        result = wx.verify_notify({}, body)
        self.assertIsNotNone(result)
        self.assertEqual(result['out_trade_no'], 'CT123')
        self.assertEqual(result['trade_state'], 'SUCCESS')
        self.assertTrue(result['transaction_id'])

    def test_wechat_verify_notify_invalid_json(self):
        """无效 JSON → None。"""
        wx = WechatPay()
        self.assertFalse(wx.is_configured)
        result = wx.verify_notify({}, 'not-a-valid-json')
        self.assertIsNone(result)

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_verify_notify_valid(self):
        """有效 JSON → 返回解密数据。"""
        wx = WechatPay()
        self.assertTrue(wx.is_configured)
        # 模拟解密后的明文（开发环境 _decrypt_resource 原样返回 ciphertext）
        decrypted_payload = json.dumps({
            'out_trade_no': 'CT123',
            'transaction_id': 'wx_tx_123',
            'trade_state': 'SUCCESS',
        })
        body = json.dumps({
            'resource': {
                'ciphertext': decrypted_payload,
                'nonce': 'abc123',
                'associated_data': 'transaction',
            }
        })
        headers = {
            'Wechatpay-Timestamp': str(int(time.time())),
            'Wechatpay-Nonce': 'nonce123',
            'Wechatpay-Signature': 'sig123',
            'Wechatpay-Serial': 'serial123',
        }
        result = wx.verify_notify(headers, body)
        self.assertIsNotNone(result)
        self.assertEqual(result['out_trade_no'], 'CT123')
        self.assertEqual(result['transaction_id'], 'wx_tx_123')
        self.assertEqual(result['trade_state'], 'SUCCESS')

    # ------------------------------------------------------------------
    # verify_notify 异常分支
    # ------------------------------------------------------------------

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_verify_notify_timestamp_expired(self):
        """回调时间戳过期 → None。"""
        wx = WechatPay()
        headers = {
            'Wechatpay-Timestamp': '1000',  # 远早于当前时间
            'Wechatpay-Nonce': 'nonce123',
            'Wechatpay-Signature': 'sig123',
            'Wechatpay-Serial': 'serial123',
        }
        body = json.dumps({'resource': {}})
        result = wx.verify_notify(headers, body)
        self.assertIsNone(result)

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_verify_notify_invalid_timestamp(self):
        """回调时间戳非数字 → None。"""
        wx = WechatPay()
        headers = {
            'Wechatpay-Timestamp': 'not-a-number',
            'Wechatpay-Nonce': 'nonce123',
            'Wechatpay-Signature': 'sig123',
            'Wechatpay-Serial': 'serial123',
        }
        body = json.dumps({'resource': {}})
        result = wx.verify_notify(headers, body)
        self.assertIsNone(result)

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_verify_notify_signature_missing(self):
        """缺少签名头 → 验签失败 → None。"""
        wx = WechatPay()
        headers = {
            'Wechatpay-Timestamp': str(int(time.time())),
            'Wechatpay-Nonce': 'nonce123',
            # 缺少 Wechatpay-Signature
            'Wechatpay-Serial': 'serial123',
        }
        body = json.dumps({'resource': {}})
        result = wx.verify_notify(headers, body)
        self.assertIsNone(result)

    @override_settings(
        WECHAT_APP_ID='wx_app',
        WECHAT_MCH_ID='wx_mch',
        WECHAT_API_KEY='wx_key',
    )
    def test_wechat_verify_notify_decrypt_fail(self):
        """解密资源失败（body 非法 JSON）→ None。"""
        wx = WechatPay()
        headers = {
            'Wechatpay-Timestamp': str(int(time.time())),
            'Wechatpay-Nonce': 'nonce123',
            'Wechatpay-Signature': 'sig123',
            'Wechatpay-Serial': 'serial123',
        }
        result = wx.verify_notify(headers, 'not-valid-json')
        self.assertIsNone(result)


class AlipayPayTest(TestCase):
    """支付宝封装测试套件。"""

    # ------------------------------------------------------------------
    # create_order
    # ------------------------------------------------------------------

    def test_alipay_not_configured_returns_mock(self):
        """未配置时 create_order 返回 mock 链接。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)
        result = alipay.create_order('CT456')
        self.assertIn('pay_url', result)
        self.assertTrue(result.get('mock', False))
        self.assertIn('CT456', result['pay_url'])

    @override_settings(
        ALIPAY_APP_ID='alipay_app',
        ALIPAY_PRIVATE_KEY='alipay_key',
    )
    def test_alipay_create_order_returns_pay_url(self):
        """create_order 返回含 pay_url。"""
        alipay = AlipayPay()
        self.assertTrue(alipay.is_configured)
        result = alipay.create_order('CT456')
        self.assertIn('pay_url', result)
        # 已配置路径不返回 mock 标记，但附带请求参数
        self.assertNotIn('mock', result)
        self.assertIn('params', result)
        self.assertEqual(result['params']['method'], 'alipay.trade.page.pay')
        self.assertIn('sign', result['params'])
        # out_trade_no 封装在 biz_content（JSON 字符串）内
        biz_content = json.loads(result['params']['biz_content'])
        self.assertEqual(biz_content['out_trade_no'], 'CT456')
        self.assertEqual(biz_content['total_amount'], '2.99')

    # ------------------------------------------------------------------
    # verify_notify
    # ------------------------------------------------------------------

    def test_alipay_verify_notify_not_configured(self):
        """未配置时 verify_notify 返回模拟数据。"""
        alipay = AlipayPay()
        self.assertFalse(alipay.is_configured)
        params = {'out_trade_no': 'CT456', 'trade_no': 'ali_tx_456'}
        result = alipay.verify_notify(params)
        self.assertIsNotNone(result)
        self.assertEqual(result['trade_status'], 'TRADE_SUCCESS')
        self.assertEqual(result['out_trade_no'], 'CT456')

    @override_settings(
        ALIPAY_APP_ID='alipay_app',
        ALIPAY_PRIVATE_KEY='alipay_key',
    )
    def test_alipay_verify_notify_invalid_params(self):
        """缺少 sign → None。"""
        alipay = AlipayPay()
        self.assertTrue(alipay.is_configured)
        params = {
            'out_trade_no': 'CT456',
            'trade_no': 'ali_tx_456',
            'trade_status': 'TRADE_SUCCESS',
        }
        result = alipay.verify_notify(params)
        self.assertIsNone(result)

    @override_settings(
        ALIPAY_APP_ID='alipay_app',
        ALIPAY_PRIVATE_KEY='alipay_key',
    )
    def test_alipay_verify_notify_valid(self):
        """有效参数 → 返回解析数据。"""
        alipay = AlipayPay()
        self.assertTrue(alipay.is_configured)
        params = {
            'out_trade_no': 'CT456',
            'trade_no': 'ali_tx_456',
            'trade_status': 'TRADE_SUCCESS',
            'total_amount': '2.99',
            'sign': 'valid_sign',
            'sign_type': 'RSA2',
        }
        result = alipay.verify_notify(params)
        self.assertIsNotNone(result)
        self.assertEqual(result['out_trade_no'], 'CT456')
        self.assertEqual(result['trade_no'], 'ali_tx_456')
        self.assertEqual(result['trade_status'], 'TRADE_SUCCESS')
        self.assertEqual(result['total_amount'], '2.99')

    @override_settings(
        ALIPAY_APP_ID='alipay_app',
        ALIPAY_PRIVATE_KEY='alipay_key',
    )
    def test_alipay_verify_notify_invalid_trade_status(self):
        """交易状态非成功（如 WAIT_BUYER_PAY）→ None。"""
        alipay = AlipayPay()
        params = {
            'out_trade_no': 'CT456',
            'trade_no': 'ali_tx_456',
            'trade_status': 'WAIT_BUYER_PAY',  # 非成功状态
            'total_amount': '2.99',
            'sign': 'valid_sign',
        }
        result = alipay.verify_notify(params)
        self.assertIsNone(result)
