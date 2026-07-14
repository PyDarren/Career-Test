"""画己职测 — 人格原型匹配器（32 原型）。

本模块负责：
  1. 根据 OCEAN 五维度的 is_high 组合匹配 32 种人格原型之一（1-32）
  2. 生成维度组合码 archetype_code（如 OHCHEHAHNL）
  3. 提供原型元数据兜底配置（当未传入 archetype_configs 时使用）

原型映射规则（PRD 7.4）：
  大五五维度各分高(H)/低(L) 两档，2^5 = 32 种组合。
  键为 (o_high, c_high, e_high, a_high, n_high) 五元布尔组，值为 archetype_id（1-32）。

archetype_code 格式：O{H/L}C{H/L}E{H/L}A{H/L}N{H/L}（10 字符，如 OHCHEHAHNL）。
  - OH = O High, OL = O Low，以此类推。

设计约束：
  - 纯 Python，不依赖 Django ORM
  - 确定性：相同输入产生相同输出
"""

from __future__ import annotations

import logging

from assessment.scoring.schemas import OCEANDimension, OCEANDimensionScore

logger: logging.Logger = logging.getLogger(__name__)


# ===========================================================================
# 32 种原型的维度组合映射表
# 键: (o_high, c_high, e_high, a_high, n_high)
# 值: archetype_id (1-32)
# ===========================================================================
ARCHETYPE_MAP: dict[tuple[bool, bool, bool, bool, bool], int] = {
    (True, True, True, True, False): 1,  # 创意倡导者
    (True, True, True, True, True): 2,  # 共情先锋
    (True, True, True, False, False): 3,  # 自信开拓者
    (True, True, True, False, True): 4,  # 锐意进取者
    (True, True, False, True, False): 5,  # 沉稳架构师
    (True, True, False, True, True): 6,  # 深思关怀者
    (True, True, False, False, False): 7,  # 独立工程师
    (True, True, False, False, True): 8,  # 完美探索者
    (True, False, True, True, False): 9,  # 灵感传播者
    (True, False, True, True, True): 10,  # 热情联结者
    (True, False, True, False, False): 11,  # 自由探索者
    (True, False, True, False, True): 12,  # 冒险创新者
    (True, False, False, True, False): 13,  # 随性梦想家
    (True, False, False, True, True): 14,  # 敏感艺术家
    (True, False, False, False, False): 15,  # 独立思考者
    (True, False, False, False, True): 16,  # 叛逆创作者
    (False, True, True, True, False): 17,  # 稳健协调者
    (False, True, True, True, True): 18,  # 温暖守护者
    (False, True, True, False, False): 19,  # 果断执行者
    (False, True, True, False, True): 20,  # 务实竞争者
    (False, True, False, True, False): 21,  # 可靠支持者
    (False, True, False, True, True): 22,  # 忠诚守卫者
    (False, True, False, False, False): 23,  # 冷静分析者
    (False, True, False, False, True): 24,  # 严谨审查者
    (False, False, True, True, False): 25,  # 活跃助人者
    (False, False, True, True, True): 26,  # 热心社交者
    (False, False, True, False, False): 27,  # 自在行动者
    (False, False, True, False, True): 28,  # 冲动冒险者
    (False, False, False, True, False): 29,  # 轻松陪伴者
    (False, False, False, True, True): 30,  # 友善观察者
    (False, False, False, False, False): 31,  # 洒脱自由人
    (False, False, False, False, True): 32,  # 随性体验者
}


# ===========================================================================
# 原型元数据兜底配置（archetype_configs 未提供时使用）
# 字段对齐 personality/fixtures/archetypes.json
# ===========================================================================
ARCHETYPE_FALLBACK: dict[int, dict[str, object]] = {
    1: {
        "archetype_name": "创意倡导者",
        "archetype_slogan": "充满灵感且善于落地的领导者",
        "rarity": "稀有",
        "rarity_percentage": 5.5,
        "career_directions": ["产品总监", "创业CEO", "设计思维顾问"],
    },
    2: {
        "archetype_name": "共情先锋",
        "archetype_slogan": "敏锐感知他人需求的开拓者",
        "rarity": "极稀有",
        "rarity_percentage": 2.0,
        "career_directions": ["用户体验研究", "心理咨询", "公益创新"],
    },
    3: {
        "archetype_name": "自信开拓者",
        "archetype_slogan": "目标明确的创新执行者",
        "rarity": "常见",
        "rarity_percentage": 7.0,
        "career_directions": ["市场总监", "投资经理", "业务拓展"],
    },
    4: {
        "archetype_name": "锐意进取者",
        "archetype_slogan": "追求卓越的竞争型创新者",
        "rarity": "常见",
        "rarity_percentage": 6.5,
        "career_directions": ["管理咨询", "投行分析师", "产品经理"],
    },
    5: {
        "archetype_name": "沉稳架构师",
        "archetype_slogan": "深思熟虑的系统设计者",
        "rarity": "稀有",
        "rarity_percentage": 4.0,
        "career_directions": ["系统架构师", "战略规划", "技术总监"],
    },
    6: {
        "archetype_name": "深思关怀者",
        "archetype_slogan": "细腻负责的知识工作者",
        "rarity": "常见",
        "rarity_percentage": 6.0,
        "career_directions": ["学术研究", "医疗诊断", "高等教育"],
    },
    7: {
        "archetype_name": "独立工程师",
        "archetype_slogan": "专注高效的独立问题解决者",
        "rarity": "常见",
        "rarity_percentage": 7.5,
        "career_directions": ["软件工程师", "数据科学家", "算法工程师"],
    },
    8: {
        "archetype_name": "完美探索者",
        "archetype_slogan": "追求极致的深度思考者",
        "rarity": "稀有",
        "rarity_percentage": 3.5,
        "career_directions": ["科研学者", "精算师", "量化研究"],
    },
    9: {
        "archetype_name": "灵感传播者",
        "archetype_slogan": "活力四射的创意传播人",
        "rarity": "常见",
        "rarity_percentage": 6.8,
        "career_directions": ["品牌策划", "内容创作", "新媒体运营"],
    },
    10: {
        "archetype_name": "热情联结者",
        "archetype_slogan": "感性丰富的社交达人",
        "rarity": "常见",
        "rarity_percentage": 6.2,
        "career_directions": ["公关", "社群运营", "活动策划"],
    },
    11: {
        "archetype_name": "自由探索者",
        "archetype_slogan": "不受拘束的冒险家",
        "rarity": "常见",
        "rarity_percentage": 5.8,
        "career_directions": ["旅行博主", "创业者", "独立顾问"],
    },
    12: {
        "archetype_name": "冒险创新者",
        "archetype_slogan": "充满激情的冒险创新者",
        "rarity": "稀有",
        "rarity_percentage": 3.0,
        "career_directions": ["风险投资", "极限运动", "连续创业"],
    },
    13: {
        "archetype_name": "随性梦想家",
        "archetype_slogan": "温和自由的灵魂探索者",
        "rarity": "常见",
        "rarity_percentage": 5.6,
        "career_directions": ["自由撰稿人", "艺术家", "独立设计"],
    },
    14: {
        "archetype_name": "敏感艺术家",
        "archetype_slogan": "情感细腻的创意表达者",
        "rarity": "稀有",
        "rarity_percentage": 3.8,
        "career_directions": ["诗人", "音乐人", "插画师"],
    },
    15: {
        "archetype_name": "独立思考者",
        "archetype_slogan": "冷静超然的自由思想者",
        "rarity": "常见",
        "rarity_percentage": 5.4,
        "career_directions": ["独立学者", "自由职业", "评论作家"],
    },
    16: {
        "archetype_name": "叛逆创作者",
        "archetype_slogan": "不羁的独立创意人",
        "rarity": "稀有",
        "rarity_percentage": 2.8,
        "career_directions": ["先锋艺术家", "独立导演", "实验音乐"],
    },
    17: {
        "archetype_name": "稳健协调者",
        "archetype_slogan": "务实可靠的团队凝聚者",
        "rarity": "常见",
        "rarity_percentage": 7.2,
        "career_directions": ["项目经理", "HR总监", "运营管理"],
    },
    18: {
        "archetype_name": "温暖守护者",
        "archetype_slogan": "细心负责的关怀者",
        "rarity": "常见",
        "rarity_percentage": 6.6,
        "career_directions": ["护理管理", "教育培训", "客户成功"],
    },
    19: {
        "archetype_name": "果断执行者",
        "archetype_slogan": "高效直接的行动派",
        "rarity": "常见",
        "rarity_percentage": 7.0,
        "career_directions": ["运营总监", "销售管理", "供应链"],
    },
    20: {
        "archetype_name": "务实竞争者",
        "archetype_slogan": "结果导向的务实竞争者",
        "rarity": "常见",
        "rarity_percentage": 6.3,
        "career_directions": ["房地产", "快消品管理", "区域销售"],
    },
    21: {
        "archetype_name": "可靠支持者",
        "archetype_slogan": "踏实可靠的幕后支柱",
        "rarity": "常见",
        "rarity_percentage": 6.9,
        "career_directions": ["财务会计", "行政管理", "运营支持"],
    },
    22: {
        "archetype_name": "忠诚守卫者",
        "archetype_slogan": "尽职尽责的守护者",
        "rarity": "常见",
        "rarity_percentage": 5.9,
        "career_directions": ["品质管理", "安全审核", "合规风控"],
    },
    23: {
        "archetype_name": "冷静分析者",
        "archetype_slogan": "理性客观的问题解决者",
        "rarity": "常见",
        "rarity_percentage": 6.7,
        "career_directions": ["数据分析", "工程管理", "流程优化"],
    },
    24: {
        "archetype_name": "严谨审查者",
        "archetype_slogan": "一丝不苟的质检专家",
        "rarity": "稀有",
        "rarity_percentage": 3.6,
        "career_directions": ["审计师", "法务合规", "质量体系"],
    },
    25: {
        "archetype_name": "活跃助人者",
        "archetype_slogan": "热心肠的行动派",
        "rarity": "常见",
        "rarity_percentage": 6.0,
        "career_directions": ["社区服务", "活动策划", "志愿协调"],
    },
    26: {
        "archetype_name": "热心社交者",
        "archetype_slogan": "感性热心的社交爱好者",
        "rarity": "常见",
        "rarity_percentage": 5.7,
        "career_directions": ["客户服务", "社团组织", "会员运营"],
    },
    27: {
        "archetype_name": "自在行动者",
        "archetype_slogan": "随性直接的行动者",
        "rarity": "常见",
        "rarity_percentage": 5.5,
        "career_directions": ["自由销售", "个体经营", "现场服务"],
    },
    28: {
        "archetype_name": "冲动冒险者",
        "archetype_slogan": "敢想敢冲的冒险者",
        "rarity": "稀有",
        "rarity_percentage": 3.2,
        "career_directions": ["创业者", "交易员", "赛事运营"],
    },
    29: {
        "archetype_name": "轻松陪伴者",
        "archetype_slogan": "随和温暖的陪伴者",
        "rarity": "常见",
        "rarity_percentage": 5.8,
        "career_directions": ["客户关系", "后勤保障", "社区运营"],
    },
    30: {
        "archetype_name": "友善观察者",
        "archetype_slogan": "安静友善的观察者",
        "rarity": "常见",
        "rarity_percentage": 5.3,
        "career_directions": ["图书馆员", "档案管理", "文博研究"],
    },
    31: {
        "archetype_name": "洒脱自由人",
        "archetype_slogan": "随遇而安的自由灵魂",
        "rarity": "常见",
        "rarity_percentage": 5.0,
        "career_directions": ["自由职业", "gap year", "数字游民"],
    },
    32: {
        "archetype_name": "随性体验者",
        "archetype_slogan": "感性随性的体验主义者",
        "rarity": "稀有",
        "rarity_percentage": 2.5,
        "career_directions": ["生活类博主", "体验师", "旅行作家"],
    },
}


def match_archetype(ocean_scores: list[OCEANDimensionScore]) -> int:
    """根据五维度高/低组合匹配原型 ID（1-32）。

    参数：
        ocean_scores: 五维度得分列表（需包含 O/C/E/A/N）

    返回：
        原型 ID（1-32）
    """
    # 构建 dimension -> is_high 映射
    high_map: dict[OCEANDimension, bool] = {s.dimension: s.is_high for s in ocean_scores}

    key: tuple[bool, bool, bool, bool, bool] = (
        high_map.get(OCEANDimension.O, False),
        high_map.get(OCEANDimension.C, False),
        high_map.get(OCEANDimension.E, False),
        high_map.get(OCEANDimension.A, False),
        high_map.get(OCEANDimension.N, False),
    )

    archetype_id: int | None = ARCHETYPE_MAP.get(key)
    if archetype_id is None:
        logger.warning("未匹配到原型，键=%s，回退到 31", key)
        return 31
    return archetype_id


def build_archetype_code(ocean_scores: list[OCEANDimensionScore]) -> str:
    """生成维度组合码（如 OHCHEHAHNL）。

    格式：O{H/L}C{H/L}E{H/L}A{H/L}N{H/L}
    """
    high_map: dict[OCEANDimension, bool] = {s.dimension: s.is_high for s in ocean_scores}
    parts: list[str] = []
    for dim in (OCEANDimension.O, OCEANDimension.C, OCEANDimension.E, OCEANDimension.A, OCEANDimension.N):
        flag: str = "H" if high_map.get(dim, False) else "L"
        parts.append(f"{dim.value}{flag}")
    return "".join(parts)


def get_archetype_meta(
    archetype_id: int,
    archetype_configs: dict[int, dict] | None = None,
) -> dict[str, object]:
    """获取原型元数据（优先用传入配置，缺失则用兜底配置）。

    返回字段：archetype_name / archetype_slogan / rarity /
              rarity_percentage / career_directions / mascot_url 等。
    """
    if archetype_configs and archetype_id in archetype_configs:
        cfg: dict = archetype_configs[archetype_id]
        return {
            "archetype_name": cfg.get("archetype_name", f"原型{archetype_id}"),
            "archetype_slogan": cfg.get("archetype_slogan", ""),
            "rarity": cfg.get("rarity", "常见"),
            "rarity_percentage": cfg.get("rarity_percentage", 5.0),
            "career_directions": cfg.get("career_directions", []),
            "famous_people": cfg.get("famous_people", []),
            "best_partners": cfg.get("best_partners", []),
            "mascot_url": cfg.get("mascot_url", f"/assets/mascots/{archetype_id:02d}.png"),
        }

    fallback: dict[str, object] = ARCHETYPE_FALLBACK.get(
        archetype_id,
        {
            "archetype_name": f"原型{archetype_id}",
            "archetype_slogan": "",
            "rarity": "常见",
            "rarity_percentage": 5.0,
            "career_directions": [],
        },
    )
    meta: dict[str, object] = {
        "archetype_name": fallback.get("archetype_name", f"原型{archetype_id}"),
        "archetype_slogan": fallback.get("archetype_slogan", ""),
        "rarity": fallback.get("rarity", "常见"),
        "rarity_percentage": fallback.get("rarity_percentage", 5.0),
        "career_directions": fallback.get("career_directions", []),
        "famous_people": fallback.get("famous_people", []),
        "best_partners": fallback.get("best_partners", []),
        "mascot_url": f"/assets/mascots/{archetype_id:02d}.png",
    }
    return meta
