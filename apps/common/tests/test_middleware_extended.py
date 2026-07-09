"""ExceptionMiddleware / RateLimitMiddleware 扩展测试。

补充覆盖 apps/common/middleware.py 中尚未覆盖的分支：
1. ExceptionMiddleware —— /api/ 路径抛异常 / 非 /api/ 路径放行
2. APIError 异常 -> 对应状态码
3. RateLimitMiddleware —— 正常请求不被限流

关联文档：TECH_DESIGN.md / IMPLEMENTATION_PLAN.md
"""

import json
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from apps.common import middleware as common_middleware
from apps.common.middleware import ExceptionMiddleware, RateLimitMiddleware
from apps.common.responses import APIError, api_error_response


def _reset_stores():
    """每个用例前清空缓存与限流内存计数。"""
    common_middleware._local_rate_limit_store.clear()


class ExceptionMiddlewareExtendedTest(TestCase):
    """ExceptionMiddleware 扩展测试套件。"""

    def setUp(self):
        _reset_stores()
        self.factory = RequestFactory()

    @patch('apps.stats.views.CompletedCountView.get')
    def test_exception_middleware_api_path(self, mock_get):
        """/api/ 路径抛异常 -> JSON 响应 500。"""
        mock_get.side_effect = ValueError('test boom')
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'internal_error')

    def test_exception_middleware_non_api(self):
        """非 /api/ 路径 -> 返回 None（放行）。"""
        request = self.factory.get('/some/page/')
        mw = ExceptionMiddleware(lambda req: None)
        result = mw.process_exception(request, ValueError('test'))
        self.assertIsNone(result)

    @patch('apps.stats.views.CompletedCountView.get')
    def test_api_error_response(self, mock_get):
        """APIError 异常 -> 对应状态码。"""
        mock_get.side_effect = APIError(
            code='custom_error',
            message='自定义错误',
            http_status=422,
        )
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'custom_error')
        self.assertEqual(data['message'], '自定义错误')

    @patch('apps.stats.views.CompletedCountView.get')
    def test_api_error_with_extra(self, mock_get):
        """APIError 带 extra 数据 -> 响应含 data 字段。"""
        mock_get.side_effect = APIError(
            code='validation_error',
            message='参数校验失败',
            http_status=400,
            extra={'field': 'uuid'},
        )
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['code'], 'validation_error')
        self.assertEqual(data['data'], {'field': 'uuid'})

    def test_api_error_response_direct(self):
        """直接调用 api_error_response 验证输出。"""
        error = APIError(
            code='not_found',
            message='资源不存在',
            http_status=404,
        )
        response = api_error_response(error)
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'not_found')

    def test_exception_middleware_call_normal(self):
        """正常请求不被 ExceptionMiddleware 拦截。"""
        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse('ok')
        mw = ExceptionMiddleware(get_response)
        request = self.factory.get('/api/test/')
        response = mw(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_exception_middleware_call_catches_exception(self):
        """__call__ 方法捕获异常并返回 JSON 响应（/api/ 路径）。"""
        def get_response(request):
            raise ValueError('call boom')
        mw = ExceptionMiddleware(get_response)
        request = self.factory.get('/api/test/')
        response = mw(request)
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'internal_error')

    def test_exception_middleware_call_catches_api_error(self):
        """__call__ 方法捕获 APIError 并返回对应状态码。"""
        def get_response(request):
            raise APIError(code='forbidden', message='禁止访问', http_status=403)
        mw = ExceptionMiddleware(get_response)
        request = self.factory.get('/api/test/')
        response = mw(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertEqual(data['code'], 'forbidden')


class RateLimitMiddlewareExtendedTest(TestCase):
    """RateLimitMiddleware 扩展测试套件。"""

    def setUp(self):
        _reset_stores()
        self.factory = RequestFactory()

    def test_rate_limit_allows_normal(self):
        """正常请求不被限流。"""
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 200)
        # 响应头含限流信息
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)

    def test_rate_limit_non_api_path(self):
        """非 API 路径不走限流逻辑。"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_rate_limit_exceeds_limit(self):
        """超过限流阈值 -> 429。"""
        # 发送超过限制的请求
        for _ in range(common_middleware.RATE_LIMIT_MAX_REQUESTS):
            response = self.client.get('/api/stats/completed-count/')
            self.assertEqual(response.status_code, 200)

        # 下一次请求应被限流
        response = self.client.get('/api/stats/completed-count/')
        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['code'], 'rate_limit_exceeded')

    def test_rate_limit_client_ip_from_forwarded(self):
        """X-Forwarded-For 头提取客户端 IP。"""
        request = self.factory.get(
            '/api/test/',
            HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8',
        )
        ip = RateLimitMiddleware._get_client_ip(request)
        self.assertEqual(ip, '1.2.3.4')

    def test_rate_limit_client_ip_from_remote_addr(self):
        """无 X-Forwarded-For 时使用 REMOTE_ADDR。"""
        request = self.factory.get('/api/test/', REMOTE_ADDR='9.8.7.6')
        ip = RateLimitMiddleware._get_client_ip(request)
        self.assertEqual(ip, '9.8.7.6')

    def test_rate_limit_redis_path(self):
        """Redis 后端的限流逻辑（mock Redis pipeline）。"""
        from unittest.mock import MagicMock
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [0, True, 1, True]
        mock_redis.pipeline.return_value = mock_pipe

        mw = RateLimitMiddleware(lambda req: None)
        mw._redis_client = mock_redis

        allowed, remaining, reset_at = mw._check_rate_limit('1.2.3.4')
        self.assertTrue(allowed)
        self.assertGreater(remaining, 0)
        self.assertGreater(reset_at, 0)
        # 验证 pipeline 被调用
        mock_redis.pipeline.assert_called_once()

    def test_rate_limit_redis_exceeds(self):
        """Redis 后端超过限流阈值 -> not allowed。"""
        from unittest.mock import MagicMock
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        # zcard 返回超过限制的数量
        mock_pipe.execute.return_value = [0, True, 100, True]
        mock_redis.pipeline.return_value = mock_pipe

        mw = RateLimitMiddleware(lambda req: None)
        mw._redis_client = mock_redis

        allowed, remaining, reset_at = mw._check_rate_limit('1.2.3.4')
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)

    def test_get_redis_client_with_redis_backend(self):
        """Redis 后端配置时返回 Redis 客户端。"""
        import sys
        from unittest.mock import MagicMock
        from django.test import override_settings

        redis_caches = {
            'default': {'BACKEND': 'django_redis.cache.RedisCache'}
        }

        # Mock django_redis module
        mock_redis_module = MagicMock()
        mock_redis_module.get_redis_connection.return_value = 'mock_redis_client'

        with override_settings(CACHES=redis_caches), \
             patch.dict(sys.modules, {'django_redis': mock_redis_module}):
            client = RateLimitMiddleware._get_redis_client()
            self.assertEqual(client, 'mock_redis_client')

    def test_get_redis_client_without_redis_backend(self):
        """非 Redis 后端但 django_redis 已安装时返回 None。"""
        import sys
        from unittest.mock import MagicMock
        from django.test import override_settings

        locmem_caches = {
            'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
        }

        # Mock django_redis module so import succeeds, but backend is not redis
        mock_redis_module = MagicMock()

        with override_settings(CACHES=locmem_caches), \
             patch.dict(sys.modules, {'django_redis': mock_redis_module}):
            client = RateLimitMiddleware._get_redis_client()
            self.assertIsNone(client)
