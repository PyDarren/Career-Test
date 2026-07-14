# 画己职测 — 测评结果服务
#
# 本模块负责测评结果相关的业务逻辑：
#   1. 构建人格认证卡渲染数据（free_card_data）
#   2. 从 Redis 缓存或数据库获取原型配置
#   3. 获取全部 80 题配置（计分引擎用）
#   4. 缓存热门结果

import logging

from django.core.cache import cache

from assessment.scoring.schemas import (
    DimensionPrefix,
    Question,
    QuestionModule,
    QuestionType,
)
from common.constants import CACHE_TTL, COLOR_SPECTRUM

logger = logging.getLogger(__name__)

# Redis 缓存 key 前缀
QUESTIONS_CACHE_KEY: str = "assessment:questions:all:v1"
ARCHETYPE_CACHE_KEY_TEMPLATE: str = "personality:archetype:{archetype_id}:v1"


def _convert_django_question_to_pydantic(django_question: object) -> Question:
    """将 Django Question 模型转换为 Pydantic Question。

    :param django_question: Django Question 模型实例
    :return: Pydantic Question 模型
    """
    # 维度前缀转换
    prefix_str: str = django_question.dimension_prefix
    try:
        dimension_prefix: DimensionPrefix = DimensionPrefix(prefix_str)
    except ValueError:
        logger.warning("未知维度前缀 | prefix=%s", prefix_str)
        dimension_prefix = DimensionPrefix.BO  # 降级处理

    # 题目模块：根据 Django question_type 映射
    django_q_type: str = django_question.question_type
    if django_q_type == "ocean":
        module: QuestionModule = QuestionModule.OCEAN
    elif django_q_type == "riasec":
        module = QuestionModule.RIASEC
    else:
        # 效度题根据维度前缀判断模块
        if prefix_str.startswith("B"):
            module = QuestionModule.OCEAN
        else:
            module = QuestionModule.RIASEC

    # 题目类型：根据 Django question_type 和 is_reverse 映射
    if django_q_type == "validity":
        question_type: QuestionType = QuestionType.LIE_SCALE
    elif django_question.is_reverse:
        question_type = QuestionType.REVERSE
    else:
        question_type = QuestionType.NORMAL

    return Question(
        question_id=str(django_question.id),
        statement=django_question.question_text,
        dimension_prefix=dimension_prefix,
        module=module,
        question_type=question_type,
        is_reverse=django_question.is_reverse,
        pair_id=None,
        is_active=django_question.is_active,
    )


def get_questions_for_scoring() -> list[Question]:
    """获取全部 80 题配置（计分引擎用）。

    优先从 Redis 缓存读取，缓存未命中或 Redis 不可用时查询数据库。

    :return: Question Pydantic 模型列表
    """
    # 尝试从缓存读取
    try:
        cached: list[dict[str, object]] | None = cache.get(QUESTIONS_CACHE_KEY)
        if cached is not None:
            logger.debug("题库缓存命中 | key=%s | count=%d", QUESTIONS_CACHE_KEY, len(cached))
            return [Question(**item) for item in cached]
    except Exception as e:
        logger.warning("题库缓存读取失败，降级为数据库查询 | error=%s", e)

    # 缓存未命中，查询数据库
    from assessment.models import Question as QuestionModel

    db_questions = QuestionModel.objects.filter(is_active=True).order_by("order")

    questions_data: list[dict[str, object]] = []
    questions: list[Question] = []

    for q in db_questions:
        pydantic_q: Question = _convert_django_question_to_pydantic(q)
        questions.append(pydantic_q)
        questions_data.append(pydantic_q.model_dump(mode="json"))

    # 尝试写入缓存
    try:
        cache.set(QUESTIONS_CACHE_KEY, questions_data, CACHE_TTL)
        logger.info(
            "题库缓存写入 | key=%s | count=%d | ttl=%d",
            QUESTIONS_CACHE_KEY,
            len(questions_data),
            CACHE_TTL,
        )
    except Exception as e:
        logger.warning("题库缓存写入失败 | error=%s", e)

    return questions


def get_archetype_config(archetype_id: int) -> dict[str, object]:
    """从 Redis 缓存或数据库获取原型配置。

    :param archetype_id: 原型 ID
    :return: 原型配置字典
    :raises PersonalityArchetype.DoesNotExist: 原型不存在
    """
    cache_key: str = ARCHETYPE_CACHE_KEY_TEMPLATE.format(archetype_id=archetype_id)

    # 尝试从缓存读取
    try:
        cached: dict[str, object] | None = cache.get(cache_key)
        if cached is not None:
            logger.debug("原型配置缓存命中 | key=%s", cache_key)
            return cached
    except Exception as e:
        logger.warning("原型配置缓存读取失败，降级为数据库查询 | error=%s", e)

    # 缓存未命中，查询数据库
    from personality.models import PersonalityArchetype

    archetype: PersonalityArchetype = PersonalityArchetype.objects.get(archetype_id=archetype_id)

    config: dict[str, object] = {
        "archetype_id": archetype.archetype_id,
        "archetype_code": archetype.archetype_code,
        "archetype_name": archetype.archetype_name,
        "archetype_slogan": archetype.archetype_slogan,
        "rarity": archetype.rarity,
        "rarity_percentage": archetype.rarity_percentage,
        "famous_people": list(archetype.famous_people),
        "best_partners": list(archetype.best_partners),
        "career_directions": list(archetype.career_directions),
        "o_range": archetype.o_range,
        "c_range": archetype.c_range,
        "e_range": archetype.e_range,
        "a_range": archetype.a_range,
        "n_range": archetype.n_range,
        "mascot_url": archetype.mascot_url,
    }

    # 尝试写入缓存
    try:
        cache.set(cache_key, config, CACHE_TTL)
        logger.info(
            "原型配置缓存写入 | key=%s | archetype_id=%d | ttl=%d",
            cache_key,
            archetype_id,
            CACHE_TTL,
        )
    except Exception as e:
        logger.warning("原型配置缓存写入失败 | error=%s", e)

    return config


def build_free_card_data(
    archetype_config: dict[str, object],
    riasec_code: str,
    color_spectrum: dict[str, object],
) -> dict[str, object]:
    """构建人格认证卡渲染数据。

    包含：画像名、RIASEC码、色彩光谱条、口号、稀有度、名人、最佳搭子。

    :param archetype_config: 原型配置字典
    :param riasec_code: RIASEC 码
    :param color_spectrum: 色彩光谱数据（dict 或 ColorSpectrum.model_dump()）
    :return: 人格认证卡渲染数据
    """
    # 提取色彩光谱条数据（用于前端渲染渐变条）
    spectrum_bar: list[dict[str, object]] = []
    dots: list[dict[str, object]] = color_spectrum.get("dots", [])
    for dot in dots:
        spectrum_bar.append(
            {
                "dimension": dot.get("dimension", ""),
                "color": dot.get("color", COLOR_SPECTRUM.get(str(dot.get("dimension", "")), "#888888")),
                "level": dot.get("level", 0),
                "percentile": dot.get("percentile", 0.0),
            }
        )

    card_data: dict[str, object] = {
        "archetype_name": archetype_config.get("archetype_name", ""),
        "archetype_slogan": archetype_config.get("archetype_slogan", ""),
        "riasec_code": riasec_code,
        "rarity": archetype_config.get("rarity", ""),
        "rarity_percentage": archetype_config.get("rarity_percentage", 0.0),
        "famous_people": archetype_config.get("famous_people", []),
        "best_partners": archetype_config.get("best_partners", []),
        "mascot_url": archetype_config.get("mascot_url", ""),
        "spectrum_bar": spectrum_bar,
    }

    logger.debug(
        "人格认证卡数据构建完成 | archetype=%s | riasec_code=%s",
        card_data["archetype_name"],
        riasec_code,
    )
    return card_data
