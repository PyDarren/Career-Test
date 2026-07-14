"""画己职测 — 计分引擎入口。

本模块为测评计分引擎的统一入口，负责：
  1. 校验提交数据（答题数必须正好 80 题，否则抛出 ValueError）
  2. 调用 validity.check_validity 进行效度检测
  3. 调用 calculators.calculate_ocean_scores 计算 OCEAN 五维度得分
  4. 调用 calculators.calculate_riasec_scores 计算 RIASEC 六类型得分
  5. 调用 archetype_matcher.match_archetype 匹配人格原型
  6. 调用 color_spectrum.generate_color_spectrum 生成色彩光谱
  7. 生成 RIASEC 码（取前三，并列按 R>I>A>S>E>C）
  8. 组装 AssessmentResult（含 free_card_data / career_matches / deep_report_outline）

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出（computed_at 取自 submission.submitted_at）
"""

from __future__ import annotations

import logging

from assessment.scoring.archetype_matcher import (
    build_archetype_code,
    get_archetype_meta,
    match_archetype,
)
from assessment.scoring.calculators import (
    calculate_ocean_scores,
    calculate_riasec_scores,
    generate_riasec_code,
)
from assessment.scoring.color_spectrum import generate_color_spectrum
from assessment.scoring.normalizer import get_norm_data
from assessment.scoring.schemas import (
    AssessmentResult,
    AssessmentSubmission,
    CareerMatch,
    Question,
)
from assessment.scoring.validity import check_validity

logger: logging.Logger = logging.getLogger(__name__)

# 业务约束
_REQUIRED_ANSWER_COUNT: int = 80

# 深度报告 12 章固定结构
_DEEP_REPORT_CHAPTERS: list[dict[str, object]] = [
    {"chapter": 1, "title": "你的人格画像速览", "locked": False},
    {"chapter": 2, "title": "五维特质深度解读", "locked": True},
    {"chapter": 3, "title": "人格稀有度与人群分布", "locked": True},
    {"chapter": 4, "title": "同型名人与共同特质", "locked": True},
    {"chapter": 5, "title": "职业兴趣码深度解析", "locked": True},
    {"chapter": 6, "title": "推荐职业路径与岗位匹配", "locked": True},
    {"chapter": 7, "title": "职场优势与潜在盲区", "locked": True},
    {"chapter": 8, "title": "团队协作风格", "locked": True},
    {"chapter": 9, "title": "亲密关系模式", "locked": True},
    {"chapter": 10, "title": "最佳恋爱与协作对象", "locked": True},
    {"chapter": 11, "title": "成长建议与行动清单", "locked": True},
    {"chapter": 12, "title": "30 天自我提升计划", "locked": True},
]


def _build_career_matches(
    career_directions: list[str],
    archetype_name: str,
    riasec_code: str,
) -> list[CareerMatch]:
    """根据原型推荐职业方向生成职业匹配列表。

    参数：
        career_directions: 推荐职业方向名称列表
        archetype_name: 原型名
        riasec_code: 用户 RIASEC 码

    返回：
        CareerMatch 列表（按匹配分降序）
    """
    matches: list[CareerMatch] = []
    for idx, name in enumerate(career_directions):
        score: float = max(90.0 - idx * 5.0, 60.0)
        if score >= 80.0:
            level: str = "high"
        elif score >= 60.0:
            level = "medium"
        else:
            level = "low"
        matches.append(
            CareerMatch(
                career_id=f"DIR-{idx + 1:02d}",
                career_name=name,
                match_score=score,
                match_level=level,
                tags=[archetype_name],
                recommended_archetype=archetype_name,
                recommended_riasec=riasec_code,
            )
        )
    return matches


def _build_free_card_data(
    archetype_id: int,
    archetype_name: str,
    archetype_slogan: str,
    archetype_code: str,
    riasec_code: str,
    color_visual: str,
    rarity: str,
    rarity_percentage: float,
    mascot_url: str,
    famous_people: list[str],
    best_partners: list[int],
) -> dict[str, object]:
    """构建人格认证卡（免费）数据。"""
    return {
        "archetype_id": archetype_id,
        "archetype_name": archetype_name,
        "archetype_slogan": archetype_slogan,
        "archetype_code": archetype_code,
        "riasec_code": riasec_code,
        "color_spectrum": color_visual,
        "rarity": rarity,
        "rarity_percentage": rarity_percentage,
        "mascot_url": mascot_url,
        "famous_people": famous_people,
        "best_partners": best_partners,
        "full_label": f"{archetype_name} · {riasec_code}",
    }


def _build_deep_report_outline(archetype_name: str) -> dict[str, object]:
    """构建深度报告（付费）大纲。"""
    return {
        "archetype_name": archetype_name,
        "chapter_count": len(_DEEP_REPORT_CHAPTERS),
        "chapters": list(_DEEP_REPORT_CHAPTERS),
    }


def calculate_assessment_result(
    submission: AssessmentSubmission,
    questions: list[Question],
    archetype_configs: dict[int, dict] | None = None,
) -> AssessmentResult:
    """计分引擎入口函数。

    参数：
        submission: 用户测评提交数据
        questions: 题库列表（80 题）
        archetype_configs: 原型配置（可选，键为 archetype_id）

    返回：
        完整测评结果 AssessmentResult

    异常：
        ValueError: 答题数不等于 80
    """
    # 0. 答题数校验
    answer_count: int = len(submission.answers)
    if answer_count != _REQUIRED_ANSWER_COUNT:
        raise ValueError(f"答题数必须为 {_REQUIRED_ANSWER_COUNT}，实际为 {answer_count}")

    answers = submission.answers
    norm_data: dict = get_norm_data()

    # 1. 效度检测
    validity = check_validity(answers, questions)

    # 2. OCEAN 计分
    ocean_scores = calculate_ocean_scores(answers, questions, norm_data)

    # 3. RIASEC 计分
    riasec_scores = calculate_riasec_scores(answers, questions)

    # 4. 原型匹配
    archetype_id: int = match_archetype(ocean_scores)

    # 5. 色彩光谱
    color_spectrum = generate_color_spectrum(ocean_scores)

    # 6. RIASEC 码
    riasec_code: str = generate_riasec_code(riasec_scores)

    # 7. 维度组合码
    archetype_code: str = build_archetype_code(ocean_scores)

    # 8. 原型元数据
    meta: dict[str, object] = get_archetype_meta(archetype_id, archetype_configs)
    archetype_name: str = str(meta["archetype_name"])
    archetype_slogan: str = str(meta["archetype_slogan"])
    rarity: str = str(meta["rarity"])
    rarity_percentage: float = float(meta["rarity_percentage"])
    mascot_url: str = str(meta["mascot_url"])
    career_directions: list[str] = list(meta["career_directions"])  # type: ignore[arg-type]
    famous_people: list[str] = list(meta["famous_people"])  # type: ignore[arg-type]
    best_partners: list[int] = list(meta["best_partners"])  # type: ignore[arg-type]

    # 9. 职业推荐
    career_matches: list[CareerMatch] = _build_career_matches(career_directions, archetype_name, riasec_code)

    # 10. 免费卡片数据
    free_card_data: dict[str, object] = _build_free_card_data(
        archetype_id=archetype_id,
        archetype_name=archetype_name,
        archetype_slogan=archetype_slogan,
        archetype_code=archetype_code,
        riasec_code=riasec_code,
        color_visual=color_spectrum.visual,
        rarity=rarity,
        rarity_percentage=rarity_percentage,
        mascot_url=mascot_url,
        famous_people=famous_people,
        best_partners=best_partners,
    )

    # 11. 深度报告大纲
    deep_report_outline: dict[str, object] = _build_deep_report_outline(archetype_name)

    # 12. 组装结果（computed_at 取自提交时间，保证确定性）
    result: AssessmentResult = AssessmentResult(
        archetype_id=archetype_id,
        archetype_name=archetype_name,
        archetype_slogan=archetype_slogan,
        archetype_code=archetype_code,
        riasec_code=riasec_code,
        color_spectrum=color_spectrum,
        ocean_scores=ocean_scores,
        riasec_scores=riasec_scores,
        free_card_data=free_card_data,
        validity=validity,
        confidence=validity.confidence_score,
        career_matches=career_matches,
        deep_report_outline=deep_report_outline,
        computed_at=submission.submitted_at,
    )

    logger.info(
        "计分完成：archetype=%s(id=%d) riasec=%s confidence=%.2f valid=%s",
        archetype_name,
        archetype_id,
        riasec_code,
        validity.confidence_score,
        validity.is_valid,
    )
    return result
