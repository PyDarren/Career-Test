"""画己职测 — 原始分标准化（常模归一化）。

本模块负责将原始得分转换为百分位（percentile）：
  1. MVP 阶段使用简化的线性映射：percentile = (raw - min) / (max - min) * 100
  2. OCEAN 维度：min=10, max=50（每维度 10 题，量表 1-5）
  3. RIASEC 类型：min=5, max=25（每类型 5 题，量表 1-5）

后续阶段可替换为基于真实 IPIP 常模的分段映射表（接口保持不变）。

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出
"""

from __future__ import annotations

import logging

from assessment.scoring.schemas import OCEANDimension, RIASECType

logger: logging.Logger = logging.getLogger(__name__)


# ===========================================================================
# 原始分取值范围
# ===========================================================================
OCEAN_RAW_MIN: int = 10
OCEAN_RAW_MAX: int = 50
OCEAN_RAW_SPAN: int = OCEAN_RAW_MAX - OCEAN_RAW_MIN  # 40

RIASEC_RAW_MIN: int = 5
RIASEC_RAW_MAX: int = 25
RIASEC_RAW_SPAN: int = RIASEC_RAW_MAX - RIASEC_RAW_MIN  # 20

# OCEAN 维度前缀集合（用于判定原始分范围）
_OCEAN_PREFIXES: frozenset[str] = frozenset({"BO", "BC", "BE", "BA", "BN"})
# RIASEC 类型前缀集合
_RIASEC_PREFIXES: frozenset[str] = frozenset({"RR", "RI", "RA", "RS", "RE", "RC"})


def get_norm_data() -> dict[str, dict[str, int]]:
    """返回常模数据（简化版，MVP 阶段使用线性映射）。

    返回结构：
        {
            "ocean": {"min": 10, "max": 50},
            "riasec": {"min": 5, "max": 25},
        }

    后续可替换为各维度独立的分段常模表，调用方接口不变。
    """
    return {
        "ocean": {"min": OCEAN_RAW_MIN, "max": OCEAN_RAW_MAX},
        "riasec": {"min": RIASEC_RAW_MIN, "max": RIASEC_RAW_MAX},
    }


def _clamp(value: float, low: float, high: float) -> float:
    """将数值限定在 [low, high] 区间。"""
    if value < low:
        return low
    if value > high:
        return high
    return value


def raw_to_percentile(raw_score: int, dimension: str, norm_data: dict) -> float:
    """将原始分转换为百分位。

    使用线性映射（简化版）：percentile = (raw - min) / (max - min) * 100

    参数：
        raw_score: 原始分
        dimension: 维度标识。支持两种形式：
                   - OCEAN 维度前缀（BO/BC/BE/BA/BN）或维度字母（O/C/E/A/N）
                   - RIASEC 类型前缀（RR/RI/RA/RS/RE/RC）或类型字母（R/I/A/S/E/C）
        norm_data: 常模数据（get_norm_data() 返回值）

    返回：
        百分位（0-100，float）
    """
    dim = dimension.upper()

    # 判定属于 OCEAN 还是 RIASEC
    if dim in _OCEAN_PREFIXES or dim in {d.value for d in OCEANDimension}:
        norm = norm_data.get("ocean", {"min": OCEAN_RAW_MIN, "max": OCEAN_RAW_MAX})
        min_val: int = norm.get("min", OCEAN_RAW_MIN)
        max_val: int = norm.get("max", OCEAN_RAW_MAX)
    elif dim in _RIASEC_PREFIXES or dim in {t.value for t in RIASECType}:
        norm = norm_data.get("riasec", {"min": RIASEC_RAW_MIN, "max": RIASEC_RAW_MAX})
        min_val = norm.get("min", RIASEC_RAW_MIN)
        max_val = norm.get("max", RIASEC_RAW_MAX)
    else:
        logger.warning("未知维度标识 %s，回退到 OCEAN 常模", dimension)
        norm = norm_data.get("ocean", {"min": OCEAN_RAW_MIN, "max": OCEAN_RAW_MAX})
        min_val = norm.get("min", OCEAN_RAW_MIN)
        max_val = norm.get("max", OCEAN_RAW_MAX)

    span: int = max_val - min_val
    if span <= 0:
        return 0.0

    percentile: float = (raw_score - min_val) / span * 100.0
    return _clamp(percentile, 0.0, 100.0)


def percentile_to_level(percentile: float) -> int:
    """百分位映射为色深档位（1-5）。

    规则：
        - 0-20%   -> 1
        - 20-40%  -> 2
        - 40-60%  -> 3
        - 60-80%  -> 4
        - 80-100% -> 5
    """
    if percentile < 20.0:
        return 1
    if percentile < 40.0:
        return 2
    if percentile < 60.0:
        return 3
    if percentile < 80.0:
        return 4
    return 5
