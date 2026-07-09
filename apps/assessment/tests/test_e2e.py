"""端到端全流程测试。

测试完整用户流程：
首页 → 答题页 → 评分提交 → 结果页 → 职业推荐 → 支付创建 →
支付回调 → 报告页 → 反馈 → 历史记录 → 报告找回

使用 Django test Client 模拟全流程，每一步都验证关键返回字段。
"""

import json

from django.core.cache import cache
from django.test import TestCase

from apps.assessment.models import Assessment, Question


class E2EFlowTest(TestCase):
    """端到端全流程测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    # Referer 头（ScoreView / CreatePaymentView 校验请求来源）
    SCORE_REFERER = 'http://127.0.0.1:8000/assessment/'
    PAYMENT_REFERER = 'http://127.0.0.1:8000/result/'

    def setUp(self):
        cache.clear()
        # 构造 48 题答案：全部选位置 3（中间值）
        # position 3 → (1, 'a')；反向题翻转后归入 B 极
        # 每维度 9 正向 + 3 反向 → score_a=9, score_b=3 → ESTJ
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id')
        )
        self.answers = [
            {'question_id': q['id'], 'position': 3}
            for q in questions
        ]
        self.user_uuid = 'e2e-uuid-001'

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _post_score(self, **extra):
        """提交评分 POST /api/score/。"""
        payload = {'answers': self.answers, 'uuid': self.user_uuid}
        return self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
            **extra,
        )

    def _create_payment(self, assessment_id, method='wechat', **extra):
        """创建支付 POST /api/payment/create/。"""
        payload = {
            'assessment_id': assessment_id,
            'uuid': self.user_uuid,
            'method': method,
        }
        return self.client.post(
            '/api/payment/create/',
            data=json.dumps(payload),
            content_type='application/json',
            **extra,
        )

    def _wechat_notify(self, order_no):
        """模拟微信支付回调 POST /payment/wechat/notify/。"""
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

    # ------------------------------------------------------------------
    # 测试用例
    # ------------------------------------------------------------------

    def test_full_flow_home_to_score(self):
        """首页 → 答题页。"""
        # GET / → 200
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # GET /assessment/ → 200 含 questions_json
        response = self.client.get('/assessment/')
        self.assertEqual(response.status_code, 200)
        # 上下文中有 48 道题目
        self.assertEqual(response.context['total_questions'], 48)
        self.assertIsNotNone(response.context['questions_json'])

    def test_full_flow_score_to_result(self):
        """评分提交 → 结果页。"""
        # POST /api/score/ with 48 answers → 200 含 mbti_type
        response = self._post_score(HTTP_REFERER=self.SCORE_REFERER)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('mbti_type', data)
        self.assertIn('assessment_id', data)
        self.assertIn('type_info', data)
        self.assertIn('recommended_careers', data)
        self.assertIn('dimensions', data)
        self.assertIn('cognitive_stack', data)
        self.assertIn('consistency_flag', data)
        self.assertEqual(data['uuid'], self.user_uuid)
        # 全选位置 3 → ESTJ
        self.assertEqual(data['mbti_type'], 'ESTJ')
        # 职业推荐非空
        self.assertIsInstance(data['recommended_careers'], list)

        # GET /result/{uuid}/ → 200
        response = self.client.get(f'/result/{self.user_uuid}/')
        self.assertEqual(response.status_code, 200)

    def test_full_flow_payment(self):
        """支付创建 → 支付回调 → 订单状态 → 报告页。"""
        # 先提交评分获取 assessment_id
        score_response = self._post_score(HTTP_REFERER=self.SCORE_REFERER)
        self.assertEqual(score_response.status_code, 200)
        assessment_id = score_response.json()['assessment_id']

        # POST /api/payment/create/ → 200 含 order_no
        pay_response = self._create_payment(
            assessment_id,
            HTTP_REFERER=self.PAYMENT_REFERER,
        )
        self.assertEqual(pay_response.status_code, 200)
        pay_data = pay_response.json()
        self.assertIn('order_no', pay_data)
        self.assertIn('pay_info', pay_data)
        self.assertIn('code_url', pay_data['pay_info'])
        order_no = pay_data['order_no']

        # 模拟微信回调 POST /payment/wechat/notify/ → 200
        notify_response = self._wechat_notify(order_no)
        self.assertEqual(notify_response.status_code, 200)
        self.assertEqual(notify_response.json()['code'], 'SUCCESS')

        # GET /api/order/status/{order_no}/ → status=paid
        status_response = self.client.get(f'/api/order/status/{order_no}/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()['status'], 'paid')

        # GET /report/{order_no}/ → 200
        report_response = self.client.get(f'/report/{order_no}/')
        self.assertEqual(report_response.status_code, 200)

    def test_full_flow_feedback(self):
        """反馈提交。"""
        # 先提交评分获取 assessment_id 和 mbti_type
        score_response = self._post_score(HTTP_REFERER=self.SCORE_REFERER)
        score_data = score_response.json()
        assessment_id = score_data['assessment_id']
        mbti_type = score_data['mbti_type']

        # POST /api/feedback/ → 200
        feedback_payload = {
            'uuid': self.user_uuid,
            'feedback_type': 'report_rating',
            'mbti_type': mbti_type,
            'rating': 'up',
        }
        response = self.client.post(
            '/api/feedback/',
            data=json.dumps(feedback_payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_full_flow_history(self):
        """历史记录查询。"""
        # 先提交评分创建测评记录
        self._post_score(HTTP_REFERER=self.SCORE_REFERER)

        # GET /api/history/{uuid}/ → 200 含 history 列表
        response = self.client.get(f'/api/history/{self.user_uuid}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('history', data)
        self.assertEqual(len(data['history']), 1)
        record = data['history'][0]
        self.assertEqual(record['mbti_type'], 'ESTJ')
        self.assertIn('assessment_id', record)
        self.assertIn('created_at', record)
        self.assertIn('dimensions', record)

    def test_full_flow_report_recover(self):
        """报告找回。"""
        # 先提交评分
        score_response = self._post_score(HTTP_REFERER=self.SCORE_REFERER)
        assessment_id = score_response.json()['assessment_id']

        # 创建支付并完成支付
        pay_response = self._create_payment(
            assessment_id,
            HTTP_REFERER=self.PAYMENT_REFERER,
        )
        order_no = pay_response.json()['order_no']
        self._wechat_notify(order_no)

        # POST /api/report/recover/ → 200 含 reports 列表
        response = self.client.post(
            '/api/report/recover/',
            data=json.dumps({'uuid': self.user_uuid}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reports', data)
        self.assertEqual(len(data['reports']), 1)
        report = data['reports'][0]
        self.assertEqual(report['mbti_type'], 'ESTJ')
        self.assertEqual(report['order_no'], order_no)
        self.assertIn('report_url', report)
