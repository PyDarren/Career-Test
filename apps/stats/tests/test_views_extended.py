"""Stats views 扩展测试。

补充覆盖 apps/stats/views.py 中尚未覆盖的页面和 API：
1. HomeView —— GET /
2. AboutView —— GET /about/
3. HelpView —— GET /help/
4. SettingsView —— GET /settings/
5. CompletedCountView —— GET /api/stats/completed-count/
6. TrackView —— 高频事件（page_view）
7. FeedbackView —— 职业反馈

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from apps.assessment.models import Assessment
from apps.common import middleware as common_middleware
from apps.stats.models import Feedback, TrackingEvent


def _reset_stores():
    """每个用例前清空缓存与限流内存计数。"""
    cache.clear()
    common_middleware._local_rate_limit_store.clear()


class HomeViewExtendedTest(TestCase):
    """HomeView (/) 扩展测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_home_view(self):
        """GET / -> 200，含 completed_count。"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIsNotNone(context)
        self.assertIn('completed_count', context)

    def test_home_view_with_count(self):
        """缓存中有已完成人数时 HomeView 显示该值。"""
        cache.set('stats:completed_count', 99, None)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['completed_count'], 99)

    def test_home_view_ref_params(self):
        """带 ref 参数时 context 含分享回流信息。"""
        response = self.client.get('/?ref=uuid-123&type=wechat&name=test')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context.get('ref_type'), 'wechat')
        self.assertEqual(context.get('ref_name'), 'test')
        self.assertEqual(context.get('ref_uuid'), 'uuid-123')


class AboutViewExtendedTest(TestCase):
    """AboutView (/about/) 扩展测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_about_view(self):
        """GET /about/ -> 200。"""
        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)


class HelpViewExtendedTest(TestCase):
    """HelpView (/help/) 扩展测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_help_view(self):
        """GET /help/ -> 200，含 faq_list。"""
        response = self.client.get('/help/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIsNotNone(context)
        self.assertIn('faq_list', context)
        faq_list = context['faq_list']
        self.assertIsInstance(faq_list, list)
        self.assertEqual(len(faq_list), 8)
        # 验证 FAQ 数据结构
        first = faq_list[0]
        self.assertIn('id', first)
        self.assertIn('question', first)
        self.assertIn('answer', first)
        self.assertIn('keywords', first)


class SettingsViewExtendedTest(TestCase):
    """SettingsView (/settings/) 扩展测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_settings_view(self):
        """GET /settings/ -> 200，含 storage_keys_info。"""
        response = self.client.get('/settings/')
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIsNotNone(context)
        self.assertIn('storage_keys_info', context)
        keys_info = context['storage_keys_info']
        self.assertIsInstance(keys_info, list)
        self.assertGreater(len(keys_info), 0)
        first = keys_info[0]
        self.assertIn('key', first)
        self.assertIn('desc', first)
        self.assertIn('ttl', first)
        self.assertIn('can_clear', first)


class CompletedCountViewExtendedTest(TestCase):
    """CompletedCountView (/api/stats/completed-count/) 扩展测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_completed_count_view(self):
        """GET /api/stats/completed-count/ -> 200，返回 JSON。"""
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('count', data)
        self.assertEqual(data['count'], 0)

    def test_completed_count_view_with_cache(self):
        """缓存中有值时返回对应值。"""
        cache.set('stats:completed_count', 42, None)
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 42)


class TrackViewHighFrequencyTest(TestCase):
    """TrackView 高频事件测试套件。

    测试环境使用 LocMemCache，不支持 Redis 的 lpush/ltrim/expire。
    通过 mock 这些方法使高频事件路径可被测试。
    """

    def setUp(self):
        _reset_stores()

    def _post(self, payload):
        return self.client.post(
            '/api/track/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    @patch('apps.stats.views.cache')
    def test_track_view_high_frequency(self, mock_cache):
        """高频事件（page_view）-> 200。"""
        mock_cache.lpush.return_value = 1
        mock_cache.ltrim.return_value = None
        mock_cache.expire.return_value = True
        event = {
            'event_name': 'page_view',
            'uuid': 'track-hf-uuid-001',
            'event_data': {'page': '/'},
        }
        response = self._post(event)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['high_frequency_cached'], 1)
        self.assertEqual(data['low_frequency_saved'], 0)

    @patch('apps.stats.views.cache')
    def test_track_view_mixed_events(self, mock_cache):
        """混合高频和低频事件 -> 200。"""
        mock_cache.lpush.return_value = 1
        mock_cache.ltrim.return_value = None
        mock_cache.expire.return_value = True
        events = [
            {
                'event_name': 'page_view',
                'uuid': 'track-mixed-uuid',
                'event_data': {'page': '/'},
            },
            {
                'event_name': 'career_click',
                'uuid': 'track-mixed-uuid',
                'event_data': {'career_id': 'C001'},
            },
        ]
        response = self._post(events)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['high_frequency_cached'], 1)
        self.assertEqual(data['low_frequency_saved'], 1)
        self.assertEqual(TrackingEvent.objects.count(), 1)


class FeedbackViewCareerMismatchTest(TestCase):
    """FeedbackView 职业反馈测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json']

    def setUp(self):
        _reset_stores()
        self.assessment = Assessment.objects.create(
            uuid='fb-ext-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )

    def _post(self, payload):
        return self.client.post(
            '/api/feedback/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_feedback_view_career_mismatch(self):
        """正常提交职业反馈 -> 200。"""
        payload = {
            'uuid': 'fb-ext-uuid-001',
            'feedback_type': 'career_mismatch',
            'assessment_id': self.assessment.id,
            'mbti_type': 'INTJ',
            'career_id': 'C001',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Feedback.objects.count(), 1)
        fb = Feedback.objects.first()
        self.assertEqual(fb.feedback_type, 'career_mismatch')
        self.assertEqual(fb.career_id, 'C001')
