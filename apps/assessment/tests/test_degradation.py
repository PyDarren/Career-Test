"""降级方案验证测试。

测试各种降级场景：
- ScoringEngine 异常输入不崩溃
- 全选中间值仍能计算
- 极端作答标记
- API 错误格式返回 400（不是 500）
- 结果页无测评记录不崩溃
- 职业匹配空数据
- 支付参数校验
- 反馈类型校验

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md
"""

import json

from django.core.cache import cache
from django.test import TestCase

from apps.assessment.models import Assessment, Question
from apps.assessment.scoring import ScoringEngine
from apps.careers.matching import CareerMatcher
from apps.payment.models import Order


class DegradationTest(TestCase):
    """降级方案验证测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    SCORE_REFERER = 'http://127.0.0.1:8000/assessment/'
    PAYMENT_REFERER = 'http://127.0.0.1:8000/result/'

    def setUp(self):
        cache.clear()
        self.engine = ScoringEngine()
        self.questions = list(
            Question.objects
            .order_by('display_order')
            .values(
                'id',
                'dimension',
                'facet',
                'facet_order',
                'pole_a',
                'pole_b',
                'is_reverse',
                'display_order',
            )
        )
        # 预构造 48 题全选位置 3 的答案
        self.answers_mid = [
            {'question_id': q['id'], 'position': 3}
            for q in self.questions
        ]

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_all_same(self, position):
        """所有题选同一位置。"""
        return [
            {'question_id': q['id'], 'position': position}
            for q in self.questions
        ]

    def _post_score(self, payload=None, **extra):
        """提交评分。"""
        if payload is None:
            payload = {'answers': self.answers_mid, 'uuid': 'deg-uuid-001'}
        return self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
            **extra,
        )

    def _create_payment(self, body, **extra):
        """创建支付。"""
        kwargs = {
            'content_type': 'application/json',
            'data': json.dumps(body),
            'HTTP_REFERER': self.PAYMENT_REFERER,
        }
        kwargs.update(extra)
        return self.client.post('/api/payment/create/', **kwargs)

    # ------------------------------------------------------------------
    # ScoringEngine 降级行为
    # ------------------------------------------------------------------

    def test_fallback_scoring_basic(self):
        """ScoringEngine 在异常输入下不崩溃（空答案列表）。"""
        # 空答案 → 不崩溃，返回有效结构
        result = self.engine.calculate([], self.questions)
        self.assertIn('mbti_type', result)
        self.assertIn('dimensions', result)
        self.assertIn('facets', result)
        self.assertIn('consistency_flag', result)
        # 空答案 → 四维度均 0:0 → 'XXXX'
        self.assertEqual(result['mbti_type'], 'XXXX')

    def test_fallback_scoring_all_mid(self):
        """全选位置 3 → 仍能计算出结果。"""
        result = self.engine.calculate(self.answers_mid, self.questions)
        self.assertIn('mbti_type', result)
        self.assertIn('dimensions', result)
        # 全选位置 3 → ESTJ（每维度 9 正向 +3 分 vs 3 反向 +3 分 → A 极胜）
        self.assertEqual(result['mbti_type'], 'ESTJ')
        # 每维度都有有效得分
        for dim_code in ('EI', 'SN', 'TF', 'JP'):
            dim = result['dimensions'][dim_code]
            self.assertGreater(dim['score_a'] + dim['score_b'], 0)

    def test_scoring_extreme_answers(self):
        """全选位置 1 或 6 → 标记 extreme_response。"""
        # 全选位置 1
        answers_pos1 = self._build_all_same(1)
        result = self.engine.calculate(answers_pos1, self.questions)
        self.assertIn('extreme_response', result['consistency_flag'])

        # 全选位置 6
        answers_pos6 = self._build_all_same(6)
        result = self.engine.calculate(answers_pos6, self.questions)
        self.assertIn('extreme_response', result['consistency_flag'])

    # ------------------------------------------------------------------
    # ScoreView API 优雅降级
    # ------------------------------------------------------------------

    def test_score_api_graceful_error(self):
        """提交错误格式 → 400 错误响应（不是 500）。"""
        response = self.client.post(
            '/api/score/',
            data='not-valid-json',
            content_type='application/json',
            HTTP_REFERER=self.SCORE_REFERER,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_score_api_missing_answers(self):
        """缺少 answers → 400。"""
        payload = {'uuid': 'deg-uuid-001'}
        response = self._post_score(payload=payload, HTTP_REFERER=self.SCORE_REFERER)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_score_api_wrong_count(self):
        """47 题答案 → 400。"""
        answers = self.answers_mid[:47]
        payload = {'answers': answers, 'uuid': 'deg-uuid-001'}
        response = self._post_score(payload=payload, HTTP_REFERER=self.SCORE_REFERER)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_score_api_invalid_position(self):
        """position=7 → 400。"""
        answers = self.answers_mid[:]
        answers[10]['position'] = 7
        payload = {'answers': answers, 'uuid': 'deg-uuid-001'}
        response = self._post_score(payload=payload, HTTP_REFERER=self.SCORE_REFERER)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    # ------------------------------------------------------------------
    # ResultView 降级
    # ------------------------------------------------------------------

    def test_result_view_no_assessment(self):
        """uuid 不存在 → 200（页面正常渲染，不崩溃）。"""
        response = self.client.get('/result/nonexistent-uuid-999/')
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # CareerMatcher 降级
    # ------------------------------------------------------------------

    def test_career_match_empty_data(self):
        """空维度数据 → 匹配返回空列表或默认列表（不崩溃）。"""
        matcher = CareerMatcher()
        results = matcher.match('INTJ', {})
        self.assertIsInstance(results, list)

    # ------------------------------------------------------------------
    # 支付降级
    # ------------------------------------------------------------------

    def test_payment_invalid_method(self):
        """method=invalid → 400。"""
        body = {
            'assessment_id': 1,
            'uuid': 'deg-uuid-001',
            'method': 'invalid',
        }
        response = self._create_payment(body)
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_payment_missing_assessment(self):
        """assessment_id 不存在 → 404。"""
        body = {
            'assessment_id': 999999,
            'uuid': 'deg-uuid-001',
            'method': 'wechat',
        }
        response = self._create_payment(body)
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())

    # ------------------------------------------------------------------
    # 反馈降级
    # ------------------------------------------------------------------

    def test_feedback_invalid_type(self):
        """无效 feedback_type → 400。"""
        payload = {
            'uuid': 'deg-uuid-001',
            'feedback_type': 'invalid_type',
        }
        response = self.client.post(
            '/api/feedback/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'invalid_type')
