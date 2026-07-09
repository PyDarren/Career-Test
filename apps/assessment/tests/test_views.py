"""ScoreView / HistoryView API 测试。

覆盖 /api/score/ 和 /api/history/<uuid>/ 端点：
1. 正常 48 题请求 → 200
2. 答案数量不足 → 400
3. position 超出范围 → 400
4. 缺少 uuid → 400
5. 非本站 Referer → 403
6. 请求后 Assessment 记录数 +1
7. 创建测评记录后查询历史 → 返回记录

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.6
"""

import json

from django.core.cache import cache
from django.test import TestCase

from apps.assessment.models import Assessment, Question


class ScoreAPITest(TestCase):
    """/api/score/ 端点测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_answers(self, target_type='INTJ'):
        """构造特定 MBTI 类型的 48 题答案。"""
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'is_reverse')
        )
        type_map = {
            'EI': target_type[0],
            'SN': target_type[1],
            'TF': target_type[2],
            'JP': target_type[3],
        }
        dim_poles = {
            'EI': ('E', 'I'),
            'SN': ('S', 'N'),
            'TF': ('T', 'F'),
            'JP': ('J', 'P'),
        }
        answers = []
        for q in questions:
            dim = q['dimension']
            target_pole = type_map[dim]
            pole_a, pole_b = dim_poles[dim]
            position = 1 if target_pole == pole_a else 6
            if q['is_reverse']:
                position = 7 - position
            answers.append({'question_id': q['id'], 'position': position})
        return answers

    def _post_score(self, answers=None, uuid='test-uuid-001', **extra):
        """发送 POST /api/score/ 请求的辅助方法。"""
        if answers is None:
            answers = self._build_answers('INTJ')
        payload = {'answers': answers, 'uuid': uuid}
        return self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
            **extra,
        )

    # ------------------------------------------------------------------
    # 测试用例
    # ------------------------------------------------------------------

    def test_score_api_normal_request(self):
        """正常 48 题请求 → 200，返回 mbti_type/type_info/recommended_careers。"""
        response = self._post_score()

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn('mbti_type', data)
        self.assertIn('type_info', data)
        self.assertIn('recommended_careers', data)
        self.assertIn('dimensions', data)
        self.assertIn('cognitive_stack', data)
        self.assertIn('consistency_flag', data)
        self.assertIn('assessment_id', data)
        self.assertEqual(data['uuid'], 'test-uuid-001')

    def test_score_api_wrong_answer_count(self):
        """答案数量不足 → 400。"""
        answers = self._build_answers('INTJ')[:40]  # 仅 40 题
        response = self._post_score(answers=answers)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_score_api_invalid_position(self):
        """position 超出范围 → 400。"""
        answers = self._build_answers('INTJ')
        answers[10]['position'] = 9  # 非法位置
        response = self._post_score(answers=answers)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_score_api_missing_uuid(self):
        """缺少 uuid → 400。"""
        answers = self._build_answers('INTJ')
        payload = {'answers': answers}
        response = self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_score_api_invalid_referer(self):
        """非本站 Referer → 403。"""
        response = self._post_score(HTTP_REFERER='http://evil.com/')

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)

    def test_score_api_creates_assessment(self):
        """请求后 Assessment 记录数 +1。"""
        before_count = Assessment.objects.count()

        response = self._post_score(uuid='test-uuid-create')
        self.assertEqual(response.status_code, 200)

        after_count = Assessment.objects.count()
        self.assertEqual(after_count, before_count + 1)

        # 验证记录内容
        assessment = Assessment.objects.filter(uuid='test-uuid-create').first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.uuid, 'test-uuid-create')
        self.assertEqual(assessment.mbti_type_code, 'INTJ')


class HistoryAPITest(TestCase):
    """/api/history/<uuid>/ 端点测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()

    def test_history_api(self):
        """创建测评记录后查询历史 → 返回记录。"""
        # 直接创建一条测评记录
        Assessment.objects.create(
            uuid='test-uuid-history',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}, 'SN': {'label': 'N'}},
            facet_scores=[],
            consistency_flag='normal',
        )

        response = self.client.get('/api/history/test-uuid-history/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('history', data)
        self.assertEqual(len(data['history']), 1)

        record = data['history'][0]
        self.assertEqual(record['mbti_type'], 'INTJ')
        self.assertIn('assessment_id', record)
        self.assertIn('created_at', record)
        self.assertIn('dimensions', record)
