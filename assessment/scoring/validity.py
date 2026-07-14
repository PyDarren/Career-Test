"""画己职测 — 效度检测（Validity & Anti-Cheat）。

本模块负责检测测评结果的效度与置信度。MVP 阶段简化规则如下：

  1. 测谎题检测：lie_scale 类型的题目，如果 scale_value >= 4 触发
  2. 矛盾题对检测：consistency 类型的配对题（同一 pair_id），
     将反向题反向计分后与正向题比较，差异 > 2 触发
  3. 直线作答检测：如果 >70% 的题目选择相同值触发
  4. 响应时间异常：如果平均响应时间 < 1000ms 触发

置信度计算：初始 1.0，每触发一项扣 0.2。
is_valid：confidence >= 0.5

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出
"""

from __future__ import annotations

import logging
from collections import Counter

from assessment.scoring.schemas import (
    Question,
    QuestionType,
    UserAnswerLog,
    ValidityResult,
)

logger: logging.Logger = logging.getLogger(__name__)

# 置信度常量
_CONFIDENCE_INIT: float = 1.0
_CONFIDENCE_PENALTY: float = 0.2
_CONFIDENCE_VALID_THRESHOLD: float = 0.5

# 检测阈值
_LIE_SCALE_TRIGGER_VALUE: int = 4  # 测谎题 scale_value >= 4 触发
_CONSISTENCY_DIFF_THRESHOLD: int = 2  # 矛盾题对差异 > 2 触发
_STRAIGHT_LINING_RATIO: float = 0.70  # >70% 相同值触发
_FAST_RESPONSE_MS: int = 1000  # 平均响应 < 1000ms 触发


def _build_answer_map(answers: list[UserAnswerLog]) -> dict[str, UserAnswerLog]:
    """构建 题号 -> UserAnswerLog 的映射。"""
    return {ans.question_id: ans for ans in answers}


def _build_question_map(questions: list[Question]) -> dict[str, Question]:
    """构建 题号 -> Question 的映射。"""
    return {q.question_id: q for q in questions}


def _reverse_value(value: int) -> int:
    """反向计分翻转：1<->5, 2<->4, 3<->3（即 6 - value）。"""
    return 6 - value


def _check_lie_scale(
    answers: list[UserAnswerLog],
    question_map: dict[str, Question],
) -> bool:
    """测谎题检测：lie_scale 类型题目，若 scale_value >= 4 触发。

    返回 True 表示触发（即检测到社会赞许性作答）。
    """
    answer_map: dict[str, UserAnswerLog] = _build_answer_map(answers)
    for q in question_map.values():
        if q.question_type != QuestionType.LIE_SCALE:
            continue
        ans: UserAnswerLog | None = answer_map.get(q.question_id)
        if ans is None:
            continue
        if int(ans.scale_value) >= _LIE_SCALE_TRIGGER_VALUE:
            return True
    return False


def _check_consistency(
    answers: list[UserAnswerLog],
    question_map: dict[str, Question],
) -> bool:
    """矛盾题对检测：consistency 配对题，反向题反向计分后与正向题差异 > 2 触发。

    配对逻辑：按 pair_id 分组，每组内正向题取原值，反向题取翻转值，
    计算 |正向 - 反向翻转| > 2 即为该对矛盾。
    任一配对矛盾即触发（consistency_failed=True）。
    """
    answer_map: dict[str, UserAnswerLog] = _build_answer_map(answers)

    # 按 pair_id 收集 consistency 题对
    pairs: dict[str, list[Question]] = {}
    for q in question_map.values():
        if q.question_type != QuestionType.CONSISTENCY:
            continue
        if not q.pair_id:
            continue
        pairs.setdefault(q.pair_id, []).append(q)

    for pair_id, qs in pairs.items():
        if len(qs) < 2:
            continue
        # 取组内两题：区分正向/反向
        forward_val: int | None = None
        reverse_val: int | None = None
        for q in qs:
            ans: UserAnswerLog | None = answer_map.get(q.question_id)
            if ans is None:
                continue
            raw: int = int(ans.scale_value)
            if q.is_reverse:
                reverse_val = _reverse_value(raw)
            else:
                forward_val = raw

        if forward_val is None or reverse_val is None:
            continue
        diff: int = abs(forward_val - reverse_val)
        if diff > _CONSISTENCY_DIFF_THRESHOLD:
            logger.debug("矛盾题对 %s 差异 %d > %d，触发", pair_id, diff, _CONSISTENCY_DIFF_THRESHOLD)
            return True
    return False


def _check_straight_lining(answers: list[UserAnswerLog]) -> bool:
    """直线作答检测：如果 >70% 的题目选择相同值触发。"""
    if not answers:
        return False
    values: list[int] = [int(a.scale_value) for a in answers]
    most_common_count: int = Counter(values).most_common(1)[0][1]
    ratio: float = most_common_count / len(values)
    return ratio > _STRAIGHT_LINING_RATIO


def _check_response_time(answers: list[UserAnswerLog]) -> bool:
    """响应时间异常检测：如果平均响应时间 < 1000ms 触发。"""
    if not answers:
        return False
    durations: list[int] = [a.response_duration_ms for a in answers]
    avg_ms: float = sum(durations) / len(durations)
    return avg_ms < _FAST_RESPONSE_MS


def check_validity(
    answers: list[UserAnswerLog],
    questions: list[Question],
) -> ValidityResult:
    """效度检测入口。

    参数：
        answers: 用户作答列表
        questions: 题库列表

    返回：
        ValidityResult
    """
    question_map: dict[str, Question] = _build_question_map(questions)

    lie_triggered: bool = _check_lie_scale(answers, question_map)
    consistency_failed: bool = _check_consistency(answers, question_map)
    straight_lining: bool = _check_straight_lining(answers)
    time_anomaly: bool = _check_response_time(answers)

    # 置信度：初始 1.0，每触发一项扣 0.2
    confidence: float = _CONFIDENCE_INIT
    invalid_reasons: list[str] = []
    if lie_triggered:
        confidence -= _CONFIDENCE_PENALTY
        invalid_reasons.append("测谎题触发：存在社会赞许性作答倾向")
    if consistency_failed:
        confidence -= _CONFIDENCE_PENALTY
        invalid_reasons.append("矛盾题对未通过：存在前后不一致作答")
    if straight_lining:
        confidence -= _CONFIDENCE_PENALTY
        invalid_reasons.append("直线作答检测触发：超过 70% 题目选择相同值")
    if time_anomaly:
        confidence -= _CONFIDENCE_PENALTY
        invalid_reasons.append("响应时间异常：平均作答耗时过短")

    # 置信度下限保护
    if confidence < 0.0:
        confidence = 0.0

    is_valid: bool = confidence >= _CONFIDENCE_VALID_THRESHOLD

    return ValidityResult(
        is_valid=is_valid,
        invalid_reasons=invalid_reasons,
        confidence_score=confidence,
        lie_scale_triggered=lie_triggered,
        response_time_anomaly=time_anomaly,
        straight_lining_detected=straight_lining,
        consistency_failed=consistency_failed,
    )


def _calculate_duration_seconds(started_at: str, submitted_at: str) -> int:
    """计算答题耗时（秒）。支持 ISO 8601 格式和时间戳。"""
    from datetime import datetime

    def _parse(ts: str) -> datetime:
        ts = ts.strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(ts, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(ts.replace("Z", ""))
        except Exception:
            pass
        try:
            return datetime.fromtimestamp(float(ts))
        except (ValueError, OSError):
            return datetime.now()

    start: datetime = _parse(started_at)
    end: datetime = _parse(submitted_at)
    delta: int = int((end - start).total_seconds())
    return max(delta, 0)
