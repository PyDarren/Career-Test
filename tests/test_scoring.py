"""画己职测 — 计分引擎单元测试。

覆盖 assessment/scoring 全部模块，目标覆盖率 >= 95%。

测试用例：
  1.  test_normal_scoring            正常答题（全选3）→ OCEAN raw=30, percentile=50
  2.  test_all_strongly_agree        有效全高分 → OCEAN raw=50, percentile=100, is_high=True
  3.  test_all_strongly_disagree     有效全低分 → OCEAN raw=10, percentile=0, is_high=False
  4.  test_reverse_scoring           反向题全选1 → 翻转后=5
  5.  test_reverse_scoring_full      反向题全选5 → 翻转后=1
  6.  test_riasec_scoring            RIASEC 全选5 → 每类型 raw=25
  7.  test_riasec_ranking            RIASEC 排名正确
  8.  test_riasec_tie_breaker        并列时按 R>I>A>S>E>C 优先
  9.  test_archetype_matching        32 种原型匹配（验证 5+ 种）
  10. test_color_spectrum            色彩光谱生成（5色，色深正确）
  11. test_validity_normal           正常答题 → is_valid=True, confidence=1.0
  12. test_validity_straight_lining  全选同一值 → straight_lining_detected=True
  13. test_validity_fast_response    响应时间过短 → response_time_anomaly=True
  14. test_confidence_calculation    多项异常 → confidence 降低
  15. test_deterministic             相同输入两次结果完全相同
  16. test_answer_count_validation   答题数≠80 → 抛出 ValueError
  17. test_riasec_code_generation    RIASEC 码取前三正确
  18. test_ocean_percentile          百分位转换正确
  19. test_free_card_data            free_card_data 包含必要字段
  20. test_full_pipeline             完整流程（提交→计分→结果）

补充用例（提升覆盖率）：
  - test_missing_answer / test_lie_scale_triggered / test_consistency_failed
  - test_normalizer_clamp_and_unknown / test_get_archetype_meta_with_configs
"""

from __future__ import annotations

import pytest

from assessment.scoring.archetype_matcher import (
    ARCHETYPE_FALLBACK,
    ARCHETYPE_MAP,
    build_archetype_code,
    get_archetype_meta,
    match_archetype,
)
from assessment.scoring.calculators import (
    calculate_ocean_scores,
    calculate_riasec_scores,
    generate_riasec_code,
)
from assessment.scoring.color_spectrum import COLOR_MAP, generate_color_spectrum
from assessment.scoring.engine import calculate_assessment_result
from assessment.scoring.normalizer import (
    get_norm_data,
    percentile_to_level,
    raw_to_percentile,
)
from assessment.scoring.schemas import (
    AssessmentSubmission,
    DimensionPrefix,
    OCEANDimension,
    OCEANDimensionScore,
    Question,
    QuestionModule,
    QuestionType,
    RIASECDimensionScore,
    RIASECType,
    UserAnswerLog,
)
from assessment.scoring.validity import check_validity

# ===========================================================================
# 题库数据（80 题，与 assessment/fixtures/questions.json 内容一致）
# (question_id, statement, dimension_prefix, is_reverse, scoring_role, pair_id, module)
# ===========================================================================
QUESTION_DATA: list[tuple[str, str, str, bool, str, str | None, str]] = [
    # BO 开放性 Q001-Q010（反向: Q003, Q008）
    ("Q001", "我喜欢思考新的想法和可能性", "BO", False, "normal", None, "ocean"),
    ("Q002", "我对艺术、文学或音乐有浓厚的兴趣", "BO", False, "normal", None, "ocean"),
    ("Q003", "我更倾向于按部就班，而非尝试新方法", "BO", True, "reverse", None, "ocean"),
    ("Q004", "我喜欢探索抽象的概念和理论", "BO", False, "normal", None, "ocean"),
    ("Q005", "我经常反思人生的意义和价值观", "BO", False, "normal", None, "ocean"),
    ("Q006", "我愿意挑战传统观念和权威", "BO", False, "normal", None, "ocean"),
    ("Q007", "我对不同的文化、思想和观点充满好奇", "BO", False, "normal", None, "ocean"),
    ("Q008", "我觉得丰富的想象力是浪费时间", "BO", True, "reverse", None, "ocean"),
    ("Q009", "我喜欢涉猎广泛的书籍和文章", "BO", False, "normal", None, "ocean"),
    ("Q010", "我乐于接受不熟悉的新鲜事物", "BO", False, "normal", None, "ocean"),
    # BC 尽责性 Q011-Q020（反向: Q014, Q019；测谎: Q012）
    ("Q011", "我会提前制定计划并按计划执行", "BC", False, "normal", None, "ocean"),
    ("Q012", "我总是说到做到，从不食言", "BC", False, "lie_scale", None, "ocean"),
    ("Q013", "我做事注重细节，力求完美", "BC", False, "normal", None, "ocean"),
    ("Q014", "我经常把该做的事拖延到最后一刻", "BC", True, "reverse", None, "ocean"),
    ("Q015", "我能长期坚持为既定目标努力", "BC", False, "normal", None, "ocean"),
    ("Q016", "我会按时完成承诺的任务", "BC", False, "normal", None, "ocean"),
    ("Q017", "我保持工作和生活环境的整洁有序", "BC", False, "normal", None, "ocean"),
    ("Q018", "面对困难任务我能专注直到完成", "BC", False, "normal", None, "ocean"),
    ("Q019", "我常常半途而废，难以坚持到底", "BC", True, "reverse", None, "ocean"),
    ("Q020", "我对自己的责任和义务认真负责", "BC", False, "normal", None, "ocean"),
    # BE 外向性 Q021-Q030（反向: Q025, Q030；一致性对 Q021<->Q025）
    ("Q021", "在社交场合中我通常是主动交谈的人", "BE", False, "consistency", "CONS_E", "ocean"),
    ("Q022", "我从与他人互动中获得能量", "BE", False, "normal", None, "ocean"),
    ("Q023", "我喜欢成为团队或活动的组织者", "BE", False, "normal", None, "ocean"),
    ("Q024", "我在人群中感到自在和充满活力", "BE", False, "normal", None, "ocean"),
    ("Q025", "我更喜欢独处，而非与人交往", "BE", True, "consistency", "CONS_E", "ocean"),
    ("Q026", "我乐于结识新朋友", "BE", False, "normal", None, "ocean"),
    ("Q027", "我说话做事节奏明快、充满热情", "BE", False, "normal", None, "ocean"),
    ("Q028", "我在会议或聚会中倾向于主动发言", "BE", False, "normal", None, "ocean"),
    ("Q029", "我享受成为众人关注的焦点", "BE", False, "normal", None, "ocean"),
    ("Q030", "我倾向于安静地待在角落，不引人注意", "BE", True, "reverse", None, "ocean"),
    # BA 宜人性 Q031-Q040（反向: Q035, Q040；测谎: Q036；一致性对 Q031<->Q035）
    ("Q031", "即使意见不同，我也能理解对方的立场", "BA", False, "consistency", "CONS_A", "ocean"),
    ("Q032", "我乐于帮助他人解决困难", "BA", False, "normal", None, "ocean"),
    ("Q033", "我相信大多数人本质上是善良的", "BA", False, "normal", None, "ocean"),
    ("Q034", "我在合作中愿意妥协以达成共识", "BA", False, "normal", None, "ocean"),
    ("Q035", "我经常与他人产生争执和冲突", "BA", True, "consistency", "CONS_A", "ocean"),
    ("Q036", "我从未对他人产生过嫉妒心理", "BA", False, "lie_scale", None, "ocean"),
    ("Q037", "我对他人的感受很敏感", "BA", False, "normal", None, "ocean"),
    ("Q038", "我宁愿合作，也不愿竞争", "BA", False, "normal", None, "ocean"),
    ("Q039", "我容易原谅他人的过错", "BA", False, "normal", None, "ocean"),
    ("Q040", "我倾向于批评，而非包容他人的不足", "BA", True, "reverse", None, "ocean"),
    # BN 神经质 Q041-Q050（反向: Q046, Q050；测谎: Q048；一致性对 Q041<->Q046）
    ("Q041", "我经常感到焦虑或不安", "BN", False, "consistency", "CONS_N", "ocean"),
    ("Q042", "小挫折也会让我情绪低落较长时间", "BN", False, "normal", None, "ocean"),
    ("Q043", "我容易因压力而感到紧张", "BN", False, "normal", None, "ocean"),
    ("Q044", "我时常担心事情会出问题", "BN", False, "normal", None, "ocean"),
    ("Q045", "我情绪起伏较大，容易波动", "BN", False, "normal", None, "ocean"),
    ("Q046", "我很少感到紧张或担忧", "BN", True, "consistency", "CONS_N", "ocean"),
    ("Q047", "面对不确定性我会感到不安", "BN", False, "normal", None, "ocean"),
    ("Q048", "我在任何情况下都能保持冷静，从不紧张", "BN", False, "lie_scale", None, "ocean"),
    ("Q049", "我容易被负面情绪困扰", "BN", False, "normal", None, "ocean"),
    ("Q050", "即使面对重大变故我也能泰然处之", "BN", True, "reverse", None, "ocean"),
    # RR 现实型 Q051-Q055（全部正向）
    ("Q051", "我喜欢使用工具、机械或设备进行实际操作", "RR", False, "normal", None, "riasec"),
    ("Q052", "我享受动手修理或制作实物", "RR", False, "normal", None, "riasec"),
    ("Q053", "我偏好在户外或实地环境中工作", "RR", False, "normal", None, "riasec"),
    ("Q054", "我对机械原理和工程结构感兴趣", "RR", False, "normal", None, "riasec"),
    ("Q055", "我愿意从事需要体力和动手能力的工作", "RR", False, "normal", None, "riasec"),
    # RI 研究型 Q056-Q060（全部正向）
    ("Q056", "我喜欢分析复杂的问题并寻找答案", "RI", False, "normal", None, "riasec"),
    ("Q057", "我享受进行科学探索和实验", "RI", False, "normal", None, "riasec"),
    ("Q058", "我对探究事物背后的原理充满热情", "RI", False, "normal", None, "riasec"),
    ("Q059", "我倾向于用逻辑和数据解决难题", "RI", False, "normal", None, "riasec"),
    ("Q060", "我喜欢阅读学术或专业领域的研究成果", "RI", False, "normal", None, "riasec"),
    # RA 艺术型 Q061-Q065（全部正向）
    ("Q061", "我喜欢通过艺术、音乐或写作表达自己", "RA", False, "normal", None, "riasec"),
    ("Q062", "我享受创意性的、不受拘束的工作", "RA", False, "normal", None, "riasec"),
    ("Q063", "我对美感和形式有敏锐的感知", "RA", False, "normal", None, "riasec"),
    ("Q064", "我倾向于用独特的方式解决问题", "RA", False, "normal", None, "riasec"),
    ("Q065", "我喜欢参与设计、表演或创作类活动", "RA", False, "normal", None, "riasec"),
    # RS 社会型 Q066-Q070（全部正向）
    ("Q066", "我喜欢帮助他人成长和发展", "RS", False, "normal", None, "riasec"),
    ("Q067", "我享受与人合作完成共同目标", "RS", False, "normal", None, "riasec"),
    ("Q068", "我善于倾听并理解他人的需求", "RS", False, "normal", None, "riasec"),
    ("Q069", "我愿意从事教育、辅导或服务类工作", "RS", False, "normal", None, "riasec"),
    ("Q070", "我在团队中常扮演协调和支持的角色", "RS", False, "normal", None, "riasec"),
    # RE 企业型 Q071-Q075（全部正向）
    ("Q071", "我喜欢带领团队达成目标", "RE", False, "normal", None, "riasec"),
    ("Q072", "我享受说服他人接受我的观点", "RE", False, "normal", None, "riasec"),
    ("Q073", "我善于发现商业机会并付诸行动", "RE", False, "normal", None, "riasec"),
    ("Q074", "我愿意承担风险以追求更大回报", "RE", False, "normal", None, "riasec"),
    ("Q075", "我喜欢在竞争环境中展现领导力", "RE", False, "normal", None, "riasec"),
    # RC 常规型 Q076-Q080（全部正向）
    ("Q076", "我喜欢按既定流程和规范完成任务", "RC", False, "normal", None, "riasec"),
    ("Q077", "我享受整理和归档信息使井井有条", "RC", False, "normal", None, "riasec"),
    ("Q078", "我对数据和细节的准确性有较高要求", "RC", False, "normal", None, "riasec"),
    ("Q079", "我偏好稳定、可预期的工作环境", "RC", False, "normal", None, "riasec"),
    ("Q080", "我善于处理报表、记录和行政事务", "RC", False, "normal", None, "riasec"),
]

# 测谎题题号集合
LIE_SCALE_IDS: frozenset[str] = frozenset({"Q012", "Q036", "Q048"})
# 一致性题对题号集合
CONSISTENCY_IDS: frozenset[str] = frozenset({"Q021", "Q025", "Q031", "Q035", "Q041", "Q046"})

_TIMESTAMP: str = "2026-01-01T00:00:00"
_SUBMITTED_AT: str = "2026-01-01T00:10:00"


# ===========================================================================
# 辅助函数
# ===========================================================================
def build_questions() -> list[Question]:
    """构建 80 题 Question schema 列表（与 fixture 内容一致）。"""
    role_map: dict[str, QuestionType] = {
        "normal": QuestionType.NORMAL,
        "reverse": QuestionType.REVERSE,
        "lie_scale": QuestionType.LIE_SCALE,
        "consistency": QuestionType.CONSISTENCY,
    }
    module_map: dict[str, QuestionModule] = {
        "ocean": QuestionModule.OCEAN,
        "riasec": QuestionModule.RIASEC,
    }
    questions: list[Question] = []
    for qid, statement, prefix, is_reverse, role, pair_id, module in QUESTION_DATA:
        # 反向题：question_type 标记为 reverse；一致性反向题标记为 consistency
        qt: QuestionType = role_map[role]
        questions.append(
            Question(
                question_id=qid,
                dimension_prefix=DimensionPrefix(prefix),
                module=module_map[module],
                question_type=qt,
                is_reverse=is_reverse,
                statement=statement,
                pair_id=pair_id,
                is_active=True,
            )
        )
    return questions


def _answer(qid: str, value: int, duration_ms: int = 2000) -> UserAnswerLog:
    """构造单题作答。"""
    return UserAnswerLog(
        question_id=qid,
        scale_value=value,
        response_duration_ms=duration_ms,
        modification_count=0,
        answered_at=_TIMESTAMP,
    )


def build_answers_all(value: int, questions: list[Question], duration_ms: int = 2000) -> list[UserAnswerLog]:
    """所有题作答同一值。"""
    return [_answer(q.question_id, value, duration_ms) for q in questions]


def build_answers_effective(value: int, questions: list[Question], duration_ms: int = 2000) -> list[UserAnswerLog]:
    """使所有题「有效分」相同：正向题取 value，反向题取 (6-value)（翻转后即 value）。"""
    answers: list[UserAnswerLog] = []
    for q in questions:
        v: int = (6 - value) if q.is_reverse else value
        answers.append(_answer(q.question_id, v, duration_ms))
    return answers


def build_answers_varied(
    questions: list[Question],
    overrides: dict[str, int] | None = None,
    duration_ms: int = 2000,
) -> list[UserAnswerLog]:
    """构造多样化作答（循环 2,3,4 避免直线作答），可按题号覆盖。"""
    overrides = overrides or {}
    answers: list[UserAnswerLog] = []
    for i, q in enumerate(questions, start=1):
        v: int = overrides.get(q.question_id, ((i - 1) % 3) + 2)
        answers.append(_answer(q.question_id, v, duration_ms))
    return answers


def build_submission(answers: list[UserAnswerLog]) -> AssessmentSubmission:
    """构造测评提交。"""
    return AssessmentSubmission(
        session_token="test-session-token",
        device_fingerprint="test-device-fingerprint",
        answers=answers,
        started_at=_TIMESTAMP,
        submitted_at=_SUBMITTED_AT,
    )


def make_ocean_scores(high_tuple: tuple[bool, bool, bool, bool, bool]) -> list[OCEANDimensionScore]:
    """根据 (o,c,e,a,n) 高低布尔组构造 OCEAN 得分（高分 raw=42，低分 raw=18）。"""
    dims: list[OCEANDimension] = [
        OCEANDimension.O,
        OCEANDimension.C,
        OCEANDimension.E,
        OCEANDimension.A,
        OCEANDimension.N,
    ]
    norm: dict = get_norm_data()
    out: list[OCEANDimensionScore] = []
    for dim, is_high in zip(dims, high_tuple, strict=False):
        raw: int = 42 if is_high else 18
        pct: float = raw_to_percentile(raw, dim.value, norm)
        out.append(
            OCEANDimensionScore(
                dimension=dim,
                raw_score=raw,
                percentile=pct,
                is_high=is_high,
                level=percentile_to_level(pct),
                t_score=50.0 + (raw - 30.0) / 10.0 * 10.0,
            )
        )
    return out


def _ocean_by_dim(scores: list[OCEANDimensionScore]) -> dict[OCEANDimension, OCEANDimensionScore]:
    return {s.dimension: s for s in scores}


def _riasec_by_type(scores: list[RIASECDimensionScore]) -> dict[RIASECType, RIASECDimensionScore]:
    return {s.type: s for s in scores}


# ===========================================================================
# 1. 正常答题（全选3）
# ===========================================================================
def test_normal_scoring() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(3, questions)
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    assert len(scores) == 5
    by_dim = _ocean_by_dim(scores)
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        s = by_dim[dim]
        # 反向题 3 翻转后仍为 3，故每维度 10×3=30
        assert s.raw_score == 30
        assert s.percentile == 50.0
        assert s.is_high is False  # 50 不大于 50
        assert s.level == 3
        assert s.t_score == 50.0


# ===========================================================================
# 2. 有效全高分（正向=5，反向=1，翻转后均为5）
# ===========================================================================
def test_all_strongly_agree() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_effective(5, questions)
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    by_dim = _ocean_by_dim(scores)
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        s = by_dim[dim]
        assert s.raw_score == 50
        assert s.percentile == 100.0
        assert s.is_high is True
        assert s.level == 5
        assert s.t_score == 70.0


# ===========================================================================
# 3. 有效全低分（正向=1，反向=5，翻转后均为1）
# ===========================================================================
def test_all_strongly_disagree() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_effective(1, questions)
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    by_dim = _ocean_by_dim(scores)
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        s = by_dim[dim]
        assert s.raw_score == 10
        assert s.percentile == 0.0
        assert s.is_high is False
        assert s.level == 1
        assert s.t_score == 30.0


# ===========================================================================
# 4. 反向题全选1 → 翻转后=5
# ===========================================================================
def test_reverse_scoring() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(1, questions)
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    by_dim = _ocean_by_dim(scores)
    # 每维度 8 道正向(=1) + 2 道反向(1→5) = 8 + 10 = 18
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        assert by_dim[dim].raw_score == 18


# ===========================================================================
# 5. 反向题全选5 → 翻转后=1
# ===========================================================================
def test_reverse_scoring_full() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(5, questions)
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    by_dim = _ocean_by_dim(scores)
    # 每维度 8 道正向(=5) + 2 道反向(5→1) = 40 + 2 = 42
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        assert by_dim[dim].raw_score == 42


# ===========================================================================
# 6. RIASEC 全选5 → 每类型 raw=25
# ===========================================================================
def test_riasec_scoring() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(5, questions)
    scores: list[RIASECDimensionScore] = calculate_riasec_scores(answers, questions)
    assert len(scores) == 6
    by_type = _riasec_by_type(scores)
    for t in (RIASECType.R, RIASECType.I, RIASECType.A, RIASECType.S, RIASECType.E, RIASECType.C):
        assert by_type[t].raw_score == 25


# ===========================================================================
# 7. RIASEC 排名正确
# ===========================================================================
def test_riasec_ranking() -> None:
    questions: list[Question] = build_questions()
    # 设定各类型分值：R=5(25), I=4(20), A=3(15), S=2(10), E=2(10), C=1(5)
    type_value: dict[str, int] = {
        "RR": 5,
        "RI": 4,
        "RA": 3,
        "RS": 2,
        "RE": 2,
        "RC": 1,
    }
    overrides: dict[str, int] = {}
    for qid, _stmt, prefix, _rev, _role, _pair, _mod in QUESTION_DATA:
        if prefix in type_value:
            overrides[qid] = type_value[prefix]
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides)
    scores: list[RIASECDimensionScore] = calculate_riasec_scores(answers, questions)
    by_type = _riasec_by_type(scores)

    assert by_type[RIASECType.R].raw_score == 25
    assert by_type[RIASECType.I].raw_score == 20
    assert by_type[RIASECType.A].raw_score == 15
    assert by_type[RIASECType.S].raw_score == 10
    assert by_type[RIASECType.E].raw_score == 10
    assert by_type[RIASECType.C].raw_score == 5

    assert by_type[RIASECType.R].rank == 1
    assert by_type[RIASECType.I].rank == 2
    assert by_type[RIASECType.A].rank == 3
    # S 与 E 并列(10)，rank 均为 4
    assert by_type[RIASECType.S].rank == 4
    assert by_type[RIASECType.E].rank == 4
    assert by_type[RIASECType.C].rank == 6

    # 前三名
    assert by_type[RIASECType.R].is_top_three is True
    assert by_type[RIASECType.I].is_top_three is True
    assert by_type[RIASECType.A].is_top_three is True
    assert by_type[RIASECType.S].is_top_three is False
    assert by_type[RIASECType.C].is_top_three is False


# ===========================================================================
# 8. RIASEC 并列时按 R>I>A>S>E>C 优先
# ===========================================================================
def test_riasec_tie_breaker() -> None:
    # 全部类型同分（全部作答 3 → 每类型 15），并列时 RIASEC 码取前三 = "RIA"
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(3, questions)
    scores: list[RIASECDimensionScore] = calculate_riasec_scores(answers, questions)
    # 所有类型 raw=15，rank 应均为 1（并列）
    for s in scores:
        assert s.raw_score == 15
        assert s.rank == 1
    code: str = generate_riasec_code(scores)
    assert code == "RIA"


# ===========================================================================
# 9. 32 种原型匹配（验证 5+ 种）
# ===========================================================================
def test_archetype_matching() -> None:
    cases: list[tuple[tuple[bool, bool, bool, bool, bool], int]] = [
        ((True, True, True, True, False), 1),  # 创意倡导者
        ((True, True, True, True, True), 2),  # 共情先锋
        ((True, True, False, False, False), 7),  # 独立工程师
        ((False, False, False, False, False), 31),  # 洒脱自由人
        ((False, False, False, False, True), 32),  # 随性体验者
        ((True, False, True, False, False), 11),  # 自由探索者
        ((False, True, False, True, False), 21),  # 可靠支持者
    ]
    for high_tuple, expected_id in cases:
        scores: list[OCEANDimensionScore] = make_ocean_scores(high_tuple)
        assert match_archetype(scores) == expected_id, f"组合 {high_tuple} 应匹配原型 {expected_id}"
    # 校验 ARCHETYPE_MAP 覆盖全部 32 种组合
    assert len(ARCHETYPE_MAP) == 32


# ===========================================================================
# 10. 色彩光谱生成（5色，色深正确）
# ===========================================================================
def test_color_spectrum() -> None:
    # 全部 level=3（percentile=50）
    _scores: list[OCEANDimensionScore] = make_ocean_scores((False, False, False, False, False))
    # make_ocean_scores 低分 raw=18 → percentile=20 → level=2，需手动构造 level=3 场景
    # 这里直接构造 percentile=50 的得分以验证色深映射
    norm: dict = get_norm_data()
    level3_scores: list[OCEANDimensionScore] = [
        OCEANDimensionScore(
            dimension=dim,
            raw_score=30,
            percentile=50.0,
            is_high=False,
            level=3,
            t_score=50.0,
        )
        for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N)
    ]
    spectrum = generate_color_spectrum(level3_scores)
    assert len(spectrum.dots) == 5
    for dot in spectrum.dots:
        assert dot.level == 3
        assert dot.color == COLOR_MAP[dot.dimension.value][3]
    # level=3 对应字符 ◑
    assert spectrum.visual == "◑◑◑◑◑"
    # 验证不同 level 取色正确
    _level5_scores: list[OCEANDimensionScore] = [
        OCEANDimensionScore(
            dimension=OCEANDimension.O,
            raw_score=50,
            percentile=100.0,
            is_high=True,
            level=5,
            t_score=70.0,
        )
    ]
    # generate_color_spectrum 需 5 维；构造完整 5 维 level=5
    all_high: list[OCEANDimensionScore] = make_ocean_scores((True, True, True, True, True))
    spectrum_high = generate_color_spectrum(all_high)
    for dot in spectrum_high.dots:
        assert dot.color == COLOR_MAP[dot.dimension.value][dot.level]
    # raw=42 → percentile=80 → level=5，对应字符 ●
    assert spectrum_high.visual == "●●●●●"
    # 确认 norm 一致
    assert norm == get_norm_data()


# ===========================================================================
# 11. 正常答题 → is_valid=True, confidence=1.0
# ===========================================================================
def test_validity_normal() -> None:
    questions: list[Question] = build_questions()
    # 多样化作答 + 测谎题压低到 3（避免触发）
    overrides: dict[str, int] = {qid: 3 for qid in LIE_SCALE_IDS}
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides, duration_ms=2000)
    result = check_validity(answers, questions)
    assert result.is_valid is True
    assert result.confidence_score == 1.0
    assert result.lie_scale_triggered is False
    assert result.response_time_anomaly is False
    assert result.straight_lining_detected is False
    assert result.consistency_failed is False
    assert result.invalid_reasons == []


# ===========================================================================
# 12. 全选同一值 → straight_lining_detected=True
# ===========================================================================
def test_validity_straight_lining() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(3, questions, duration_ms=2000)
    result = check_validity(answers, questions)
    assert result.straight_lining_detected is True
    # 仅直线作答触发，置信度 0.8，仍有效
    assert result.confidence_score == 0.8
    assert result.is_valid is True
    assert result.lie_scale_triggered is False
    assert result.response_time_anomaly is False


# ===========================================================================
# 13. 响应时间过短 → response_time_anomaly=True
# ===========================================================================
def test_validity_fast_response() -> None:
    questions: list[Question] = build_questions()
    overrides: dict[str, int] = {qid: 3 for qid in LIE_SCALE_IDS}
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides, duration_ms=500)
    result = check_validity(answers, questions)
    assert result.response_time_anomaly is True
    assert result.straight_lining_detected is False
    assert result.confidence_score == 0.8
    assert result.is_valid is True


# ===========================================================================
# 14. 多项异常 → confidence 降低
# ===========================================================================
def test_confidence_calculation() -> None:
    questions: list[Question] = build_questions()
    # 触发：测谎题(Q012=5) + 一致性冲突(Q021=5, Q025=5) + 响应过快(500ms)
    overrides: dict[str, int] = {
        "Q012": 5,  # 测谎题 >=4 触发
        "Q021": 5,  # 一致性正向
        "Q025": 5,  # 一致性反向(5→1)，与正向(5)差异 4 > 2 触发
    }
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides, duration_ms=500)
    result = check_validity(answers, questions)
    assert result.lie_scale_triggered is True
    assert result.consistency_failed is True
    assert result.response_time_anomaly is True
    assert result.straight_lining_detected is False
    # 三项触发：1.0 - 3×0.2 = 0.4
    assert result.confidence_score == pytest.approx(0.4)
    assert result.is_valid is False  # 0.4 < 0.5
    assert len(result.invalid_reasons) == 3


# ===========================================================================
# 15. 相同输入两次计算结果完全相同
# ===========================================================================
def test_deterministic() -> None:
    questions: list[Question] = build_questions()
    overrides: dict[str, int] = {qid: 3 for qid in LIE_SCALE_IDS}
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides)
    submission: AssessmentSubmission = build_submission(answers)
    r1 = calculate_assessment_result(submission, questions)
    r2 = calculate_assessment_result(submission, questions)
    assert r1.model_dump_json() == r2.model_dump_json()
    # computed_at 取自提交时间，保证确定性
    assert r1.computed_at == _SUBMITTED_AT


# ===========================================================================
# 16. 答题数≠80 → 抛出 ValueError
# ===========================================================================
def test_answer_count_validation() -> None:
    questions: list[Question] = build_questions()
    # 79 题
    answers_short: list[UserAnswerLog] = build_answers_all(3, questions)[:79]
    submission_short: AssessmentSubmission = build_submission(answers_short)
    with pytest.raises(ValueError):
        calculate_assessment_result(submission_short, questions)

    # 81 题
    answers_long: list[UserAnswerLog] = build_answers_all(3, questions) + [_answer("Q081", 3)]
    submission_long: AssessmentSubmission = build_submission(answers_long)
    with pytest.raises(ValueError):
        calculate_assessment_result(submission_long, questions)


# ===========================================================================
# 17. RIASEC 码取前三正确
# ===========================================================================
def test_riasec_code_generation() -> None:
    # 直接构造得分：R=25, I=20, A=15, S=10, E=10, C=5 → 码 "RIA"
    scores: list[RIASECDimensionScore] = [
        RIASECDimensionScore(type=RIASECType.R, raw_score=25, rank=1, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.I, raw_score=20, rank=2, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.A, raw_score=15, rank=3, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.S, raw_score=10, rank=4, is_top_three=False),
        RIASECDimensionScore(type=RIASECType.E, raw_score=10, rank=4, is_top_three=False),
        RIASECDimensionScore(type=RIASECType.C, raw_score=5, rank=6, is_top_three=False),
    ]
    assert generate_riasec_code(scores) == "RIA"

    # 并列场景：E 与 C 同分，E 优先于 C
    scores2: list[RIASECDimensionScore] = [
        RIASECDimensionScore(type=RIASECType.R, raw_score=25, rank=1, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.I, raw_score=20, rank=2, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.A, raw_score=15, rank=3, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.S, raw_score=15, rank=3, is_top_three=True),
        RIASECDimensionScore(type=RIASECType.E, raw_score=10, rank=5, is_top_three=False),
        RIASECDimensionScore(type=RIASECType.C, raw_score=10, rank=5, is_top_three=False),
    ]
    # 第三名 A(15) 与 S(15) 并列，A 优先 → 码 "RIA"
    assert generate_riasec_code(scores2) == "RIA"


# ===========================================================================
# 18. 百分位转换正确
# ===========================================================================
def test_ocean_percentile() -> None:
    norm: dict = get_norm_data()
    # OCEAN: min=10, max=50
    assert raw_to_percentile(30, "O", norm) == 50.0
    assert raw_to_percentile(50, "BO", norm) == 100.0
    assert raw_to_percentile(10, "C", norm) == 0.0
    assert raw_to_percentile(42, "BN", norm) == 80.0
    assert raw_to_percentile(18, "BE", norm) == 20.0
    # RIASEC: min=5, max=25
    assert raw_to_percentile(15, "R", norm) == 50.0
    assert raw_to_percentile(25, "RR", norm) == 100.0
    assert raw_to_percentile(5, "RC", norm) == 0.0
    # 色深档位
    assert percentile_to_level(0.0) == 1
    assert percentile_to_level(19.9) == 1
    assert percentile_to_level(20.0) == 2
    assert percentile_to_level(50.0) == 3
    assert percentile_to_level(79.9) == 4
    assert percentile_to_level(80.0) == 5
    assert percentile_to_level(100.0) == 5


# ===========================================================================
# 19. free_card_data 包含必要字段
# ===========================================================================
def test_free_card_data() -> None:
    questions: list[Question] = build_questions()
    overrides: dict[str, int] = {qid: 3 for qid in LIE_SCALE_IDS}
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides)
    submission: AssessmentSubmission = build_submission(answers)
    result = calculate_assessment_result(submission, questions)

    fcd: dict = result.free_card_data
    required_keys: list[str] = [
        "archetype_id",
        "archetype_name",
        "archetype_slogan",
        "archetype_code",
        "riasec_code",
        "color_spectrum",
        "rarity",
        "rarity_percentage",
        "mascot_url",
        "famous_people",
        "best_partners",
        "full_label",
    ]
    for key in required_keys:
        assert key in fcd, f"free_card_data 缺少字段 {key}"
    assert fcd["archetype_id"] == result.archetype_id
    assert fcd["archetype_name"] == result.archetype_name
    assert fcd["riasec_code"] == result.riasec_code
    assert fcd["color_spectrum"] == result.color_spectrum.visual
    assert isinstance(fcd["famous_people"], list)
    assert isinstance(fcd["best_partners"], list)
    assert isinstance(fcd["rarity_percentage"], (int, float))
    assert fcd["full_label"] == f"{result.archetype_name} · {result.riasec_code}"


# ===========================================================================
# 20. 完整流程（提交→计分→结果）
# ===========================================================================
def test_full_pipeline() -> None:
    questions: list[Question] = build_questions()
    overrides: dict[str, int] = {qid: 3 for qid in LIE_SCALE_IDS}
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides)
    submission: AssessmentSubmission = build_submission(answers)
    result = calculate_assessment_result(submission, questions)

    # 原型
    assert 1 <= result.archetype_id <= 32
    assert result.archetype_name
    assert len(result.archetype_code) == 10
    # RIASEC 码
    assert len(result.riasec_code) == 3
    # OCEAN / RIASEC 得分
    assert len(result.ocean_scores) == 5
    assert len(result.riasec_scores) == 6
    # 色彩光谱
    assert len(result.color_spectrum.dots) == 5
    assert len(result.color_spectrum.visual) == 5
    # 效度
    assert result.validity.is_valid is True
    assert result.confidence == result.validity.confidence_score
    # 职业推荐
    assert isinstance(result.career_matches, list)
    assert len(result.career_matches) >= 1
    for cm in result.career_matches:
        assert 0 <= cm.match_score <= 100
        assert cm.match_level in ("high", "medium", "low")
    # 深度报告大纲
    assert "chapters" in result.deep_report_outline
    assert result.deep_report_outline["chapter_count"] == 12
    # computed_at 取自提交时间
    assert result.computed_at == _SUBMITTED_AT


# ===========================================================================
# 补充用例：缺失作答按 0 计入
# ===========================================================================
def test_missing_answer() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(3, questions)
    # 删除 Q001 的作答，BO 维度将少 3 分（30 - 3 = 27）
    answers = [a for a in answers if a.question_id != "Q001"]
    # 计算器不强制 80 题，可处理缺失
    scores: list[OCEANDimensionScore] = calculate_ocean_scores(answers, questions, get_norm_data())
    by_dim = _ocean_by_dim(scores)
    assert by_dim[OCEANDimension.O].raw_score == 27  # 30 - 3（Q001 缺失按 0）


# ===========================================================================
# 补充用例：测谎题触发
# ===========================================================================
def test_lie_scale_triggered() -> None:
    questions: list[Question] = build_questions()
    overrides: dict[str, int] = {"Q012": 4}  # 测谎题 =4 触发
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides, duration_ms=2000)
    result = check_validity(answers, questions)
    assert result.lie_scale_triggered is True
    assert result.confidence_score == 0.8


# ===========================================================================
# 补充用例：一致性题对失败
# ===========================================================================
def test_consistency_failed() -> None:
    questions: list[Question] = build_questions()
    # Q021(正向)=5, Q025(反向)=5 → 翻转后=1，差异 |5-1|=4 > 2 触发
    overrides: dict[str, int] = {"Q021": 5, "Q025": 5}
    # 将测谎题压低到 3，避免测谎题触发干扰一致性检测
    overrides.update({qid: 3 for qid in LIE_SCALE_IDS})
    answers: list[UserAnswerLog] = build_answers_varied(questions, overrides=overrides, duration_ms=2000)
    result = check_validity(answers, questions)
    assert result.consistency_failed is True
    assert result.lie_scale_triggered is False
    assert result.confidence_score == 0.8


# ===========================================================================
# 补充用例：normalizer 边界（clamp）与未知维度回退
# ===========================================================================
def test_normalizer_clamp_and_unknown() -> None:
    norm: dict = get_norm_data()
    # 超出上限 → clamp 到 100
    assert raw_to_percentile(60, "O", norm) == 100.0
    # 低于下限 → clamp 到 0
    assert raw_to_percentile(0, "O", norm) == 0.0
    # 未知维度 → 回退到 OCEAN 常模（不抛异常）
    assert raw_to_percentile(30, "XYZ", norm) == 50.0
    # span<=0 容错
    bad_norm: dict = {"ocean": {"min": 10, "max": 10}, "riasec": {"min": 5, "max": 25}}
    assert raw_to_percentile(30, "O", bad_norm) == 0.0


# ===========================================================================
# 补充用例：get_archetype_meta 使用传入配置
# ===========================================================================
def test_get_archetype_meta_with_configs() -> None:
    configs: dict[int, dict] = {
        1: {
            "archetype_name": "自定义原型",
            "archetype_slogan": "自定义口号",
            "rarity": "极稀有",
            "rarity_percentage": 1.5,
            "career_directions": ["方向A", "方向B"],
            "famous_people": ["名人甲"],
            "best_partners": [2, 3],
            "mascot_url": "/assets/mascots/custom.png",
        }
    }
    meta: dict = get_archetype_meta(1, configs)
    assert meta["archetype_name"] == "自定义原型"
    assert meta["rarity_percentage"] == 1.5
    assert meta["mascot_url"] == "/assets/mascots/custom.png"

    # 未提供配置时使用兜底
    meta_fb: dict = get_archetype_meta(1, None)
    assert meta_fb["archetype_name"] == "创意倡导者"
    assert meta_fb["mascot_url"] == "/assets/mascots/01.png"
    # 兜底覆盖全部 32 个原型
    for aid in range(1, 33):
        assert aid in ARCHETYPE_FALLBACK
        assert get_archetype_meta(aid, None)["archetype_name"]


# ===========================================================================
# 补充用例：archetype_code 生成
# ===========================================================================
def test_archetype_code_generation() -> None:
    # 全高 → OHCHEHAHNH（N 也为 High）
    scores_high: list[OCEANDimensionScore] = make_ocean_scores((True, True, True, True, True))
    assert build_archetype_code(scores_high) == "OHCHEHAHNH"
    # 全低 → OLCLELALNL
    scores_low: list[OCEANDimensionScore] = make_ocean_scores((False, False, False, False, False))
    assert build_archetype_code(scores_low) == "OLCLELALNL"


# ===========================================================================
# 补充用例：色彩光谱缺失维度容错
# ===========================================================================
def test_color_spectrum_missing_dimension() -> None:
    # 仅传入 3 个维度（缺少 E、A），generate_color_spectrum 应使用默认 level=3
    partial_scores: list[OCEANDimensionScore] = [
        OCEANDimensionScore(
            dimension=OCEANDimension.O,
            raw_score=50,
            percentile=100.0,
            is_high=True,
            level=5,
            t_score=70.0,
        ),
        OCEANDimensionScore(
            dimension=OCEANDimension.C,
            raw_score=10,
            percentile=0.0,
            is_high=False,
            level=1,
            t_score=30.0,
        ),
        OCEANDimensionScore(
            dimension=OCEANDimension.N,
            raw_score=30,
            percentile=50.0,
            is_high=False,
            level=3,
            t_score=50.0,
        ),
    ]
    spectrum = generate_color_spectrum(partial_scores)
    assert len(spectrum.dots) == 5
    by_dim: dict[str, object] = {d.dimension.value: d for d in spectrum.dots}
    # 缺失维度 E、A 使用默认 level=3
    assert by_dim["E"].level == 3  # type: ignore[union-attr]
    assert by_dim["A"].level == 3  # type: ignore[union-attr]
    assert by_dim["E"].percentile == 50.0  # type: ignore[union-attr]
    assert by_dim["A"].percentile == 50.0  # type: ignore[union-attr]


# ===========================================================================
# 补充用例：效度检测空答案容错
# ===========================================================================
def test_validity_empty_answers() -> None:
    questions: list[Question] = build_questions()
    result = check_validity([], questions)
    # 空答案不会触发直线作答和响应时间异常
    assert result.straight_lining_detected is False
    assert result.response_time_anomaly is False
    assert result.lie_scale_triggered is False
    assert result.consistency_failed is False
    assert result.confidence_score == 1.0
    assert result.is_valid is True


# ===========================================================================
# 补充用例：RIASEC 缺失作答按 0 计入
# ===========================================================================
def test_riasec_missing_answer() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_all(3, questions)
    # 删除 Q051（RR 现实型），该类型将少 3 分（15 - 3 = 12）
    answers = [a for a in answers if a.question_id != "Q051"]
    scores: list[RIASECDimensionScore] = calculate_riasec_scores(answers, questions)
    by_type = _riasec_by_type(scores)
    assert by_type[RIASECType.R].raw_score == 12  # 15 - 3（Q051 缺失按 0）


# ===========================================================================
# 补充用例：测谎题/一致性题缺失作答时不触发
# ===========================================================================
def test_validity_missing_lie_and_consistency_answers() -> None:
    questions: list[Question] = build_questions()
    answers: list[UserAnswerLog] = build_answers_varied(
        questions, overrides={qid: 3 for qid in LIE_SCALE_IDS}, duration_ms=2000
    )
    # 删除所有测谎题和一致性题的作答
    skip_ids: frozenset[str] = LIE_SCALE_IDS | CONSISTENCY_IDS
    answers = [a for a in answers if a.question_id not in skip_ids]
    result = check_validity(answers, questions)
    # 缺失作答不会触发测谎和一致性检测
    assert result.lie_scale_triggered is False
    assert result.consistency_failed is False
