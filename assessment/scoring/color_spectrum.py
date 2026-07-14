"""画己职测 — 色彩光谱生成。

本模块负责根据 OCEAN 五维度百分位生成个性化色彩光谱码（5 色圆点）：
  1. 每个维度根据 level(1-5) 取对应 HEX 色值
  2. 生成 dots 列表（SpectrumDot）
  3. 生成 visual 字符串（用不同 Unicode 字符表示色深深浅）

色深档位与色值（与 PRD 1.4.1 一致）：
  Level 1（0-20%）  -> 浅色
  Level 2（20-40%） -> 偏浅
  Level 3（40-60%） -> 中等（基准色）
  Level 4（60-80%） -> 偏深
  Level 5（80-100%）-> 深色

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出
"""

from __future__ import annotations

import logging

from assessment.scoring.schemas import (
    ColorSpectrum,
    OCEANDimension,
    OCEANDimensionScore,
    SpectrumDot,
)

logger: logging.Logger = logging.getLogger(__name__)


# ===========================================================================
# 色彩映射表（维度 -> {level: HEX}）
# 与 PRD 1.4.1 / common.constants.COLOR_SPECTRUM 对齐
# ===========================================================================
COLOR_MAP: dict[str, dict[int, str]] = {
    "O": {1: "#D4C3F0", 2: "#B89FE0", 3: "#9B7ED8", 4: "#8266C2", 5: "#6B4EAB"},
    "C": {1: "#B0D4E0", 2: "#8AB5C6", 3: "#5a96b1", 4: "#4A86A1", 5: "#3A7691"},
    "E": {1: "#B0D5C0", 2: "#88BD9F", 3: "#5ea67e", 4: "#4E966E", 5: "#3E865E"},
    "A": {1: "#F0D9A0", 2: "#E5C67C", 3: "#deb45c", 4: "#CEA44C", 5: "#BE943C"},
    "N": {1: "#F0A590", 2: "#E88870", 3: "#e17055", 4: "#D16045", 5: "#C15035"},
}

# OCEAN 维度固定输出顺序
_SPECTRUM_ORDER: list[OCEANDimension] = [
    OCEANDimension.O,
    OCEANDimension.C,
    OCEANDimension.E,
    OCEANDimension.A,
    OCEANDimension.N,
]

# 可视化字符：用不同填充深浅的圆点表示色深档位（1 浅 -> 5 深）
# 使用 Unicode 圆点字符区分深浅
_VISUAL_CHARS: dict[int, str] = {
    1: "○",  # 空心圆（最浅）
    2: "◔",  # 四分之一圆
    3: "◑",  # 半圆
    4: "◕",  # 四分之三圆
    5: "●",  # 实心圆（最深）
}


def _level_to_color(dimension: OCEANDimension, level: int) -> str:
    """根据维度与色深档位取 HEX 色值。"""
    palette: dict[int, str] | None = COLOR_MAP.get(dimension.value)
    if palette is None:
        logger.warning("维度 %s 无色值映射，回退到灰色", dimension)
        return "#999999"
    return palette.get(level, palette[3])


def _level_to_visual_char(level: int) -> str:
    """根据色深档位取可视化字符。"""
    return _VISUAL_CHARS.get(level, "●")


def generate_color_spectrum(ocean_scores: list[OCEANDimensionScore]) -> ColorSpectrum:
    """根据五维度百分位生成色彩光谱码（5 色圆点）。

    参数：
        ocean_scores: 五维度得分列表

    返回：
        ColorSpectrum（含 5 个 SpectrumDot 与 visual 字符串）
    """
    score_map: dict[OCEANDimension, OCEANDimensionScore] = {s.dimension: s for s in ocean_scores}

    dots: list[SpectrumDot] = []
    visual_parts: list[str] = []
    for dim in _SPECTRUM_ORDER:
        score: OCEANDimensionScore | None = score_map.get(dim)
        if score is None:
            logger.warning("缺失维度 %s 的得分，使用默认 level=3", dim)
            level: int = 3
            percentile: float = 50.0
        else:
            level = score.level
            percentile = score.percentile

        color: str = _level_to_color(dim, level)
        dots.append(
            SpectrumDot(
                dimension=dim,
                percentile=percentile,
                level=level,
                color=color,
            )
        )
        visual_parts.append(_level_to_visual_char(level))

    return ColorSpectrum(dots=dots, visual="".join(visual_parts))
