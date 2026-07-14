"""画己职测 — 各维度计算器。

本模块包含两个核心计算函数：
  - calculate_ocean_scores: 大五人格五维度（O/C/E/A/N）得分计算
  - calculate_riasec_scores: RIASEC 六类型得分计算与排名

OCEAN 计分规则：
  1. 筛选 dimension_prefix 以 "B" 开头的题目（50 题）
  2. 正向题直接取 scale_value，反向题翻转（1<->5, 2<->4, 3<->3）
  3. 每维度 10 题求和（范围 10-50）
  4. 用常模数据转换为百分位（线性映射）
  5. 百分位 > 50 为高分(is_high=True)
  6. 色深档位：0-20%=1, 20-40%=2, 40-60%=3, 60-80%=4, 80-100%=5
  7. T 分数：t_score = 50 + (raw - 30) / 10 * 10（均值 30，标准差 10）

RIASEC 计分规则：
  1. 筛选 dimension_prefix 以 "R" 开头的题目（30 题）
  2. 全部正向计分
  3. 每类型 5 题求和（范围 5-25）
  4. 按总分降序排名（并列时按 R>I>A>S>E>C 字母顺序优先）
  5. 取前三名 is_top_three=True

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出
  - 所有 80 题均参与计分（效度题 lie_scale/consistency 同时作为维度题计分，
    以保证「每维度 10 题」「每类型 5 题」的题量约束）
"""

from __future__ import annotations

import logging

from assessment.scoring.normalizer import (
    percentile_to_level,
    raw_to_percentile,
)
from assessment.scoring.schemas import (
    PREFIX_TO_OCEAN,
    PREFIX_TO_RIASEC,
    OCEANDimension,
    OCEANDimensionScore,
    Question,
    RIASECDimensionScore,
    RIASECType,
    UserAnswerLog,
)

logger: logging.Logger = logging.getLogger(__name__)

# OCEAN 维度在结果中的固定输出顺序
_OCEAN_ORDER: list[OCEANDimension] = [
    OCEANDimension.O,
    OCEANDimension.C,
    OCEANDimension.E,
    OCEANDimension.A,
    OCEANDimension.N,
]

# RIASEC 并列时的优先级顺序（R>I>A>S>E>C）
_RIASEC_PRIORITY: list[RIASECType] = [
    RIASECType.R,
    RIASECType.I,
    RIASECType.A,
    RIASECType.S,
    RIASECType.E,
    RIASECType.C,
]

# T 分数计算常量（简化版）
_T_MEAN: float = 30.0  # 原始分均值
_T_SD: float = 10.0  # 原始分标准差
_T_BASE: float = 50.0  # T 分数基准


def _build_answer_map(answers: list[UserAnswerLog]) -> dict[str, int]:
    """构建 题号 -> 量表值 的映射（量表值取 int）。"""
    return {ans.question_id: int(ans.scale_value) for ans in answers}


def _reverse_value(value: int) -> int:
    """反向计分翻转：1<->5, 2<->4, 3<->3（即 6 - value）。"""
    return 6 - value


def calculate_ocean_scores(
    answers: list[UserAnswerLog],
    questions: list[Question],
    norm_data: dict,
) -> list[OCEANDimensionScore]:
    """计算大五人格五维度得分。

    参数：
        answers: 用户作答列表
        questions: 题库列表
        norm_data: 常模数据（normalizer.get_norm_data() 返回值）

    返回：
        五维度得分列表（顺序固定为 O/C/E/A/N）
    """
    answer_map: dict[str, int] = _build_answer_map(answers)

    # 按维度聚合原始分：dimension -> raw_score
    raw_by_dim: dict[OCEANDimension, int] = {dim: 0 for dim in _OCEAN_ORDER}

    for q in questions:
        prefix: str = q.dimension_prefix.value
        if not prefix.startswith("B"):
            continue
        dim: OCEANDimension | None = PREFIX_TO_OCEAN.get(prefix)
        if dim is None:
            logger.warning("未知 OCEAN 前缀 %s，跳过", prefix)
            continue
        value: int | None = answer_map.get(q.question_id)
        if value is None:
            logger.warning("题目 %s 缺少作答，按 0 计入", q.question_id)
            value = 0
        # 反向题翻转
        if q.is_reverse:
            value = _reverse_value(value)
        raw_by_dim[dim] += value

    # 转换为 OCEANDimensionScore
    results: list[OCEANDimensionScore] = []
    for dim in _OCEAN_ORDER:
        raw_score: int = raw_by_dim[dim]
        percentile: float = raw_to_percentile(raw_score, dim.value, norm_data)
        is_high: bool = percentile > 50.0
        level: int = percentile_to_level(percentile)
        t_score: float = _T_BASE + (raw_score - _T_MEAN) / _T_SD * 10.0
        results.append(
            OCEANDimensionScore(
                dimension=dim,
                raw_score=raw_score,
                percentile=percentile,
                is_high=is_high,
                level=level,
                t_score=t_score,
            )
        )
    return results


def calculate_riasec_scores(
    answers: list[UserAnswerLog],
    questions: list[Question],
) -> list[RIASECDimensionScore]:
    """计算 RIASEC 六类型得分并排名。

    参数：
        answers: 用户作答列表
        questions: 题库列表

    返回：
        六类型得分列表（按 R/I/A/S/E/C 顺序输出，rank 字段反映排名）
    """
    answer_map: dict[str, int] = _build_answer_map(answers)

    # 按类型聚合原始分
    raw_by_type: dict[RIASECType, int] = {t: 0 for t in _RIASEC_PRIORITY}

    for q in questions:
        prefix: str = q.dimension_prefix.value
        if not prefix.startswith("R") or len(prefix) < 2:
            continue
        rtype: RIASECType | None = PREFIX_TO_RIASEC.get(prefix)
        if rtype is None:
            logger.warning("未知 RIASEC 前缀 %s，跳过", prefix)
            continue
        value: int | None = answer_map.get(q.question_id)
        if value is None:
            logger.warning("题目 %s 缺少作答，按 0 计入", q.question_id)
            value = 0
        # RIASEC 全部正向计分，不翻转
        raw_by_type[rtype] += value

    # 排名：按总分降序，并列时按 R>I>A>S>E>C 优先
    # 先按优先级建立稳定顺序，再按分数降序排序（Python sort 稳定，相同分数保持原顺序）
    ordered_types: list[RIASECType] = list(_RIASEC_PRIORITY)
    sorted_types: list[RIASECType] = sorted(ordered_types, key=lambda t: raw_by_type[t], reverse=True)

    # 计算 rank（处理并列：相同分数相同 rank）
    rank_by_type: dict[RIASECType, int] = {}
    prev_score: int | None = None
    prev_rank: int = 0
    for idx, rtype in enumerate(sorted_types, start=1):
        score: int = raw_by_type[rtype]
        if prev_score is not None and score == prev_score:
            rank_by_type[rtype] = prev_rank  # 并列，沿用前一名次
        else:
            rank_by_type[rtype] = idx
            prev_rank = idx
        prev_score = score

    # 按 R/I/A/S/E/C 固定顺序输出
    results: list[RIASECDimensionScore] = []
    for rtype in _RIASEC_PRIORITY:
        rank: int = rank_by_type[rtype]
        results.append(
            RIASECDimensionScore(
                type=rtype,
                raw_score=raw_by_type[rtype],
                rank=rank,
                is_top_three=(rank <= 3),
            )
        )
    return results


def generate_riasec_code(riasec_scores: list[RIASECDimensionScore]) -> str:
    """生成 3 字母 RIASEC 码（取前三，并列按 R>I>A>S>E>C 优先）。

    参数：
        riasec_scores: calculate_riasec_scores 的输出

    返回：
        3 字母 RIASEC 码（如 "IAS"）
    """
    # 按分数降序、并列按优先级 R>I>A>S>E>C 排序后取前三
    priority_index: dict[RIASECType, int] = {t: i for i, t in enumerate(_RIASEC_PRIORITY)}
    sorted_scores: list[RIASECDimensionScore] = sorted(
        riasec_scores,
        key=lambda s: (-s.raw_score, priority_index[s.type]),
    )
    top_three: list[RIASECType] = [s.type for s in sorted_scores[:3]]
    return "".join(t.value for t in top_three)
