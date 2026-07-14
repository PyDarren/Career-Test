"""画己职测 — 计分引擎数据结构（Pydantic V2，零 Django 依赖）。

本模块定义计分引擎全流程所需的枚举与数据结构：
  - 枚举：OCEANDimension / RIASECType / DimensionPrefix / QuestionType /
          ScalePoint / QuestionModule
  - 输入：Question / UserAnswerLog / AssessmentSubmission
  - 中间：OCEANDimensionScore / RIASECDimensionScore / ValidityResult /
          SpectrumDot / ColorSpectrum / CareerMatch
  - 输出：AssessmentResult

设计约束：
  - 纯 Pydantic V2 模型，不依赖 Django ORM
  - 全部字段使用完整 type hints
  - 相同输入必须产生相同输出（确定性）
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


# ===========================================================================
# 枚举
# ===========================================================================
class OCEANDimension(str, Enum):
    """大五人格五维度（OCEAN）。"""

    O = "O"  # Openness 开放性
    C = "C"  # Conscientiousness 尽责性
    E = "E"  # Extraversion 外向性
    A = "A"  # Agreeableness 宜人性
    N = "N"  # Neuroticism 神经质


class RIASECType(str, Enum):
    """霍兰德职业兴趣六类型（RIASEC）。"""

    R = "R"  # Realistic 现实型
    I = "I"  # Investigative 研究型
    A = "A"  # Artistic 艺术型
    S = "S"  # Social 社会型
    E = "E"  # Enterprising 企业型
    C = "C"  # Conventional 常规型


class DimensionPrefix(str, Enum):
    """题目维度前缀编码。"""

    # 大五人格（B = Big Five）
    BO = "BO"  # 开放性
    BC = "BC"  # 尽责性
    BE = "BE"  # 外向性
    BA = "BA"  # 宜人性
    BN = "BN"  # 神经质
    # RIASEC（R = RIASEC）
    RR = "RR"  # 现实型
    RI = "RI"  # 研究型
    RA = "RA"  # 艺术型
    RS = "RS"  # 社会型
    RE = "RE"  # 企业型
    RC = "RC"  # 常规型


class QuestionType(str, Enum):
    """题目类型。兼容数据库模型值（ocean/riasec/validity）与计分引擎值。"""

    NORMAL = "normal"  # 普通正向计分题
    REVERSE = "reverse"  # 反向计分题
    LIE_SCALE = "lie_scale"  # 测谎题（社会赞许性检测）
    CONSISTENCY = "consistency"  # 一致性矛盾题对
    OCEAN = "ocean"  # 大五人格题（DB 模型值）
    RIASEC = "riasec"  # RIASEC 职业兴趣题（DB 模型值）
    VALIDITY = "validity"  # 效度题（DB 模型值）


class ScalePoint(int, Enum):
    """5 点李克特量表。"""

    ONE = 1  # 非常不符合
    TWO = 2  # 比较不符合
    THREE = 3  # 不确定
    FOUR = 4  # 比较符合
    FIVE = 5  # 非常符合


class QuestionModule(str, Enum):
    """题目所属模块。"""

    OCEAN = "ocean"  # 大五人格模块（50 题）
    RIASEC = "riasec"  # 职业兴趣模块（30 题）


# ===========================================================================
# 前缀 -> 维度映射（供计算器复用）
# ===========================================================================
PREFIX_TO_OCEAN: dict[str, OCEANDimension] = {
    "BO": OCEANDimension.O,
    "BC": OCEANDimension.C,
    "BE": OCEANDimension.E,
    "BA": OCEANDimension.A,
    "BN": OCEANDimension.N,
}

PREFIX_TO_RIASEC: dict[str, RIASECType] = {
    "RR": RIASECType.R,
    "RI": RIASECType.I,
    "RA": RIASECType.A,
    "RS": RIASECType.S,
    "RE": RIASECType.E,
    "RC": RIASECType.C,
}


# ===========================================================================
# 题目与答题输入
# ===========================================================================
class Question(BaseModel):
    """题目结构（5 点李克特量表，单陈述句）。"""

    question_id: str  # 题号，格式 Q\d{3}（如 Q001）
    dimension_prefix: DimensionPrefix  # 维度前缀
    module: QuestionModule  # 所属模块（OCEAN/RIASEC）
    question_type: QuestionType  # 题目类型
    is_reverse: bool = False  # 是否反向计分（仅大五人格有反向题）
    statement: str  # 陈述句文本
    pair_id: str | None = None  # 一致性题对的配对 ID（仅 consistency 类型）
    is_active: bool = True  # 是否启用


class UserAnswerLog(BaseModel):
    """用户单题作答记录。"""

    question_id: str  # 题号
    scale_value: ScalePoint  # 量表值（1-5）
    response_duration_ms: int  # 单题响应耗时（毫秒）
    modification_count: int = 0  # 修改次数
    answered_at: str  # 作答时间（ISO 字符串）


class AssessmentSubmission(BaseModel):
    """用户测评提交数据。"""

    session_token: str  # 会话令牌
    device_fingerprint: str  # 设备指纹
    answers: list[UserAnswerLog]  # 作答列表（业务要求正好 80 题）
    started_at: str  # 开始作答时间
    submitted_at: str  # 提交时间
    questions: list[Question] = []  # 题目配置列表（计分引擎使用）


# ===========================================================================
# 维度得分
# ===========================================================================
class OCEANDimensionScore(BaseModel):
    """大五人格单维度得分。"""

    dimension: OCEANDimension  # 维度 O/C/E/A/N
    raw_score: int  # 原始分（10-50）
    percentile: float  # 百分位（0-100）
    is_high: bool  # 是否高分（百分位 > 50）
    level: int  # 色深档位（1-5）
    t_score: float  # T 分数


class RIASECDimensionScore(BaseModel):
    """RIASEC 单类型得分。"""

    type: RIASECType  # 类型 R/I/A/S/E/C
    raw_score: int  # 原始分（5-25）
    rank: int  # 排名（1-6，1 为最高）
    is_top_three: bool  # 是否进入前三


# ===========================================================================
# 效度
# ===========================================================================
class ValidityResult(BaseModel):
    """效度检测结果。"""

    is_valid: bool  # 测评是否有效
    invalid_reasons: list[str]  # 失效原因列表
    confidence_score: float  # 置信度（0-1）
    lie_scale_triggered: bool  # 是否触发测谎题
    response_time_anomaly: bool  # 是否响应时间异常
    straight_lining_detected: bool  # 是否直线作答
    consistency_failed: bool  # 是否矛盾题对未通过


# ===========================================================================
# 色彩光谱
# ===========================================================================
class SpectrumDot(BaseModel):
    """色彩光谱单点。"""

    dimension: OCEANDimension  # 维度
    percentile: float  # 百分位
    level: int  # 色深档位（1-5）
    color: str  # HEX 色值


class ColorSpectrum(BaseModel):
    """五维色彩光谱。"""

    dots: list[SpectrumDot]  # 5 个色点
    visual: str  # 可视化字符串（如 "●●●●●"）


# ===========================================================================
# 职业推荐
# ===========================================================================
class CareerMatch(BaseModel):
    """职业匹配项。"""

    career_id: str  # 职业 ID
    career_name: str  # 职业名称
    match_score: float  # 匹配分（0-100）
    match_level: str  # 匹配等级 high/medium/low
    tags: list[str]  # 标签
    recommended_archetype: str  # 推荐原型名
    recommended_riasec: str  # 推荐 RIASEC 码


# ===========================================================================
# 完整测评结果
# ===========================================================================
class AssessmentResult(BaseModel):
    """完整测评结果（计分引擎输出）。"""

    # === 原型信息（免费可见）===
    archetype_id: int  # 原型编号（1-32）
    archetype_name: str  # 画像名
    archetype_slogan: str  # 一句话描述
    archetype_code: str  # 维度组合码（如 OHCHEHAEHLN）
    riasec_code: str  # RIASEC 码（如 IAS）

    # === 色彩光谱 ===
    color_spectrum: ColorSpectrum

    # === OCEAN 得分（免费可见）===
    ocean_scores: list[OCEANDimensionScore]  # 5 维度得分

    # === RIASEC 得分 ===
    riasec_scores: list[RIASECDimensionScore]  # 6 类型得分

    # === 免费卡片数据 ===
    free_card_data: dict[str, object]  # 人格认证卡数据

    # === 效度 ===
    validity: ValidityResult
    confidence: float  # 置信度（与 validity.confidence_score 一致）

    # === 职业推荐 ===
    career_matches: list[CareerMatch]

    # === 深度报告大纲（付费）===
    deep_report_outline: dict[str, object]

    computed_at: str  # 计算时间（ISO 字符串）
