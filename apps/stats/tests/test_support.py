"""阶段六支撑功能测试。

覆盖 stats / assessment / common 模块提供的支撑性 API：
1. FeedbackView          —— 用户反馈（职业反馈 / 报告评分 / 报告文字 / 防重复）
2. CustomerServiceView   —— 客服留言
3. TrackView             —— 前端埋点（低频入库 / 高频入 Redis / 批量上限）
4. CompletedCountView    —— 已完成测评人数
5. HistoryView           —— 测评历史（最多 3 条）
6. ExceptionMiddleware   —— API 异常返回 JSON / 非 API 放行

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md 阶段六
"""

import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, TestCase

from apps.assessment.models import Assessment
from apps.common import middleware as common_middleware
from apps.common.middleware import ExceptionMiddleware
from apps.stats.models import (
    CustomerServiceMessage,
    Feedback,
    TrackingEvent,
)


def _reset_stores():
    """每个用例前清空缓存与限流内存计数，保证互不影响。"""
    cache.clear()
    # RateLimitMiddleware 在非 Redis 环境下使用模块级内存字典
    common_middleware._local_rate_limit_store.clear()


class FeedbackViewTest(TestCase):
    """/api/feedback/ 端点测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json']

    def setUp(self):
        _reset_stores()
        self.assessment = Assessment.objects.create(
            uuid='fb-uuid-001',
            mbti_type_code='INTJ',
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _post(self, payload):
        return self.client.post(
            '/api/feedback/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def _career_payload(self, **overrides):
        payload = {
            'uuid': 'fb-uuid-001',
            'feedback_type': 'career_mismatch',
            'assessment_id': self.assessment.id,
            'mbti_type': 'INTJ',
            'career_id': 'C001',
        }
        payload.update(overrides)
        return payload

    # ------------------------------------------------------------------
    # 正常用例
    # ------------------------------------------------------------------

    def test_feedback_career_mismatch(self):
        """正常提交职业反馈 → 200 success。"""
        response = self._post(self._career_payload())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(Feedback.objects.count(), 1)
        fb = Feedback.objects.first()
        self.assertEqual(fb.feedback_type, 'career_mismatch')
        self.assertEqual(fb.career_id, 'C001')
        self.assertEqual(fb.assessment_id, self.assessment.id)

    def test_feedback_report_rating(self):
        """报告评分 up → 200 success。"""
        payload = {
            'uuid': 'fb-uuid-001',
            'feedback_type': 'report_rating',
            'mbti_type': 'INTJ',
            'rating': 'up',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        fb = Feedback.objects.get(feedback_type='report_rating')
        self.assertEqual(fb.rating, 'up')

    def test_feedback_report_text(self):
        """报告文字反馈 → 200 success。"""
        payload = {
            'uuid': 'fb-uuid-001',
            'feedback_type': 'report_text',
            'mbti_type': 'INTJ',
            'content': '报告很有帮助，谢谢！',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        fb = Feedback.objects.get(feedback_type='report_text')
        self.assertEqual(fb.content, '报告很有帮助，谢谢！')

    # ------------------------------------------------------------------
    # 异常用例
    # ------------------------------------------------------------------

    def test_feedback_duplicate_prevention(self):
        """同一 uuid + assessment_id + type 重复提交 → 400。"""
        # 首次提交成功
        first = self._post(self._career_payload())
        self.assertEqual(first.status_code, 200)

        # 再次提交相同组合 → 防重复
        second = self._post(self._career_payload())
        self.assertEqual(second.status_code, 400)
        data = second.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'duplicate_feedback')
        # 仍只有一条记录
        self.assertEqual(Feedback.objects.count(), 1)

    def test_feedback_missing_uuid(self):
        """缺少 uuid → 400。"""
        payload = self._career_payload()
        payload.pop('uuid')
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'missing_uuid')

    def test_feedback_invalid_type(self):
        """无效反馈类型 → 400。"""
        response = self._post(self._career_payload(feedback_type='unknown_type'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_type')

    def test_feedback_text_too_long(self):
        """文字反馈超过 200 字 → 400。"""
        payload = {
            'uuid': 'fb-uuid-001',
            'feedback_type': 'report_text',
            'mbti_type': 'INTJ',
            'content': '测' * 201,
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'content_too_long')

    def test_feedback_missing_career_id(self):
        """职业反馈缺少 career_id → 400。"""
        payload = self._career_payload()
        payload.pop('career_id')
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'missing_career_id')

    def test_feedback_invalid_rating(self):
        """无效评分 → 400。"""
        payload = {
            'uuid': 'fb-uuid-001',
            'feedback_type': 'report_rating',
            'mbti_type': 'INTJ',
            'rating': 'medium',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_rating')


class CustomerServiceViewTest(TestCase):
    """/api/customer-service/ 端点测试套件。"""

    def setUp(self):
        _reset_stores()

    def _post(self, payload):
        return self.client.post(
            '/api/customer-service/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_customer_service_normal(self):
        """正常留言 → 200 success。"""
        payload = {
            'message': '我支付后看不到报告，订单号 CT-001',
            'contact': 'wechat123',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(CustomerServiceMessage.objects.count(), 1)
        msg = CustomerServiceMessage.objects.first()
        self.assertEqual(msg.status, 'pending')
        self.assertEqual(msg.contact, 'wechat123')

    def test_customer_service_empty_message(self):
        """空消息 → 400。"""
        response = self._post({'message': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'empty_message')
        # 纯空白同样视为空
        response_ws = self._post({'message': '   '})
        self.assertEqual(response_ws.status_code, 400)

    def test_customer_service_too_long(self):
        """消息超过 500 字 → 400。"""
        payload = {'message': '问' * 501}
        response = self._post(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'message_too_long')

    def test_customer_service_with_order(self):
        """带订单号留言 → 200 success。"""
        payload = {
            'message': '退款咨询',
            'order_no': 'CT-ORDER-002',
            'uuid': 'cs-uuid-001',
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, 200)
        msg = CustomerServiceMessage.objects.get()
        self.assertEqual(msg.order_no, 'CT-ORDER-002')
        self.assertEqual(msg.uuid, 'cs-uuid-001')


class TrackViewTest(TestCase):
    """/api/track/ 端点测试套件。"""

    # 低频事件名（直接入库，不依赖 Redis）
    LOW_FREQ_EVENT = 'career_click'

    def setUp(self):
        _reset_stores()

    def _post(self, payload):
        return self.client.post(
            '/api/track/',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def _event(self, name=None, uuid='track-uuid-001'):
        return {
            'event_name': name or self.LOW_FREQ_EVENT,
            'uuid': uuid,
            'event_data': {'source': 'test'},
        }

    def test_track_single_event(self):
        """单个低频事件 → 200，tracking_event 表有记录。"""
        before = TrackingEvent.objects.count()
        response = self._post(self._event())

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['low_frequency_saved'], 1)
        self.assertEqual(TrackingEvent.objects.count(), before + 1)
        evt = TrackingEvent.objects.first()
        self.assertEqual(evt.event_name, self.LOW_FREQ_EVENT)
        self.assertEqual(evt.uuid, 'track-uuid-001')

    def test_track_batch_events(self):
        """批量 5 个事件 → 200，全部入库。"""
        events = [self._event(uuid='track-batch-001') for _ in range(5)]
        response = self._post(events)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['low_frequency_saved'], 5)
        self.assertEqual(TrackingEvent.objects.count(), 5)

    def test_track_empty(self):
        """空事件列表 → 400。"""
        response = self._post([])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'empty_events')

    def test_track_too_many(self):
        """超过 50 个事件 → 400。"""
        events = [self._event() for _ in range(51)]
        response = self._post(events)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'too_many_events')
        self.assertEqual(TrackingEvent.objects.count(), 0)


class CompletedCountViewTest(TestCase):
    """/api/stats/completed-count/ 端点测试套件。"""

    def setUp(self):
        _reset_stores()

    def test_completed_count(self):
        """GET 返回 {"count": N}，值取自缓存。"""
        # 缓存为空时返回 0
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'count': 0})

        # 写入缓存后应返回对应值
        cache.set('stats:completed_count', 42, None)
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'count': 42})


class HistoryViewTest(TestCase):
    """/api/history/<uuid>/ 端点测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json']

    def setUp(self):
        _reset_stores()

    def _create(self, uuid, mbti='INTJ'):
        return Assessment.objects.create(
            uuid=uuid,
            mbti_type_code=mbti,
            dimension_scores={'EI': {'label': 'I'}},
            facet_scores=[],
            consistency_flag='normal',
        )

    def test_history_returns_max_3(self):
        """创建 5 条测评记录，API 最多返回 3 条。"""
        for _ in range(5):
            self._create('hist-uuid-001')

        response = self.client.get('/api/history/hist-uuid-001/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('history', data)
        self.assertEqual(len(data['history']), 3)
        # 每条记录均含必要字段
        for record in data['history']:
            self.assertIn('assessment_id', record)
            self.assertIn('mbti_type', record)
            self.assertIn('dimensions', record)
            self.assertIn('created_at', record)

    def test_history_empty(self):
        """不存在的 uuid 返回空列表。"""
        response = self.client.get('/api/history/not-exist-uuid/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'history': []})


class ExceptionMiddlewareTest(TestCase):
    """ExceptionMiddleware 行为测试套件。"""

    def setUp(self):
        _reset_stores()
        self.factory = RequestFactory()

    @patch('apps.stats.views.CompletedCountView.get')
    def test_api_error_returns_json(self, mock_get):
        """API 路径抛出异常 → 返回 JSON 而非 HTML。"""
        mock_get.side_effect = ValueError('boom')

        response = self.client.get('/api/stats/completed-count/')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'internal_error')

    def test_non_api_path_falls_through(self):
        """非 API 路径不被中间件拦截（process_exception 返回 None）。"""
        request = self.factory.get('/some/non-api/page/')
        mw = ExceptionMiddleware(lambda req: None)

        result = mw.process_exception(request, ValueError('boom'))

        self.assertIsNone(result)
