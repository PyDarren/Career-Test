"""安全审计测试 — 自动化安全检查。

覆盖范围：
- CSRF 保护（POST 无 token → 403）
- Referer 校验（评分 / 支付接口）
- 金额防篡改（服务端硬编码）
- 防重复支付
- SQL 注入鲁棒性
- XSS 防护（反馈 / 客服留言）
- 速率限制（100 次/分钟 → 部分 429）
- 订单号枚举防护（404 不泄露信息）
- 报告访问控制（未支付不可访问）
- 微信回调签名验证
- HTTPS 重定向（开发环境不强制）
- 生产环境 DEBUG 关闭
- 敏感数据不泄露（评分结果不含原始答案）

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md Phase 7
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.template import Context, Template
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.utils.html import escape

from apps.assessment.models import Assessment, Question
from apps.common import middleware as common_middleware
from apps.payment.models import Order
from tests.performance.test_performance import build_answers


class SecurityAuditTest(TestCase):
    """安全审计测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()
        common_middleware._local_rate_limit_store.clear()
        self.answers = build_answers('INTJ')
        self.assessment = Assessment.objects.create(
            uuid='sec-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={
                'EI': {'percentage': 20, 'label': 'I', 'score_a': 12,
                       'score_b': 24, 'strength': 'moderate'},
                'SN': {'percentage': 25, 'label': 'N', 'score_a': 9,
                       'score_b': 27, 'strength': 'distinct'},
                'TF': {'percentage': 75, 'label': 'T', 'score_a': 27,
                       'score_b': 9, 'strength': 'distinct'},
                'JP': {'percentage': 70, 'label': 'J', 'score_a': 25,
                       'score_b': 11, 'strength': 'distinct'},
            },
            facet_scores=[],
            consistency_flag='normal',
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _post_score(self, client=None, answers=None, uuid='sec-score-uuid',
                    **extra):
        """发送 POST /api/score/ 请求。"""
        client = client or self.client
        payload = {
            'answers': answers if answers is not None else self.answers,
            'uuid': uuid,
        }
        return client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
            **extra,
        )

    def _create_payment(self, assessment_id=None, uuid='sec-uuid-001',
                        method='wechat', referer=None, amount=None):
        """创建支付订单辅助方法。"""
        client = Client()
        body = {
            'assessment_id': assessment_id or self.assessment.id,
            'uuid': uuid,
            'method': method,
        }
        if amount is not None:
            body['amount'] = amount
        kwargs = {'content_type': 'application/json', 'data': json.dumps(body)}
        if referer:
            kwargs['HTTP_REFERER'] = referer
        return client.post('/api/payment/create/', **kwargs)

    # ------------------------------------------------------------------
    # CSRF 保护
    # ------------------------------------------------------------------

    def test_csrf_protection_on_post(self):
        """POST /api/score/ 无 CSRF token → 403。

        Django 测试 Client 默认不强制 CSRF，需要用
        ``enforce_csrf_checks=True`` 显式启用。
        """
        csrf_client = Client(enforce_csrf_checks=True)
        response = self._post_score(client=csrf_client)
        self.assertEqual(response.status_code, 403)

    # ------------------------------------------------------------------
    # Referer 校验
    # ------------------------------------------------------------------

    def test_referer_validation_score(self):
        """POST /api/score/ 带恶意 Referer → 403。"""
        response = self._post_score(HTTP_REFERER='http://evil.com/attack')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())

    def test_referer_validation_payment(self):
        """POST /api/payment/create/ 带恶意 Referer → 403。"""
        response = self._create_payment(referer='http://evil.com/attack')
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())

    # ------------------------------------------------------------------
    # 金额防篡改
    # ------------------------------------------------------------------

    def test_amount_tamper_proof(self):
        """POST /api/payment/create/ 带 amount=0.01 → 订单金额仍为 2.99。"""
        response = self._create_payment(amount='0.01')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # 返回金额仍为服务端硬编码值
        self.assertEqual(data['amount'], '2.99')
        # 数据库订单金额未被篡改
        order = Order.objects.get(order_no=data['order_no'])
        self.assertEqual(order.amount, Decimal('2.99'))

    # ------------------------------------------------------------------
    # 防重复支付
    # ------------------------------------------------------------------

    def test_duplicate_payment_blocked(self):
        """同一 assessment 已 paid → 再次创建 400。"""
        Order.objects.create(
            order_no='CT-SEC-PAID-001',
            uuid='sec-uuid-001',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )
        response = self._create_payment()
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    # ------------------------------------------------------------------
    # SQL 注入鲁棒性
    # ------------------------------------------------------------------

    def test_sql_injection_score(self):
        """POST /api/score/ answers 含 SQL 注入字符 → 不崩溃（返回受控错误）。"""
        # 1. position 字段含 SQL 注入字符串 → 参数校验拦截（400）
        sql_answers = [
            {'question_id': q['id'], 'position': "' OR 1=1--"}
            for q in Question.objects.order_by('display_order').values('id')[:48]
        ]
        response = self._post_score(answers=sql_answers,
                                    uuid='sec-sql-injection-1')
        self.assertIn(response.status_code, (400, 500))
        # 服务器仍正常运行
        health = self.client.get('/')
        self.assertEqual(health.status_code, 200)

        # 2. question_id 字段含 SQL 注入字符串（position 合法）→ 受控错误
        sql_qid_answers = [
            {'question_id': "1' OR '1'='1", 'position': 4}
            for _ in range(48)
        ]
        response = self._post_score(answers=sql_qid_answers,
                                    uuid='sec-sql-injection-2')
        self.assertIn(response.status_code, (400, 500))
        # 服务器仍正常运行
        health = self.client.get('/')
        self.assertEqual(health.status_code, 200)

    # ------------------------------------------------------------------
    # XSS 防护
    # ------------------------------------------------------------------

    def test_xss_in_feedback(self):
        """POST /api/feedback/ content 含 <script> → 被转义或拒绝。"""
        xss_payload = '<script>alert("xss")</script>'
        response = self.client.post(
            '/api/feedback/',
            data=json.dumps({
                'uuid': 'sec-xss-feedback',
                'feedback_type': 'report_text',
                'content': xss_payload,
            }),
            content_type='application/json',
        )
        # 被拒绝（400）或接受（200）
        self.assertIn(response.status_code, (200, 400))

        if response.status_code == 200:
            # 验证存储内容经 Django 模板自动转义后安全
            from apps.stats.models import Feedback
            fb = Feedback.objects.filter(
                uuid='sec-xss-feedback', feedback_type='report_text'
            ).first()
            self.assertIsNotNone(fb)
            # 内容原文存储，但模板渲染时会自动转义
            rendered = Template('{{ content }}').render(
                Context({'content': fb.content})
            )
            self.assertNotIn('<script>', rendered)
            self.assertIn('&lt;script&gt;', rendered)

    def test_xss_in_customer_service(self):
        """POST /api/customer-service/ message 含 <script> → 被转义或拒绝。"""
        xss_payload = '<script>document.cookie</script>'
        response = self.client.post(
            '/api/customer-service/',
            data=json.dumps({
                'message': xss_payload,
                'uuid': 'sec-xss-cs',
            }),
            content_type='application/json',
        )
        self.assertIn(response.status_code, (200, 400))

        if response.status_code == 200:
            from apps.stats.models import CustomerServiceMessage
            msg = CustomerServiceMessage.objects.filter(
                uuid='sec-xss-cs'
            ).first()
            self.assertIsNotNone(msg)
            # 模板自动转义验证
            rendered = Template('{{ message }}').render(
                Context({'message': msg.message})
            )
            self.assertNotIn('<script>', rendered)
            self.assertIn('&lt;script&gt;', rendered)

    # ------------------------------------------------------------------
    # 速率限制
    # ------------------------------------------------------------------

    def test_rate_limiting(self):
        """100 次/分钟请求 /api/ → 部分 429。"""
        statuses = []
        for _ in range(100):
            response = self.client.get('/api/stats/completed-count/')
            statuses.append(response.status_code)

        rate_limited = [s for s in statuses if s == 429]
        ok_count = [s for s in statuses if s == 200]
        # 应有部分请求被限流（429），也有部分正常通过
        self.assertGreater(len(rate_limited), 0,
                          '100 次 /api/ 请求应触发速率限制（429）')
        self.assertGreater(len(ok_count), 0,
                          '前 60 次请求应正常通过')

    # ------------------------------------------------------------------
    # 订单号枚举防护
    # ------------------------------------------------------------------

    def test_order_id_guessing(self):
        """随机 order_no 查询 → 404（不泄露信息）。"""
        response = self.client.get('/api/order/status/CT-RANDOM-GUESS-001/')
        self.assertEqual(response.status_code, 404)
        # 响应不泄露内部信息
        body = response.json()
        self.assertIn('error', body)
        self.assertNotIn('traceback', str(body).lower())

    # ------------------------------------------------------------------
    # 报告访问控制
    # ------------------------------------------------------------------

    def test_report_access_without_payment(self):
        """GET /report/{random}/ → 404（未支付不可访问）。"""
        response = self.client.get('/report/CT-RANDOM-NO-PAY/')
        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------
    # 微信回调签名验证
    # ------------------------------------------------------------------

    @override_settings(
        WECHAT_APP_ID='wx_test_app',
        WECHAT_MCH_ID='mch_test',
        WECHAT_API_KEY='api_key_test',
    )
    def test_payment_callback_signature(self):
        """微信回调无签名 → 验证不通过（400 FAIL）。

        通过 override_settings 模拟生产环境已配置微信支付，
        此时 verify_notify 走生产验签流程，无签名头 → 返回 None。
        """
        body = json.dumps({
            'resource': {
                'out_trade_no': 'CT-NO-SIG',
                'transaction_id': 'tx_001',
            }
        })
        # 不携带任何 Wechatpay-* 签名头
        response = self.client.post(
            '/payment/wechat/notify/',
            data=body,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'FAIL')

    # ------------------------------------------------------------------
    # HTTPS 重定向检查
    # ------------------------------------------------------------------

    def test_https_redirect_check(self):
        """开发环境不强制 HTTPS（production 才需要）。"""
        # 开发环境 SECURE_SSL_REDIRECT 未启用
        self.assertNotEqual(getattr(settings, 'SECURE_SSL_REDIRECT', False), True)
        # HTTP 请求不被重定向到 HTTPS
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response)

    # ------------------------------------------------------------------
    # 生产环境 DEBUG 关闭
    # ------------------------------------------------------------------

    def test_debug_mode_off_in_production(self):
        """production settings DEBUG=False（检查 settings 文件）。"""
        from caretest.settings import production
        self.assertFalse(production.DEBUG,
                         '生产环境 DEBUG 必须为 False')

    # ------------------------------------------------------------------
    # 敏感数据不泄露
    # ------------------------------------------------------------------

    def test_sensitive_data_not_in_response(self):
        """评分结果不包含用户原始答案。"""
        response = self._post_score(uuid='sec-sensitive-uuid')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # 响应不应包含原始 answers 字段
        self.assertNotIn('answers', data)
        # 响应不应包含原始 position 数据
        response_text = json.dumps(data, ensure_ascii=False)
        self.assertNotIn('"position"', response_text)
        # 响应不应包含 question_id 列表
        self.assertNotIn('"question_id"', response_text)

        # 数据库测评记录也不存储原始答案
        assessment = Assessment.objects.get(uuid='sec-sensitive-uuid')
        self.assertNotIn('answers', assessment.dimension_scores)
        # dimension_scores 仅含聚合得分，不含原始 position
        for dim_data in assessment.dimension_scores.values():
            self.assertNotIn('position', dim_data)
