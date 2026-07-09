"""性能测试 — 测量各接口与核心算法的响应时间。

测试范围：
- 页面响应时间：首页 / 测评页 / 结果页 / 报告页
- API 响应时间：评分接口 / 已完成人数 / 埋点上报
- 核心算法性能：ScoringEngine.calculate() / CareerMatcher.match()
- 首页 HTML 体积
- 并发评分请求

使用 ``time.perf_counter()`` 测量耗时。测试环境性能通常比生产慢 2-3
倍，因此时间断言阈值统一设为目标值的 3 倍。

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md Phase 7
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, Client
from django.utils import timezone

from apps.assessment.models import Assessment, Question
from apps.assessment.scoring import ScoringEngine
from apps.careers.matching import CareerMatcher
from apps.common import middleware as common_middleware
from apps.mbti_types.models import MBTIType
from apps.payment.models import Order


# 16 种 MBTI 类型
MBTI_TYPES = [
    'INTJ', 'INTP', 'ENTJ', 'ENTP',
    'INFJ', 'INFP', 'ENFJ', 'ENFP',
    'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
    'ISTP', 'ISFP', 'ESTP', 'ESFP',
]


def build_answers(target_type='INTJ'):
    """构造特定 MBTI 类型的 48 题答案。

    与 ``apps/assessment/tests/test_views.py`` 中的辅助方法逻辑一致：
    根据目标类型的极性选择 position 1 或 6，反向题翻转。
    """
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


class PerformanceTest(TestCase):
    """各接口与核心算法的性能测试。

    时间断言阈值 = 目标值 × 3（补偿测试环境与生产环境的性能差异）。
    """

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        cache.clear()
        # 清空速率限制内存计数器，避免跨用例累积
        common_middleware._local_rate_limit_store.clear()
        self.answers = build_answers('INTJ')
        self.questions_meta = list(
            Question.objects
            .order_by('display_order')
            .values(
                'id', 'dimension', 'facet', 'facet_order',
                'pole_a', 'pole_b', 'is_reverse', 'display_order',
            )
        )
        # 预创建一条已支付测评 + 订单，供结果页 / 报告页测试使用
        self.assessment = Assessment.objects.create(
            uuid='perf-uuid-001',
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
        self.paid_order = Order.objects.create(
            order_no='CT-PERF-PAID-001',
            uuid='perf-uuid-001',
            assessment_id=self.assessment.id,
            amount=Decimal('2.99'),
            status='paid',
            expires_at=timezone.now() + timedelta(minutes=15),
            paid_at=timezone.now(),
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _post_score(self, uuid='perf-score-uuid', answers=None):
        """发送 POST /api/score/ 请求。"""
        payload = {
            'answers': answers if answers is not None else self.answers,
            'uuid': uuid,
        }
        return self.client.post(
            '/api/score/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    # ------------------------------------------------------------------
    # 页面响应时间
    # ------------------------------------------------------------------

    def test_home_page_response_time(self):
        """GET / → ≤ 500ms（阈值 1500ms）。"""
        start = time.perf_counter()
        response = self.client.get('/')
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1500, f'首页响应耗时 {elapsed:.1f}ms 超过 1500ms')

    def test_assessment_page_response_time(self):
        """GET /assessment/ → ≤ 500ms（阈值 1500ms）。"""
        start = time.perf_counter()
        response = self.client.get('/assessment/')
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1500,
                        f'测评页响应耗时 {elapsed:.1f}ms 超过 1500ms')

    def test_result_page_response_time(self):
        """GET /result/{uuid}/ → ≤ 500ms（阈值 1500ms）。"""
        url = f'/result/{self.assessment.uuid}/'
        start = time.perf_counter()
        response = self.client.get(url)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1500,
                        f'结果页响应耗时 {elapsed:.1f}ms 超过 1500ms')

    def test_report_page_response_time(self):
        """GET /report/{order_no}/ → ≤ 1000ms（阈值 3000ms）。"""
        url = f'/report/{self.paid_order.order_no}/'
        start = time.perf_counter()
        response = self.client.get(url)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 3000,
                        f'报告页响应耗时 {elapsed:.1f}ms 超过 3000ms')

    # ------------------------------------------------------------------
    # API 响应时间
    # ------------------------------------------------------------------

    def test_score_api_response_time(self):
        """POST /api/score/ → ≤ 1000ms（阈值 3000ms，48 题提交）。"""
        start = time.perf_counter()
        response = self._post_score(uuid='perf-score-api-uuid')
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200, response.content[:500])
        self.assertLess(elapsed, 3000,
                        f'评分接口耗时 {elapsed:.1f}ms 超过 3000ms')

    def test_completed_count_response_time(self):
        """GET /api/stats/completed-count/ → ≤ 200ms（阈值 600ms）。"""
        start = time.perf_counter()
        response = self.client.get('/api/stats/completed-count/')
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 600,
                        f'已完成人数接口耗时 {elapsed:.1f}ms 超过 600ms')

    def test_track_api_response_time(self):
        """POST /api/track/ → ≤ 200ms（阈值 600ms）。"""
        payload = {
            'event_name': 'assessment_start',
            'uuid': 'perf-track-uuid',
            'event_data': {'page': 'home'},
        }
        start = time.perf_counter()
        response = self.client.post(
            '/api/track/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        elapsed = (time.perf_counter() - start) * 1000

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 600,
                        f'埋点接口耗时 {elapsed:.1f}ms 超过 600ms')

    # ------------------------------------------------------------------
    # 核心算法性能
    # ------------------------------------------------------------------

    def test_scoring_engine_performance(self):
        """ScoringEngine.calculate() → ≤ 100ms（阈值 300ms）。"""
        engine = ScoringEngine()
        # 预热（避免首次导入开销影响测量）
        engine.calculate(self.answers, self.questions_meta)

        start = time.perf_counter()
        engine.calculate(self.answers, self.questions_meta)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed, 300,
                        f'评分引擎耗时 {elapsed:.2f}ms 超过 300ms')

    def test_career_matcher_performance(self):
        """CareerMatcher.match() → ≤ 200ms（阈值 600ms）。"""
        matcher = CareerMatcher()
        dimensions = {
            'EI': {'percentage': 20, 'label': 'I'},
            'SN': {'percentage': 25, 'label': 'N'},
            'TF': {'percentage': 75, 'label': 'T'},
            'JP': {'percentage': 70, 'label': 'J'},
        }
        # 预热
        matcher.match('INTJ', dimensions)

        start = time.perf_counter()
        matcher.match('INTJ', dimensions)
        elapsed = (time.perf_counter() - start) * 1000

        self.assertLess(elapsed, 600,
                        f'职业匹配引擎耗时 {elapsed:.2f}ms 超过 600ms')

    # ------------------------------------------------------------------
    # 页面体积
    # ------------------------------------------------------------------

    def test_page_size(self):
        """首页 HTML 大小 → ≤ 100KB（不含图片）。"""
        response = self.client.get('/')
        size_bytes = len(response.content)
        size_kb = size_bytes / 1024

        self.assertEqual(response.status_code, 200)
        self.assertLess(size_bytes, 100 * 1024,
                        f'首页 HTML 体积 {size_kb:.1f}KB 超过 100KB')


class ConcurrentScoreTest(TransactionTestCase):
    """并发评分请求测试。

    使用 ``TransactionTestCase`` 以确保 fixtures 数据被真实提交到数据库，
    从而各工作线程的独立数据库连接能够读取到题目 / 类型 / 职业数据。

    注意：开发 / 测试环境使用 SQLite 共享缓存内存库，其表级锁在高并发写入时
    可能抛出 "database table is locked"（生产环境为 MySQL，无此问题）。因此
    每个工作线程在发起请求前会为自身连接设置 ``busy_timeout``，并对偶发的
    500 响应进行有限次重试，以验证评分接口在并发压力下的逻辑正确性。
    """

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']
    CONCURRENT_COUNT = 10
    MAX_RETRIES = 6
    RETRY_DELAY = 0.08  # 秒

    def setUp(self):
        cache.clear()
        common_middleware._local_rate_limit_store.clear()
        self.answers = build_answers('INTJ')

    def test_concurrent_score_requests(self):
        """10 个并发评分请求 → 全部成功（status 200）。"""

        def submit(idx):
            """单个线程提交评分请求（含 SQLite 锁重试）。"""
            from django.db import connection

            # 为当前线程的连接设置 busy_timeout，缓解共享缓存表锁
            try:
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA busy_timeout = 30000')
            except Exception:
                pass

            client = Client()
            payload = {
                'answers': self.answers,
                'uuid': f'perf-concurrent-{idx}',
            }
            body = json.dumps(payload)
            for attempt in range(self.MAX_RETRIES):
                response = client.post(
                    '/api/score/',
                    data=body,
                    content_type='application/json',
                )
                if response.status_code == 200:
                    return response
                # SQLite 共享缓存表锁 → 短暂退避后重试
                time.sleep(self.RETRY_DELAY)
            return response

        statuses = []
        with ThreadPoolExecutor(max_workers=self.CONCURRENT_COUNT) as executor:
            futures = [
                executor.submit(submit, i)
                for i in range(self.CONCURRENT_COUNT)
            ]
            for future in as_completed(futures):
                response = future.result()
                statuses.append(response.status_code)

        self.assertEqual(len(statuses), self.CONCURRENT_COUNT)
        failed = [s for s in statuses if s != 200]
        self.assertEqual(
            failed, [],
            f'并发评分请求存在失败: {failed}（共 {len(statuses)} 个）',
        )
        # 验证并发创建的测评记录数正确
        created = Assessment.objects.filter(
            uuid__startswith='perf-concurrent-'
        ).count()
        self.assertEqual(created, self.CONCURRENT_COUNT)
