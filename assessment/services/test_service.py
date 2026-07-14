# 画己职测 — 测评测试服务
#
# 本模块负责测评流程相关的业务逻辑：
#   1. 获取/缓存题目列表
#   2. 验证答题数据完整性
#   3. 加密存储答题数据
#   4. 调用计分引擎计算结果
#   5. 查询测评结果

import json
import logging

from django.conf import settings

from assessment.scoring.engine import calculate_assessment_result
from assessment.scoring.schemas import AssessmentSubmission, UserAnswerLog
from assessment.scoring.validity import _calculate_duration_seconds
from assessment.services.result_service import (
    build_free_card_data,
    get_archetype_config,
    get_questions_for_scoring,
)
from common.constants import QUESTION_COUNT
from common.utils import encrypt_data, mask_answers, mask_token

logger = logging.getLogger(__name__)


def submit_assessment(
    submission_data: dict[str, object],
    device_fingerprint: str,
    session_token: str,
) -> dict[str, object]:
    """测评提交流程编排。

    流程：
      1. 验证答案数量（80题）
      2. 从数据库加载题目配置
      3. 调用计分引擎 calculate_assessment_result()
      4. AES-256 加密 answers 数据
      5. 存储 Assessment 记录
      6. 返回结构化结果

    :param submission_data: 提交数据字典（含 answers, started_at, submitted_at）
    :param device_fingerprint: 设备指纹
    :param session_token: 会话令牌
    :return: 结构化测评结果字典
    :raises ValueError: 答案数量不正确或计分失败
    """
    answers_raw: list[dict[str, int]] = submission_data.get("answers", [])
    started_at: str = str(submission_data.get("started_at", ""))
    submitted_at: str = str(submission_data.get("submitted_at", ""))

    # 1. 验证答案数量
    if len(answers_raw) != QUESTION_COUNT:
        logger.error(
            "答案数量校验失败 | expected=%d | got=%d",
            QUESTION_COUNT,
            len(answers_raw),
        )
        raise ValueError(f"答案数量不正确：期望 {QUESTION_COUNT} 题，实际 {len(answers_raw)} 题")

    logger.info(
        "测评提交开始 | session=%s | device=%s | answers=%s",
        mask_token(session_token),
        device_fingerprint,
        mask_answers(len(answers_raw)),
    )

    # 2. 从数据库加载题目配置
    questions = get_questions_for_scoring()

    if len(questions) != QUESTION_COUNT:
        logger.error(
            "题库数量异常 | expected=%d | got=%d",
            QUESTION_COUNT,
            len(questions),
        )
        raise ValueError(f"题库数量异常：期望 {QUESTION_COUNT} 题，实际 {len(questions)} 题")

    # 3. 构建 Pydantic 提交模型
    user_answers: list[UserAnswerLog] = [
        UserAnswerLog(
            question_id=str(a["question_id"]),
            scale_value=a["scale_value"],
            response_duration_ms=a.get("response_duration_ms", 0),
            modification_count=0,
            answered_at=submitted_at,
        )
        for a in answers_raw
    ]

    submission: AssessmentSubmission = AssessmentSubmission(
        session_token=session_token,
        device_fingerprint=device_fingerprint,
        answers=user_answers,
        started_at=started_at,
        submitted_at=submitted_at,
        questions=questions,
    )

    # 4. 调用计分引擎
    result = calculate_assessment_result(submission, questions)

    # 5. AES-256 加密答题数据
    aes_key: str = getattr(settings, "AES_ENCRYPTION_KEY", "change-me-to-a-32-byte-aes-key")
    answers_json: str = json.dumps(answers_raw, ensure_ascii=False)
    encrypted_answers: str = encrypt_data(answers_json, aes_key)

    # 6. 计算 OCEAN 百分位用于存储
    ocean_percentile_map: dict[str, float] = {s.dimension.value: s.percentile for s in result.ocean_scores}

    # 7. 计算答题耗时
    duration_seconds: int = _calculate_duration_seconds(started_at, submitted_at)

    # 8. 存储 Assessment 记录
    from assessment.models import Assessment

    assessment: Assessment = Assessment.objects.create(
        session_token=session_token,
        device_fingerprint=device_fingerprint,
        answers=encrypted_answers,
        archetype_id=result.archetype_id,
        archetype_name=result.archetype_name,
        riasec_code=result.riasec_code,
        o_score=ocean_percentile_map.get("O"),
        c_score=ocean_percentile_map.get("C"),
        e_score=ocean_percentile_map.get("E"),
        a_score=ocean_percentile_map.get("A"),
        n_score=ocean_percentile_map.get("N"),
        confidence=result.confidence,
        is_valid=result.validity.is_valid,
        duration_seconds=duration_seconds,
    )

    logger.info(
        "测评记录存储完成 | assessment_id=%d | archetype=%s | riasec=%s | confidence=%.2f",
        assessment.id,
        result.archetype_name,
        result.riasec_code,
        result.confidence,
    )

    # 9. 构建人格认证卡数据
    archetype_config: dict[str, object] = get_archetype_config(result.archetype_id)
    color_spectrum_dict: dict[str, object] = result.color_spectrum.model_dump(mode="json")
    free_card_data: dict[str, object] = build_free_card_data(
        archetype_config,
        result.riasec_code,
        color_spectrum_dict,
    )

    # 10. 填充 free_card_data 到结果
    result.free_card_data = free_card_data

    # 11. 转换为 dict 返回
    result_dict: dict[str, object] = {
        "session_token": session_token,
        "assessment_id": assessment.id,
        "archetype_id": result.archetype_id,
        "archetype_name": result.archetype_name,
        "archetype_slogan": result.archetype_slogan,
        "riasec_code": result.riasec_code,
        "color_spectrum": result.color_spectrum.model_dump(mode="json"),
        "ocean_scores": [
            {
                "dimension": s.dimension.value,
                "raw_score": s.raw_score,
                "percentile": s.percentile,
                "is_high": s.is_high,
                "level": s.level,
            }
            for s in result.ocean_scores
        ],
        "riasec_scores": [
            {
                "type": s.type.value,
                "raw_score": s.raw_score,
                "rank": s.rank,
                "is_top_three": s.is_top_three,
            }
            for s in result.riasec_scores
        ],
        "confidence": result.confidence,
        "is_valid": result.validity.is_valid,
        "free_card_data": free_card_data,
    }

    logger.info("测评提交流程完成 | session=%s", mask_token(session_token))
    return result_dict


def get_assessment_result(session_token: str) -> dict[str, object] | None:
    """查询测评结果。

    根据 session_token 查询 Assessment 记录，重建结构化结果。

    :param session_token: 会话令牌
    :return: 结构化测评结果字典，不存在时返回 None
    """
    from assessment.models import Assessment

    try:
        # 使用 .only() 限制查询字段，避免拉取加密答题数据等大字段
        # 同一 session_token 可能有多条记录，取最新一条
        assessment: Assessment = Assessment.objects.only(
            "id",
            "session_token",
            "archetype_id",
            "archetype_name",
            "riasec_code",
            "o_score",
            "c_score",
            "e_score",
            "a_score",
            "n_score",
            "confidence",
            "is_valid",
        ).filter(session_token=session_token).latest("id")
    except Assessment.DoesNotExist:
        logger.warning("测评记录不存在 | session=%s", mask_token(session_token))
        return None

    # 获取原型配置
    archetype_config: dict[str, object] = get_archetype_config(assessment.archetype_id)

    # 重建 OCEAN 分数
    ocean_data: list[tuple[str, float | None]] = [
        ("O", assessment.o_score),
        ("C", assessment.c_score),
        ("E", assessment.e_score),
        ("A", assessment.a_score),
        ("N", assessment.n_score),
    ]
    ocean_scores: list[dict[str, object]] = []
    for dim, score in ocean_data:
        percentile: float = float(score) if score is not None else 0.0
        ocean_scores.append(
            {
                "dimension": dim,
                "raw_score": 0,
                "percentile": percentile,
                "is_high": percentile > 50.0,
                "level": _percentile_to_level(percentile),
            }
        )

    # 重建色彩光谱
    from assessment.scoring.color_spectrum import generate_color_spectrum
    from assessment.scoring.schemas import OCEANDimension, OCEANDimensionScore

    # 从数据库百分位构建 OCEANDimensionScore 列表
    ocean_dim_data: list[tuple[OCEANDimension, float]] = [
        (OCEANDimension.O, float(assessment.o_score) if assessment.o_score else 0.0),
        (OCEANDimension.C, float(assessment.c_score) if assessment.c_score else 0.0),
        (OCEANDimension.E, float(assessment.e_score) if assessment.e_score else 0.0),
        (OCEANDimension.A, float(assessment.a_score) if assessment.a_score else 0.0),
        (OCEANDimension.N, float(assessment.n_score) if assessment.n_score else 0.0),
    ]
    ocean_score_objs: list[OCEANDimensionScore] = []
    for dim, percentile in ocean_dim_data:
        level: int = _percentile_to_level(percentile)
        ocean_score_objs.append(
            OCEANDimensionScore(
                dimension=dim,
                raw_score=0,
                percentile=percentile,
                is_high=percentile > 50.0,
                level=level,
                t_score=0.0,
            )
        )
    color_spectrum = generate_color_spectrum(ocean_score_objs)
    color_spectrum_dict: dict[str, object] = color_spectrum.model_dump(mode="json")

    # 构建人格认证卡数据
    free_card_data: dict[str, object] = build_free_card_data(
        archetype_config,
        assessment.riasec_code or "",
        color_spectrum_dict,
    )

    result_dict: dict[str, object] = {
        "session_token": session_token,
        "assessment_id": assessment.id,
        "archetype_id": assessment.archetype_id,
        "archetype_name": assessment.archetype_name,
        "archetype_slogan": archetype_config.get("archetype_slogan", ""),
        "riasec_code": assessment.riasec_code,
        "color_spectrum": color_spectrum_dict,
        "ocean_scores": ocean_scores,
        "riasec_scores": [],  # 查询时无法重建 RIASEC 排名，需从加密数据恢复
        "confidence": assessment.confidence,
        "is_valid": assessment.is_valid,
        "free_card_data": free_card_data,
    }

    logger.info(
        "测评结果查询完成 | session=%s | archetype=%s",
        mask_token(session_token),
        assessment.archetype_name,
    )
    return result_dict


def _percentile_to_level(percentile: float) -> int:
    """将百分位转换为色深档位（1-5）。

    :param percentile: 百分位 0-100
    :return: 色深档位 1-5
    """
    if percentile < 20.0:
        return 1
    elif percentile < 40.0:
        return 2
    elif percentile < 60.0:
        return 3
    elif percentile < 80.0:
        return 4
    else:
        return 5
