"""Views for the stats app.

Provides the homepage, about, help, settings and report pages together
with a set of small JSON APIs used by the front-end (completed-count,
feedback, customer-service and analytics tracking).
"""

import json
import logging

from django.core.cache import cache
from django.views import View
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import Feedback, CustomerServiceMessage, TrackingEvent

logger = logging.getLogger(__name__)

# 高频事件存 Redis list，低频事件直接入库
HIGH_FREQUENCY_EVENTS = frozenset({
    'page_view',
    'assessment_answer',
    'assessment_pause',
    'assessment_resume',
    'report_scroll',
})

# Redis list key 前缀
TRACK_REDIS_PREFIX = 'track:'
TRACK_REDIS_MAX_LENGTH = 500  # 每个 uuid 最多存 500 条高频事件


class HomeView(View):
    """Homepage of the site.

    Renders the landing page ``pages/home.html`` with the number of
    completed assessments read from Redis (key ``stats:completed_count``).

    Also parses URL parameters for share referral (ref / type / name).
    """

    def get(self, request, *args, **kwargs):
        completed_count = cache.get('stats:completed_count', 0)
        context = {
            'completed_count': completed_count,
        }
        # 分享回流参数
        ref_uuid = request.GET.get('ref', '')
        ref_type = request.GET.get('type', '')
        ref_name = request.GET.get('name', '')
        if ref_type:
            context['ref_type'] = ref_type
            context['ref_name'] = ref_name or ''
            context['ref_uuid'] = ref_uuid
        return render(request, 'pages/home.html', context)


class AboutView(View):
    """About page.

    Renders ``pages/about.html`` if it exists, otherwise falls back to
    ``pages/home.html``.
    """

    def get(self, request, *args, **kwargs):
        from django.template.loader import select_template
        template = select_template(['pages/about.html', 'pages/home.html'])
        return HttpResponse(template.render({}, request))


class HelpView(View):
    """Help / FAQ page.

    Renders ``pages/help.html`` with FAQ data for search functionality.
    """

    # 8 条 FAQ 数据
    FAQ_DATA = [
        {
            'id': 1,
            'question': '测评是免费的吗？需要注册吗？',
            'answer': '完全免费，无需注册。你可以直接打开网页开始测评，48 道题目约需 6-8 分钟。基础报告（性格类型 + 四维度 + 职业推荐）也完全免费。仅深度报告需要 2.99 元解锁，但这完全是可选的。',
            'keywords': '免费 注册 费用 价格',
        },
        {
            'id': 2,
            'question': '测评结果准确吗？',
            'answer': '我们的测评基于 MBTI 人格理论，48 道题目经过心理学量表验证。虽然没有哪种性格测评能做到 100% 准确，但 MBTI 在职业匹配领域有广泛的应用和参考价值。建议你在自然、放松的状态下答题，以获得最贴近真实的结果。',
            'keywords': '准确 准确性 可信 科学',
        },
        {
            'id': 3,
            'question': '推荐的职业不匹配怎么办？',
            'answer': '职业推荐基于你的 MBTI 类型匹配，仅供参考。如果觉得推荐方向完全不对，可以点击职业旁的"推荐不准"按钮反馈，我们会持续优化匹配算法。同时建议重新测评 2-3 次确认类型稳定性。',
            'keywords': '职业 推荐 不准 不匹配 偏差',
        },
        {
            'id': 4,
            'question': '深度报告包含什么内容？',
            'answer': '深度报告包含 12 个章节的详细解析：性格概览、核心特质、思维方式、情感模式、社交风格、工作方式、领导风格、职业匹配、人际关系、成长建议、潜在盲区和行动计划。每章配有实际案例和可操作的建议。',
            'keywords': '深度 报告 内容 章节 解析',
        },
        {
            'id': 5,
            'question': '支付后看不到报告怎么办？',
            'answer': '支付成功后页面会自动跳转到深度报告。如果未跳转，请等待 2 分钟（前端轮询确认支付状态）。如仍未显示，请刷新页面。若问题持续，请通过帮助中心底部的客服联系方式告诉我们你的订单号，我们会尽快处理。',
            'keywords': '支付 看不到 报告 失败 订单',
        },
        {
            'id': 6,
            'question': '如何重新查看已购买的报告？',
            'answer': '在设置页面或报告页底部，使用"找回报告"功能，输入你的设备标识即可恢复已购买报告的访问权限。报告绑定你的浏览器设备，永久有效。',
            'keywords': '找回 报告 查看 恢复 已购',
        },
        {
            'id': 7,
            'question': '如何清除我的测评数据？',
            'answer': '在设置页面（点击页面底部"设置"链接），你可以查看和清除所有存储在浏览器本地的测评数据，包括测评进度、结果和报告访问权限。清除后不可恢复，请谨慎操作。',
            'keywords': '清除 数据 删除 隐私 设置',
        },
        {
            'id': 8,
            'question': '如何联系客服？',
            'answer': '你可以通过以下方式联系我们：邮箱 support@zhitan.com，微信 zhitan_support。工作日 9:00-18:00 内回复。也可以在帮助中心页面提交在线留言，我们会尽快处理。',
            'keywords': '联系 客服 邮箱 微信 留言',
        },
    ]

    def get(self, request, *args, **kwargs):
        context = {'faq_list': self.FAQ_DATA}
        return render(request, 'pages/help.html', context)


class SettingsView(View):
    """Settings page.

    Renders ``pages/settings.html`` with localStorage key descriptions
    for the data clearing feature.
    """

    # localStorage 键名规范
    STORAGE_KEYS_INFO = [
        {'key': 'ct_uuid', 'desc': '匿名用户标识', 'ttl': '永久', 'can_clear': True},
        {'key': 'ct_assessment_progress', 'desc': '测评答题进度', 'ttl': '7 天过期', 'can_clear': True},
        {'key': 'ct_last_result', 'desc': '最近测评结果', 'ttl': '会话级', 'can_clear': True},
        {'key': 'ct_paid_reports', 'desc': '已购买报告列表', 'ttl': '90 天标记过期', 'can_clear': True},
        {'key': 'ct_referrer_type', 'desc': '分享来源类型', 'ttl': '会话级', 'can_clear': True},
        {'key': 'ct_settings', 'desc': '用户偏好设置', 'ttl': '永久', 'can_clear': True},
    ]

    def get(self, request, *args, **kwargs):
        context = {'storage_keys_info': self.STORAGE_KEYS_INFO}
        return render(request, 'pages/settings.html', context)


class CompletedCountView(View):
    """Return the number of completed assessments.

    Reads from Redis key ``stats:completed_count`` (TTL 1 hour).
    Returns ``{"count": N}``.
    """

    def get(self, request, *args, **kwargs):
        count = cache.get('stats:completed_count', 0)
        return JsonResponse({"count": count})


class FeedbackView(View):
    """Receive user feedback submitted from the front-end.

    Supports four feedback types:
    - career_mismatch: 方向完全不对
    - career_partial: 部分匹配
    - report_rating: 报告评分（up/down）
    - report_text: 报告文字反馈

    Prevents duplicate submissions (same uuid + assessment_id + feedback_type).
    """

    ALLOWED_TYPES = frozenset({
        'career_mismatch',
        'career_partial',
        'report_rating',
        'report_text',
    })

    ALLOWED_RATINGS = frozenset({'up', 'down'})

    def post(self, request, *args, **kwargs):
        # 解析请求体
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'success': False, 'code': 'invalid_params', 'message': '请求体格式错误'},
                status=400,
            )

        uuid = data.get('uuid', '')
        feedback_type = data.get('feedback_type', '')
        assessment_id = data.get('assessment_id')
        mbti_type = data.get('mbti_type', '')
        career_id = data.get('career_id', '')
        rating = data.get('rating', '')
        content = data.get('content', '')
        order_no = data.get('order_no', '')

        # 参数校验
        if not uuid:
            return JsonResponse(
                {'success': False, 'code': 'missing_uuid', 'message': '缺少 uuid 参数'},
                status=400,
            )

        if feedback_type not in self.ALLOWED_TYPES:
            return JsonResponse(
                {'success': False, 'code': 'invalid_type',
                 'message': f'不支持的反馈类型: {feedback_type}'},
                status=400,
            )

        # 报告评分必须有 rating
        if feedback_type == 'report_rating' and rating not in self.ALLOWED_RATINGS:
            return JsonResponse(
                {'success': False, 'code': 'invalid_rating',
                 'message': '评分必须为 up 或 down'},
                status=400,
            )

        # 文字反馈限 200 字
        if feedback_type == 'report_text':
            if not content:
                return JsonResponse(
                    {'success': False, 'code': 'empty_content',
                     'message': '反馈内容不能为空'},
                    status=400,
                )
            if len(content) > 200:
                return JsonResponse(
                    {'success': False, 'code': 'content_too_long',
                     'message': '反馈内容不能超过 200 字'},
                    status=400,
                )

        # 职业反馈必须有 career_id
        if feedback_type in ('career_mismatch', 'career_partial') and not career_id:
            return JsonResponse(
                {'success': False, 'code': 'missing_career_id',
                 'message': '职业反馈需要提供 career_id'},
                status=400,
            )

        # 防重复提交（同一 uuid + assessment_id + feedback_type）
        query = Feedback.objects.filter(
            uuid=uuid,
            feedback_type=feedback_type,
        )
        if assessment_id:
            query = query.filter(assessment_id=assessment_id)
        if career_id:
            query = query.filter(career_id=career_id)

        if query.exists():
            return JsonResponse(
                {'success': False, 'code': 'duplicate_feedback',
                 'message': '你已提交过相同类型的反馈'},
                status=400,
            )

        # 写入数据库
        Feedback.objects.create(
            uuid=uuid,
            assessment_id=assessment_id,
            order_no=order_no or None,
            mbti_type=mbti_type,
            feedback_type=feedback_type,
            career_id=career_id or None,
            rating=rating if rating in self.ALLOWED_RATINGS else None,
            content=content or None,
        )

        logger.info('用户反馈: uuid=%s, type=%s', uuid[:8], feedback_type)

        return JsonResponse({'success': True, 'message': '反馈提交成功'})


class CustomerServiceView(View):
    """Customer-service contact endpoint.

    Accepts a message form with:
    - message (required, max 500 chars)
    - contact (optional, wechat or phone)
    - order_no (optional)
    - uuid (optional)

    Writes to the customer_service_message table.
    """

    MAX_MESSAGE_LENGTH = 500

    def post(self, request, *args, **kwargs):
        # 解析请求体
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'success': False, 'code': 'invalid_params', 'message': '请求体格式错误'},
                status=400,
            )

        message = data.get('message', '').strip()
        contact = data.get('contact', '').strip()
        order_no = data.get('order_no', '').strip()
        uuid = data.get('uuid', '').strip()

        # 参数校验
        if not message:
            return JsonResponse(
                {'success': False, 'code': 'empty_message',
                 'message': '问题描述不能为空'},
                status=400,
            )

        if len(message) > self.MAX_MESSAGE_LENGTH:
            return JsonResponse(
                {'success': False, 'code': 'message_too_long',
                 'message': f'问题描述不能超过 {self.MAX_MESSAGE_LENGTH} 字'},
                status=400,
            )

        # 写入数据库
        CustomerServiceMessage.objects.create(
            uuid=uuid or None,
            contact=contact or None,
            message=message,
            order_no=order_no or None,
            status='pending',
        )

        logger.info('客服留言: uuid=%s, message_len=%d',
                    uuid[:8] if uuid else 'anonymous', len(message))

        return JsonResponse({'success': True, 'message': '留言已提交，我们会尽快处理'})


class TrackView(View):
    """Analytics tracking endpoint.

    Receives front-end tracking events. High-frequency events are stored
    in Redis list ``track:{uuid}``, low-frequency events are written
    directly to the tracking_event table.
    """

    # 低频事件直接入库
    LOW_FREQUENCY_EVENTS = frozenset({
        'assessment_start',
        'assessment_submit',
        'result_view',
        'career_click',
        'career_feedback',
        'share_click',
        'share_success',
        'payment_click',
        'payment_success',
        'payment_fail',
        'report_view',
        'report_feedback',
        'referral_landing',
    })

    def post(self, request, *args, **kwargs):
        # 解析请求体（支持批量上报）
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'success': False, 'code': 'invalid_params', 'message': '请求体格式错误'},
                status=400,
            )

        # 支持单条和批量两种格式
        events = data if isinstance(data, list) else [data]

        if not events:
            return JsonResponse(
                {'success': False, 'code': 'empty_events', 'message': '事件列表为空'},
                status=400,
            )

        if len(events) > 50:
            return JsonResponse(
                {'success': False, 'code': 'too_many_events',
                 'message': '单次最多上报 50 个事件'},
                status=400,
            )

        low_freq_events = []
        high_freq_count = 0

        for event in events:
            event_name = event.get('event_name', '')
            user_uuid = event.get('uuid', '')
            event_data = event.get('event_data', {})

            if not event_name or not user_uuid:
                continue

            if event_name in self.LOW_FREQUENCY_EVENTS:
                low_freq_events.append(TrackingEvent(
                    uuid=user_uuid,
                    event_name=event_name,
                    event_data=event_data,
                ))
            else:
                # 高频事件存 Redis list
                redis_key = f'{TRACK_REDIS_PREFIX}{user_uuid}'
                cache.lpush(redis_key, json.dumps({
                    'event_name': event_name,
                    'event_data': event_data,
                    'timestamp': timezone.now().isoformat(),
                }, ensure_ascii=False))
                # 限制 list 长度
                cache.ltrim(redis_key, 0, TRACK_REDIS_MAX_LENGTH - 1)
                cache.expire(redis_key, 86400)  # 24 小时过期
                high_freq_count += 1

        # 批量写入低频事件
        if low_freq_events:
            TrackingEvent.objects.bulk_create(low_freq_events)

        logger.debug('埋点上报: %d 低频入库, %d 高频入Redis',
                     len(low_freq_events), high_freq_count)

        return JsonResponse({
            'success': True,
            'low_frequency_saved': len(low_freq_events),
            'high_frequency_cached': high_freq_count,
        })
