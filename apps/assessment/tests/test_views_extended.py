"""ResultView / HistoryView / AssessmentView / ScoreView 扩展测试。

补充覆盖 apps/assessment/views.py 中尚未覆盖的分支：
1. ResultView  —— 有效 uuid / 无效 uuid / 无 uuid / 已支付状态
2. HistoryView —— 最多 3 条 / 空 uuid / 字段格式
3. AssessmentView —— 测评页面加载
4. ScoreView —— 正常提交 / 缺少 uuid

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

import json
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.assessment.models import Assessment, Question
from apps.payment.models import Order


class ResultViewTest(TestCase):
    """ResultView (/result/<uuid>/) 测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()
        self.assessment = Assessment.objects.create(
            uuid='result-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={
                'EI': {'percentage': 33, 'label': 'I', 'score_a': 12, 'score_b': 24,
                       'strength': 'moderate', 'pole_a': 'E', 'pole_b': 'I'},
                'SN': {'percentage': 25, 'label': 'N', 'score_a': 9, 'score_b': 27,
                       'strength': 'distinct', 'pole_a': 'S', 'pole_b': 'N'},
                'TF': {'percentage': 75, 'label': 'T', 'score_a': 27, 'score_b': 9,
                       'strength': 'distinct', 'pole_a': 'T', 'pole_b': 'F'},
                'JP': {'percentage': 70, 'label': 'J', 'score_a': 25, 'score_b': 11,
                       'strength': 'distinct', 'pole_a': 'J', 'pole_b': 'P'},
            },
            facet_scores=[
                {'dimension': 'EI', 'facet': '社交能量', 'pole': 'I',
                 'score_a': 4, 'score_b': 8, 'percentage': 33},
            ],
            consistency_flag='normal',
        )

    def test_result_view_with_valid_uuid(self):
        """有 uuid 且有 Assessment 记录 -> 200，context 含 type_config。"""
        response = self.client.get(f'/result/{self.assessment.uuid}/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIsNotNone(context)
        self.assertIn('type_config', context)
        self.assertIn('assessment', context)
        self.assertIn('dimensions', context)
        self.assertIn('facets', context)
        self.assertIn('careers', context)

    def test_result_view_with_invalid_uuid(self):
        """uuid 不存在 -> 200（空 context，仅含 uuid）。"""
        response = self.client.get('/result/nonexistent-uuid/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context.get('uuid'), 'nonexistent-uuid')
        self.assertNotIn('type_config', context)
        self.assertNotIn('assessment', context)

    def test_result_view_without_uuid(self):
        """无 uuid -> 200（空 context）。"""
        response = self.client.get('/result/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertNotIn('type_config', context)
        self.assertNotIn('uuid', context)

    def test_result_view_checks_paid_status(self):
        """已支付订单 -> context has_paid=True。"""
        Order.objects.create(
            order_no='CT-RESULT-PAID-001',
            uuid='result-uuid-001',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )
        response = self.client.get(f'/result/{self.assessment.uuid}/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertTrue(context.get('has_paid'))
        self.assertIn('report_url', context)

    def test_result_view_unpaid_status(self):
        """无支付订单 -> has_paid=False。"""
        response = self.client.get(f'/result/{self.assessment.uuid}/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertFalse(context.get('has_paid'))


class HistoryViewExtendedTest(TestCase):
    """HistoryView (/api/history/<uuid>/) 扩展测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()

    def _create(self, uuid, mbti='INTJ'):
        return Assessment.objects.create(
            uuid=uuid,
            mbti_type_code=mbti,
            dimension_scores={
                'EI': {'label': 'I', 'percentage': 33},
                'SN': {'label': 'N', 'percentage': 25},
                'TF': {'label': 'T', 'percentage': 75},
                'JP': {'label': 'J', 'percentage': 70},
            },
            facet_scores=[],
            consistency_flag='normal',
        )

    def test_history_returns_max_3(self):
        """5 条记录返回 3 条。"""
        for _ in range(5):
            self._create('hist-ext-uuid-001')
        response = self.client.get('/api/history/hist-ext-uuid-001/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['history']), 3)

    def test_history_empty_uuid(self):
        """不存在的 uuid 返回空列表。"""
        response = self.client.get('/api/history/nonexistent-uuid/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['history'], [])

    def test_history_field_format(self):
        """验证返回字段格式（assessment_id, mbti_type, dimensions, created_at）。"""
        self._create('hist-format-uuid', mbti='ENTP')
        response = self.client.get('/api/history/hist-format-uuid/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['history']), 1)
        record = data['history'][0]
        self.assertIn('assessment_id', record)
        self.assertIn('mbti_type', record)
        self.assertIn('dimensions', record)
        self.assertIn('created_at', record)
        self.assertEqual(record['mbti_type'], 'ENTP')
        self.assertIsInstance(record['assessment_id'], int)
        self.assertIsInstance(record['created_at'], str)


class AssessmentViewTest(TestCase):
    """AssessmentView (/assessment/) 测试套件。"""

    fixtures = ['questions.json']

    def setUp(self):
        cache.clear()

    def test_assessment_page_loads(self):
        """GET /assessment/ -> 200，含 questions_json。"""
        response = self.client.get('/assessment/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIsNotNone(context)
        self.assertIn('questions_json', context)
        self.assertIn('total_questions', context)
        # questions_json 是 JSON 字符串，解析后应为 48 题
        questions = json.loads(context['questions_json'])
        self.assertEqual(len(questions), Question.objects.count())
        self.assertEqual(context['total_questions'], 48)


class ScoreViewExtendedTest(TestCase):
    """ScoreView (/api/score/) 补充测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()

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

    def test_score_valid_submission(self):
        """正常 48 题提交 -> 200，返回 mbti_type。"""
        answers = self._build_answers('INTJ')
        payload = {'answers': answers, 'uuid': 'score-ext-uuid-001'}
        response = self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['mbti_type'], 'INTJ')
        self.assertIn('dimensions', data)
        self.assertIn('facets', data)
        self.assertIn('assessment_id', data)

    def test_score_missing_uuid(self):
        """缺少 uuid -> 400。"""
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
