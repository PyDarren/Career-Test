"""Views for the assessment app.

Handles the assessment (questionnaire) page, score submission, result
rendering and history lookup.
"""

import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from .models import Assessment, Question
from .scoring import ScoringEngine

logger = logging.getLogger(__name__)

# 评分结果缓存 key 前缀和 TTL
SCORE_CACHE_PREFIX = 'score:'
SCORE_CACHE_TTL = 3600  # 1 小时


class AssessmentView(View):
    """Assessment (questionnaire) page.

    Renders ``pages/assessment.html`` with 48 questions loaded from
    the database, ordered by ``display_order``.
    """

    def get(self, request, *args, **kwargs):
        questions = (
            Question.objects
            .order_by('display_order')
            .values(
                'id',
                'question_order',
                'dimension',
                'facet',
                'facet_order',
                'text_a',
                'text_b',
                'pole_a',
                'pole_b',
                'is_reverse',
                'display_order',
            )
        )
        questions_list = list(questions)
        context = {
            'questions_json': json.dumps(questions_list, ensure_ascii=False),
            'total_questions': len(questions_list),
        }
        return render(request, 'pages/assessment.html', context)


class ScoreView(View):
    """Score submission endpoint.

    Accepts the user's 48 answers, validates input, runs the scoring
    engine, queries MBTI type configuration, matches careers, creates
    an Assessment record, and returns the complete result as JSON.

    Security:
    - Validates answers length (must be 48)
    - Validates each position is in [1, 6]
    - Validates Referer header (reject non-local origins)
    - Uses Redis cache for scoring results (TTL 1 hour)
    """

    # 允许的 Referer 前缀（开发环境）
    ALLOWED_REFERERS = ('http://127.0.0.1:', 'http://localhost:', 'https://careertest')

    def post(self, request, *args, **kwargs):
        # 1. Referer 校验
        referer = request.headers.get('Referer', '')
        if referer and not any(referer.startswith(prefix) for prefix in self.ALLOWED_REFERERS):
            return JsonResponse(
                {'error': '非法请求来源'},
                status=403,
            )

        # 2. 解析请求体
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse(
                {'error': '请求体格式错误，应为 JSON'},
                status=400,
            )

        answers = data.get('answers', [])
        user_uuid = data.get('uuid', '')

        # 3. 参数校验
        if not user_uuid:
            return JsonResponse(
                {'error': '缺少 uuid 参数'},
                status=400,
            )

        if not isinstance(answers, list) or len(answers) != 48:
            return JsonResponse(
                {'error': f'答案数量不正确，应为 48 题，实际 {len(answers) if isinstance(answers, list) else 0} 题'},
                status=400,
            )

        for ans in answers:
            position = ans.get('position', 0)
            if not isinstance(position, int) or position < 1 or position > 6:
                return JsonResponse(
                    {'error': f'刻度位置必须在 1-6 范围内，收到 {position}'},
                    status=400,
                )

        # 4. 加载题目元数据
        questions = list(
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

        # 5. 评分计算（带缓存）
        engine = ScoringEngine()

        # 生成答案指纹用于缓存
        answers_fingerprint = engine._generate_fingerprint(answers)
        cache_key = f'{SCORE_CACHE_PREFIX}{answers_fingerprint}'

        # 尝试从缓存读取
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            result = cached_result
            logger.debug('评分结果命中缓存: %s', cache_key)
        else:
            result = engine.calculate(answers, questions)
            cache.set(cache_key, result, SCORE_CACHE_TTL)
            logger.debug('评分结果已缓存: %s', cache_key)

        # 6. 查询 MBTI 类型配置
        from apps.mbti_types.models import MBTIType

        mbti_type_code = result['mbti_type']
        try:
            mbti_type = MBTIType.objects.get(type_code=mbti_type_code)
        except MBTIType.DoesNotExist:
            logger.error('MBTI 类型不存在: %s', mbti_type_code)
            return JsonResponse(
                {'error': f'类型配置不存在: {mbti_type_code}'},
                status=500,
            )

        # 7. 职业匹配
        from apps.careers.matching import CareerMatcher

        matcher = CareerMatcher()
        careers = matcher.match(mbti_type_code, result['dimensions'])

        # 8. 创建测评记录（缓存命中时也创建新记录）
        assessment = Assessment.objects.create(
            uuid=user_uuid,
            mbti_type_code=mbti_type_code,
            dimension_scores=result['dimensions'],
            facet_scores=result['facets'],
            consistency_flag=result['consistency_flag'],
        )

        # 9. 更新已完成人数（Redis 计数器）
        completed_count_key = 'stats:completed_count'
        try:
            cache.incr(completed_count_key)
        except ValueError:
            # key 不存在时初始化
            cache.set(completed_count_key, 1, None)

        # 10. 返回完整结果
        return JsonResponse({
            'mbti_type': mbti_type_code,
            'role_group': mbti_type.role_group,
            'dimensions': result['dimensions'],
            'facets': result['facets'],
            'cognitive_stack': result['cognitive_stack'],
            'consistency_flag': result['consistency_flag'],
            'type_info': mbti_type.to_dict(),
            'recommended_careers': careers,
            'assessment_id': assessment.id,
            'uuid': user_uuid,
        })


class ResultView(View):
    """Assessment result page.

    Renders ``pages/result.html``. When a ``uuid`` is provided (via the
    URL path), the specific result for that assessment is looked up.
    Loads the assessment record and MBTI type configuration for display.
    """

    def get(self, request, uuid=None, *args, **kwargs):
        context = {}

        if uuid:
            # 查找最近的测评记录
            assessment = (
                Assessment.objects
                .filter(uuid=uuid)
                .order_by('-created_at')
                .first()
            )

            if assessment:
                from apps.mbti_types.models import MBTIType

                try:
                    type_config = MBTIType.objects.get(
                        type_code=assessment.mbti_type_code
                    )
                    context['type_config'] = type_config
                    context['assessment'] = assessment
                    context['dimensions'] = assessment.dimension_scores
                    context['facets'] = assessment.facet_scores

                    # 职业推荐
                    from apps.careers.matching import CareerMatcher
                    matcher = CareerMatcher()
                    careers = matcher.match(
                        assessment.mbti_type_code,
                        assessment.dimension_scores,
                    )
                    context['careers'] = careers

                    # 检查是否已购买报告
                    from apps.payment.models import Order
                    paid_order = Order.objects.filter(
                        assessment_id=assessment.id, status='paid'
                    ).first()
                    context['has_paid'] = paid_order is not None
                    if paid_order:
                        context['report_url'] = f'/report/{paid_order.order_no}/'

                except MBTIType.DoesNotExist:
                    context['error'] = '类型配置不存在'

            context['uuid'] = uuid

        return render(request, 'pages/result.html', context)


class HistoryView(View):
    """Return the assessment history for a given ``uuid``.

    Returns at most 3 recent assessments, ordered by ``created_at``
    descending.
    """

    def get(self, request, uuid, *args, **kwargs):
        assessments = (
            Assessment.objects
            .filter(uuid=uuid)
            .order_by('-created_at')[:3]
            .values('id', 'mbti_type_code', 'dimension_scores', 'created_at')
        )
        history = []
        for a in assessments:
            history.append({
                'assessment_id': a['id'],
                'mbti_type': a['mbti_type_code'],
                'dimensions': a['dimension_scores'],
                'created_at': a['created_at'].isoformat() if a['created_at'] else None,
            })
        return JsonResponse({'history': history})
