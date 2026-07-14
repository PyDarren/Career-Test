"""画己职测 — 深度报告生成服务

本模块负责深度报告（12 章）的生成与管理：
  1. generate_deep_report() — 根据原型/RIASEC/OCEAN 生成完整 12 章报告
  2. get_report_preview()   — 返回免费预览（第 1 章完整 + 其余标题+预览片段）
  3. get_full_report()      — 校验支付状态后返回完整报告或预览
  4. check_payment_status() — 检查测评是否已付费解锁

12 章固定结构：
  1  你的人格画像速览
  2  人格特征分析
  3  人口比例
  4  相同人格名人
  5  人格优势
  6  人格劣势
  7  成长建议
  8  大五人格五维度深度解读
  9  人格恋爱专题
  10 最佳恋爱对象
  11 深度职业专题
  12 合适的职业
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from common.utils import mask_token

if TYPE_CHECKING:
    from careers.models import Career
    from personality.models import PersonalityArchetype

logger = logging.getLogger(__name__)

# ===========================================================================
# 常量
# ===========================================================================

# 12 章标题（固定结构，不可更改）
CHAPTER_TITLES: list[str] = [
    "你的人格画像速览",
    "人格特征分析",
    "人口比例",
    "相同人格名人",
    "人格优势",
    "人格劣势",
    "成长建议",
    "大五人格五维度深度解读",
    "人格恋爱专题",
    "最佳恋爱对象",
    "深度职业专题",
    "合适的职业",
]

# 预览截取比例（15%-20%）
PREVIEW_RATIO: float = 0.18
PREVIEW_MIN_CHARS: int = 60

# 默认百分位（用于预览模式，根据原型 high/low 推导）
DEFAULT_HIGH_PERCENTILE: float = 75.0
DEFAULT_LOW_PERCENTILE: float = 25.0

# 大五维度中文名
OCEAN_LABELS: dict[str, str] = {
    "O": "开放性",
    "C": "尽责性",
    "E": "外向性",
    "A": "宜人性",
    "N": "神经质",
}

# 大五维度英文全称
OCEAN_FULL_NAMES: dict[str, str] = {
    "O": "Openness（开放性）",
    "C": "Conscientiousness（尽责性）",
    "E": "Extraversion（外向性）",
    "A": "Agreeableness（宜人性）",
    "N": "Neuroticism（神经质）",
}

# RIASEC 类型中文名
RIASEC_FULL_NAMES: dict[str, str] = {
    "R": "现实型",
    "I": "研究型",
    "A": "艺术型",
    "S": "社会型",
    "E": "企业型",
    "C": "常规型",
}

# RIASEC 类型描述
RIASEC_DESCRIPTIONS: dict[str, str] = {
    "R": "喜欢动手操作、使用工具和机械，偏好具体实际的任务，注重看得见的成果",
    "I": "喜欢观察、学习、研究和分析，偏好科学探索和智力挑战，追求真理与理解",
    "A": "喜欢创造和自我表达，偏好非结构化的自由环境，追求美感和原创性",
    "S": "喜欢帮助、教导和服务他人，偏好与人合作的工作，重视关系与社会贡献",
    "E": "喜欢影响、说服和管理他人，偏好领导和竞争环境，追求成就与权力",
    "C": "喜欢组织、整理和处理数据，偏好有序和规范的工作，重视精确与效率",
}

# ===========================================================================
# 大五人格维度高低分详细描述
# 每个维度包含 high/low 两套描述，覆盖各章节所需内容
# ===========================================================================
DIMENSION_DATA: dict[str, dict[str, dict[str, str]]] = {
    "O": {
        "high": {
            "level_name": "高度开放",
            "summary": "你拥有旺盛的好奇心和丰富的想象力，对新鲜事物、多元观点和抽象概念充满热情。"
            "你乐于探索未知，不满足于表面答案，总是试图理解事物背后的深层逻辑。"
            "你的思维不拘泥于传统和常规，喜欢从不同角度审视问题。",
            "behavior": "你倾向于尝试新方法、接纳新理念，在变化中感到兴奋而非焦虑。"
            "你欣赏艺术与美，喜欢哲学思辨，对不同的文化和生活方式保持开放态度。"
            "你乐于接受挑战常规的想法，不害怕打破既定框架。",
            "advantage": "创新思维突出、学习能力强劲、对新环境适应力强、视野开阔、善于跨界联想",
            "weakness": "可能因想法过多而难以聚焦落地，对 routine 事务缺乏耐心，"
            "有时过于追求新奇而忽视稳定积累，决策时可能因选项过多而犹豫不决",
            "growth": "在保持开放探索的同时，有意识地训练聚焦与执行力。"
            "可以为自己设定阶段性的“深度目标”，将发散的创意收敛为可落地的行动计划，"
            "避免“什么都想试“导致的精力分散。",
            "cognitive": "你的认知模式偏向发散性思维，善于从多角度审视问题，"
            "乐于在模糊和不确定性中探索。你习惯将不同领域的知识进行跨界联想，"
            "产生独特的见解。你关注“可能是什么“而非仅仅是“是什么“。",
            "emotional": "面对新刺激时，你更容易产生好奇和兴奋等积极情绪。"
            "然而，当环境过于单调或重复时，你可能会感到无聊和焦躁，"
            "需要持续的智力刺激来保持情绪稳定。",
            "behavior_pref": "在决策时，你更看重可能性和创意性，愿意为新颖的方案承担一定风险。"
            "你不喜欢被条条框框束缚，偏好灵活自主的工作方式，"
            "在需要创意和变革的场景中表现尤为出色。",
            "love": "在亲密关系中，你渴望精神层面的深度交流，喜欢与伴侣一起探索新体验。"
            "你可能对伴侣的智力和创造力有较高期待，希望关系中有持续的思想碰撞和成长。",
        },
        "low": {
            "level_name": "务实稳健",
            "summary": "你更注重实际和当下，偏好具体、熟悉和经过验证的事物。"
            "你做事脚踏实地，重视传统和经验，对过于抽象或前卫的想法持谨慎态度。"
            "你倾向于用已知有效的方式处理问题，追求确定的成果。",
            "behavior": "你倾向于用经过验证的方法解决问题，重视秩序和稳定。"
            "你可能对频繁的变化感到不适，更愿意在熟悉的领域深耕。"
            "你做事讲求实际效果，不喜欢空谈理论。",
            "advantage": "脚踏实地、执行力强、专注务实、判断力稳健、对细节把控到位",
            "weakness": "可能对创新和变化反应较慢，有时过于保守而错失机会，"
            "在面对全新挑战时可能需要更多时间适应，思维灵活度有待提升",
            "growth": "在保持务实优势的同时，可以适度尝试接触新观点和新方法。"
            "不必一次性做出巨大改变，可以从小范围的尝试开始，"
            "逐步拓宽认知边界，培养对新事物的接纳能力。",
            "cognitive": "你的认知模式偏向收敛性思维，善于聚焦核心问题，"
            "运用已有经验和知识高效解决实际问题。你重视逻辑的严密性和结论的可操作性，"
            "关注“如何用“而非“还有什么可能“。",
            "emotional": "你在面对变化和不确定性时可能感到不安，偏好稳定可预测的环境。"
            "当处于熟悉的情境中时，你表现得更加从容自信，"
            "情绪波动较小，内心状态相对平稳。",
            "behavior_pref": "在决策时，你更看重可行性和过往经验，倾向于选择经过验证的方案。"
            "你偏好结构清晰、目标明确的工作方式，"
            "在需要稳定输出和质量把控的场景中表现尤为出色。",
            "love": "在亲密关系中，你重视稳定和安全感，偏好传统的关系模式。"
            "你通过实际行动表达关爱，是可靠而踏实的伴侣，"
            "为关系提供坚实的物质和情感基础。",
        },
    },
    "C": {
        "high": {
            "level_name": "高度尽责",
            "summary": "你是一个高度自律和有责任感的人。你做事有计划、有条理，"
            "对目标有清晰的规划并坚持执行。你重视承诺，追求质量，"
            "不会轻易半途而废，是团队中值得信赖的支柱。",
            "behavior": "你善于制定计划并严格执行，对细节一丝不苟。"
            "你做事有始有终，不会拖延或敷衍，对自己的工作质量有较高标准。"
            "你习惯提前准备，很少临时抱佛脚。",
            "advantage": "自律性强、执行力出色、可靠性高、目标导向清晰、善于规划和时间管理",
            "weakness": "可能因追求完美而给自己和他人过大压力，有时过于死板缺乏灵活，"
            "对突发变化适应较慢，可能因过度关注细节而忽视全局",
            "growth": "在保持高标准的同时，学会适度“放过自己“。"
            "可以区分“必须完美“和”足够好即可“的任务，"
            "将精力集中在真正重要的事情上，培养对不确定性的容忍度。",
            "cognitive": "你的认知模式偏向结构化和系统化，善于将复杂任务拆解为可管理的步骤。"
            "你重视逻辑顺序和因果关系，在思考问题时习惯从目标倒推行动计划，"
            "确保每一步都指向最终结果。",
            "emotional": "你对自己的表现有较高的内在标准，当未能达到预期时可能产生自责和焦虑。"
            "你倾向于通过“做些什么“来缓解情绪，用行动而非倾诉来应对压力，"
            "在完成任务后才能感到真正的放松。",
            "behavior_pref": "在决策时，你更看重可行性和完成度，倾向于制定详细的计划后再行动。"
            "你偏好有明确标准和反馈的工作环境，"
            "在需要质量把控和项目管理的场景中表现尤为出色。",
            "love": "在亲密关系中，你是一个可靠而有责任感的伴侣。"
            "你重视承诺，会认真经营关系，为未来做长远规划。"
            "但需注意不要让“任务感“取代了感情的自然流露。",
        },
        "low": {
            "level_name": "灵活随性",
            "summary": "你是一个灵活而随性的人，不喜欢被严格的计划和规则束缚。"
            "你适应能力强，能随遇而安，对突发事件有较好的应变能力。"
            "你更关注当下体验，而非长远规划。",
            "behavior": "你做事灵活变通，不喜欢死板的流程。"
            "你可能对细节和计划不够重视，更倾向于“走一步看一步“。"
            "你能够在混乱中找到方向，但有时会因为缺乏规划而手忙脚乱。",
            "advantage": "灵活性强、适应能力好、心态轻松、不拘小节、能在变化中快速调整",
            "weakness": "可能因缺乏规划而影响效率和产出，时间管理能力有待加强，"
            "有时做事有始无终，对承诺的执行力不稳定，容易被外界干扰分心",
            "growth": "在保持灵活性的同时，可以有意识地建立一些基础结构。"
            "不必追求完美计划，但可以设定关键节点和最低标准，"
            "用“最小可行计划“来提升执行力和可靠性。",
            "cognitive": "你的认知模式偏向直觉和整体性，善于捕捉大方向而非纠结细节。"
            "你在思考问题时更依赖灵感和当下感受，而非系统化的分析。"
            "这种模式让你在需要快速反应的场景中表现灵活。",
            "emotional": "你对未完成任务的焦虑感相对较低，心态较为放松。"
            "然而，当被迫进入高度结构化和高压的环境时，你可能感到不适和受限，"
            "需要一定的自由空间来保持心理舒适。",
            "behavior_pref": "在决策时，你更看重当下的直觉和感受，倾向于边做边调整而非提前规划一切。"
            "你偏好灵活自主、容许变化的工作方式，"
            "在需要快速应变和创意发挥的场景中表现更为自如。",
            "love": "在亲密关系中，你带来轻松和惊喜，不喜欢被太多规则束缚。"
            "你享受当下的相处时光，但需注意在关系中的稳定性和可靠性，"
            "避免让对方觉得你“不靠谱“。",
        },
    },
    "E": {
        "high": {
            "level_name": "外向活跃",
            "summary": "你是一个精力充沛、热情开朗的人。你享受社交互动，"
            "在人群中感到充电而非消耗。你善于表达自己，乐于与人交流，"
            "是天生的沟通者和氛围带动者。",
            "behavior": "你主动与人交往，在社交场合中如鱼得水。"
            "你说话直接、表达丰富，善于调动气氛。"
            "你喜欢参与各种活动，对外部世界充满热情。",
            "advantage": "社交能力强、沟通表达出色、领导力突出、行动力旺盛、善于激励他人",
            "weakness": "可能因过度社交而忽视深度思考，有时说话做事不够谨慎，"
            "在独处时可能感到不安或无聊，对需要长时间专注的任务缺乏耐心",
            "growth": "在享受社交的同时，可以有意识地培养独处和深度思考的能力。"
            "定期给自己留出“安静时间“进行反思和充电，"
            "让外向的能量与内在的深度形成平衡。",
            "cognitive": "你的认知模式偏向“边说边想”，通过交流和讨论来理清思路。"
            "你善于从他人的反馈中获取信息和灵感，"
            "在群体讨论中的思维活跃度明显高于独处时。",
            "emotional": "你的情绪外露且变化较快，容易因外界事件产生即时的情绪反应。"
            "你在社交互动中获得能量和积极情绪，而在长时间独处后可能感到低落。"
            "你倾向于通过倾诉和交流来处理负面情绪。",
            "behavior_pref": "在决策时，你倾向于快速行动，“先做再说“。"
            "你偏好充满互动和变化的工作环境，"
            "在需要团队协作、公开表达和快速推进的场景中表现尤为出色。",
            "love": "在亲密关系中，你热情主动，善于表达爱意。"
            "你希望与伴侣共享丰富的社交生活，但需注意给对方足够的独处空间，"
            "不要将自己的社交节奏强加于伴侣。",
        },
        "low": {
            "level_name": "内敛沉静",
            "summary": "你是一个内敛而沉静的人，偏好独处或小范围的深度交流。"
            "你在社交中消耗能量，需要独处时间来恢复。"
            "你做事沉稳，不急于表达，善于倾听和观察。",
            "behavior": "你不喜欢成为焦点，在大型社交场合中可能感到不自在。"
            "你说话谨慎，深思熟虑后才开口。"
            "你更喜欢一对一的深度交流，而非群体社交。",
            "advantage": "善于深度思考、倾听能力强、做事沉稳、独立性高、观察力敏锐",
            "weakness": "可能在社交场合中不够主动，有时被误解为冷漠或疏离，"
            "在需要公开表达的场合可能感到不适，团队合作中的存在感有待提升",
            "growth": "在保持内敛特质的同时，可以适度锻炼公开表达和社交主动性。"
            "不必勉强自己成为“社交达人”，但可以掌握基本的社交技能，"
            "在关键时刻能够有效传达自己的想法。",
            "cognitive": "你的认知模式偏向“先想后说”，在内心进行充分思考后再表达。"
            "你善于深度分析和独立思考，在安静环境中的思维质量最高。"
            "你关注事物的内在逻辑而非表面现象。",
            "emotional": "你的情绪较为内敛，不易外露。你在独处时感到充电和恢复，"
            "在过度社交后可能感到疲惫和烦躁。你倾向于通过内省而非倾诉来处理情绪，"
            "情绪反应相对缓慢但持久。",
            "behavior_pref": "在决策时，你更倾向于充分思考后再行动，“谋定而后动“。"
            "你偏好安静、独立的工作环境，"
            "在需要深度分析、独立研究和精细操作的场景中表现尤为出色。",
            "love": "在亲密关系中，你是一个深沉而忠诚的伴侣。"
            "你用行动而非言语表达爱意，重视关系的深度而非广度。"
            "你需要伴侣理解你对独处空间的需求，不要将内敛误解为冷淡。",
        },
    },
    "A": {
        "high": {
            "level_name": "温和利他",
            "summary": "你是一个温暖、友善且富有同理心的人。你重视人际和谐，"
            "乐于帮助他人，善于换位思考。你信任他人，倾向于合作而非竞争，"
            "是团队中的润滑剂和凝聚力量。",
            "behavior": "你主动关心他人，乐于伸出援手。你避免冲突，"
            "在矛盾中倾向于寻求妥协和共赢。你说话温和，"
            "善于倾听，让人感到被理解和接纳。",
            "advantage": "同理心强、团队协作出色、善于调解冲突、值得信赖、人际关系融洽",
            "weakness": "可能因过度迁就他人而忽视自身需求，有时难以拒绝不合理要求，"
            "在竞争环境中可能不够果断，可能因回避冲突而积累问题",
            "growth": "在保持善良品质的同时，学会设立健康的边界。"
            "可以练习在必要时说“不”，区分“利他“与”自我牺牲”，"
            "确保在关爱他人的同时也不亏待自己。",
            "cognitive": "你的认知模式偏向关系导向，在分析问题时习惯考虑各方立场和感受。"
            "你善于理解他人的动机和需求，在决策时不仅关注逻辑正确，"
            "更关注方案对人的影响。",
            "emotional": "你对他人情绪高度敏感，容易产生共情反应。"
            "你在和谐的人际环境中感到舒适，在冲突和对立中感到不适和焦虑。"
            "你倾向于通过包容和退让来恢复情绪平衡。",
            "behavior_pref": "在决策时，你更看重方案对各方的影响，追求共赢结果。"
            "你偏好合作、支持性的工作环境，"
            "在需要团队协调、客户服务和人文关怀的场景中表现尤为出色。",
            "love": "在亲密关系中，你是一个温柔体贴的伴侣，善于照顾对方的感受。"
            "你重视关系的和谐与稳定，愿意为对方付出。"
            "但需注意不要在关系中失去自我，保持独立的人格边界。",
        },
        "low": {
            "level_name": "独立务实",
            "summary": "你是一个务实、独立且有主见的人。你重视客观事实和效率，"
            "不太受他人情感的影响。你倾向于直言不讳，"
            "在竞争中表现出色，以结果为导向。",
            "behavior": "你说话直接，不绕弯子。你重视效率和结果，"
            "不太在意是否“讨好“他人。在团队合作中，你更关注任务完成，"
            "而非人际关系的维护。",
            "advantage": "客观理性、决策果断、抗压能力强、竞争力突出、以结果为导向",
            "weakness": "可能在人际沟通中显得生硬或冷漠，有时不够顾及他人感受，"
            "在团队合作中可能引发摩擦，亲和力和共情能力有待提升",
            "growth": "在保持务实和果断的同时，可以有意识地培养同理心和沟通技巧。"
            "学会在表达观点时考虑他人的感受，"
            "在追求效率的同时兼顾团队氛围，让“硬实力“与”软技能“平衡发展。",
            "cognitive": "你的认知模式偏向任务导向，在分析问题时聚焦于事实、数据和逻辑。"
            "你善于发现问题的关键症结，在决策时不太受人际关系因素的干扰，"
            "更关注方案的客观有效性和执行效率。",
            "emotional": "你对他人的情绪反应相对钝感，不易被他人的情绪所左右。"
            "在冲突和竞争中你能保持冷静，但你可能忽视他人的情感需求，"
            "在需要情感共鸣的场合中显得疏离。",
            "behavior_pref": "在决策时，你更看重客观效果和效率，追求最优解。"
            "你偏好目标明确、竞争性强的环境，"
            "在需要果断决策、攻坚克难和高绩效输出的场景中表现尤为出色。",
            "love": "在亲密关系中，你是一个直接而务实的伴侣。"
            "你用实际行动而非甜言蜜语表达爱，重视关系的实质而非形式。"
            "但需注意培养情感表达能力，让对方感受到你的关心。",
        },
    },
    "N": {
        "high": {
            "level_name": "敏感细腻",
            "summary": "你是一个情感细腻、感受深刻的人。你对环境变化和他人的情绪反应敏感，"
            "容易体验到焦虑、担忧等负面情绪。然而，这种敏感性也赋予了你"
            "深刻的洞察力和丰富的内心世界。",
            "behavior": "你对压力和不确定性反应较强，容易感到紧张和焦虑。"
            "你可能反复思考过去的事情或担忧未来，"
            "在情绪波动时需要时间来恢复平静。",
            "advantage": "洞察力深刻、感受力丰富、危机意识强、细节感知敏锐、自我反思能力强",
            "weakness": "可能因过度焦虑而影响决策和行动，情绪波动较大，" "抗压能力有待加强，容易因小事而陷入内耗",
            "growth": "在接纳自身敏感特质的同时，学习有效的情绪管理技巧。"
            "可以通过正念冥想、规律运动和认知重构来降低焦虑水平，"
            "将敏感性转化为洞察力而非内耗的源泉。",
            "cognitive": "你的认知模式带有较强的情绪色彩，对威胁和风险信息更为敏感。"
            "你善于察觉他人忽略的细节和微妙变化，"
            "但也容易因过度解读而产生认知偏差，需要练习区分“事实“与”想象“。",
            "emotional": "你的情绪反应较为强烈和频繁，容易体验焦虑、担忧、悲伤等负面情绪。"
            "你的情绪恢复周期较长，在压力下可能影响判断力和行动力。"
            "然而，你也因此能深刻体验积极情绪，对美好事物的感受更加丰富。",
            "behavior_pref": "在决策时，你可能因担心风险而倾向于保守或推迟决定。"
            "你偏好稳定、可预测的环境，在低压和有支持的工作场景中表现更好。"
            "需要培养在压力下保持冷静和行动的能力。",
            "love": "在亲密关系中，你是一个深情而敏感的伴侣。"
            "你对伴侣的情绪变化高度敏感，但也容易因小事而感到不安。"
            "你需要一个能给予安全感和稳定支持的伴侣，"
            "同时也要学习管理自己的焦虑情绪。",
        },
        "low": {
            "level_name": "稳定从容",
            "summary": "你是一个情绪稳定、从容自信的人。你在面对压力和变化时能保持冷静，"
            "不易被负面情绪困扰。你心态积极，恢复力强，"
            "是周围人的稳定力量。",
            "behavior": "你在压力下依然能保持冷静和理性，不会轻易慌张。"
            "你不太纠结于过去，也不过度担忧未来，"
            "能够专注于当下需要做的事情。",
            "advantage": "情绪稳定、抗压能力强、心态积极、恢复力出色、在危机中保持冷静",
            "weakness": "可能对他人的情绪反应不够敏感，有时显得“过于淡定”，"
            "可能低估风险或忽视潜在问题，在需要紧迫感时可能缺乏动力",
            "growth": "在保持从容稳定的同时，可以适度培养对风险的敏感度。"
            "不必变得焦虑，但可以对潜在问题保持合理的警觉，"
            "避免因过度自信而忽视重要的预警信号。",
            "cognitive": "你的认知模式冷静而理性，不易被情绪干扰判断。"
            "你在压力下依然能保持清晰的思维，善于从客观角度分析问题。"
            "你可能对他人的情绪信号不够敏感，需要有意识地关注情感维度。",
            "emotional": "你的情绪基线稳定，波动幅度小，负面情绪恢复快。"
            "你在高压环境中依然能保持内心的平静，不易被外界事件击垮。"
            "你可能对他人的情感需求不够敏感，需要培养情感共鸣能力。",
            "behavior_pref": "在决策时，你能保持冷静和理性，不易受情绪影响。"
            "你偏好有一定挑战和压力的环境，"
            "在需要危机处理、高压决策和稳定输出的场景中表现尤为出色。",
            "love": "在亲密关系中，你是一个稳定而可靠的伴侣，为关系提供安全感。"
            "你在冲突中能保持冷静，不易被情绪左右。"
            "但需注意培养对伴侣情绪的敏感度，不要让对方觉得你“冷漠“。",
        },
    },
}


# ===========================================================================
# 辅助函数
# ===========================================================================


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


def _count_words(html_content: str) -> int:
    """统计 HTML 内容的字数（去除标签后的有效字符数）。

    :param html_content: HTML 格式的内容字符串
    :return: 字数
    """
    text: str = re.sub(r"<[^>]+>", "", html_content)
    text = re.sub(r"\s+", "", text)
    return len(text)


def _build_chapter(chapter_id: int, title: str, content: str) -> dict[str, object]:
    """构建章节字典。

    :param chapter_id: 章节编号（1-12）
    :param title: 章节标题
    :param content: HTML 格式的内容
    :return: 章节字典
    """
    return {
        "chapter_id": chapter_id,
        "title": title,
        "content": content,
        "word_count": _count_words(content),
    }


def _truncate_content(content: str, ratio: float = PREVIEW_RATIO) -> str:
    """截取 HTML 内容的前 ratio 比例作为预览片段。

    :param content: 完整 HTML 内容
    :param ratio: 截取比例
    :return: 截取后的预览片段（HTML 段落）
    """
    text: str = re.sub(r"<[^>]+>", "", content)
    text = re.sub(r"\s+", "", text)
    truncate_len: int = max(PREVIEW_MIN_CHARS, int(len(text) * ratio))
    truncated: str = text[:truncate_len]
    return f"<p>{truncated}……</p>"


def _normalize_ocean_scores(
    ocean_scores: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """将 OCEAN 分数列表归一化为以维度为 key 的字典。

    :param ocean_scores: OCEAN 分数列表
    :return: 以维度（O/C/E/A/N）为 key 的分数字典
    """
    result: dict[str, dict[str, object]] = {}
    for score in ocean_scores:
        dim: str = str(score.get("dimension", ""))
        if dim:
            result[dim] = score
    return result


def _get_archetype(archetype_id: int) -> PersonalityArchetype:
    """从数据库获取原型配置。

    :param archetype_id: 原型 ID（1-32）
    :return: PersonalityArchetype 模型实例
    :raises PersonalityArchetype.DoesNotExist: 原型不存在
    """
    from personality.models import PersonalityArchetype

    return PersonalityArchetype.objects.get(archetype_id=archetype_id)


def _get_default_ocean_scores(archetype: PersonalityArchetype) -> list[dict[str, object]]:
    """根据原型的 high/low 区间推导默认 OCEAN 分数（用于预览模式）。

    :param archetype: 原型模型实例
    :return: OCEAN 分数列表
    """
    ranges: list[tuple[str, str]] = [
        ("O", archetype.o_range),
        ("C", archetype.c_range),
        ("E", archetype.e_range),
        ("A", archetype.a_range),
        ("N", archetype.n_range),
    ]
    scores: list[dict[str, object]] = []
    for dim, level in ranges:
        percentile: float = DEFAULT_HIGH_PERCENTILE if level == "high" else DEFAULT_LOW_PERCENTILE
        scores.append(
            {
                "dimension": dim,
                "percentile": percentile,
                "is_high": level == "high",
                "level": _percentile_to_level(percentile),
            }
        )
    return scores


def _generate_spectrum_data(
    ocean_scores: list[dict[str, object]],
) -> list[dict[str, object]]:
    """根据 OCEAN 分数生成色彩光谱数据。

    :param ocean_scores: OCEAN 分数列表
    :return: 色彩光谱条数据列表
    """

    score_map: dict[str, dict[str, object]] = _normalize_ocean_scores(ocean_scores)
    spectrum_items: list[dict[str, object]] = []

    color_map: dict[str, dict[int, str]] = {
        "O": {1: "#D4C3F0", 2: "#B89FE0", 3: "#9B7ED8", 4: "#8266C2", 5: "#6B4EAB"},
        "C": {1: "#B0D4E0", 2: "#8AB5C6", 3: "#5a96b1", 4: "#4A86A1", 5: "#3A7691"},
        "E": {1: "#B0D5C0", 2: "#88BD9F", 3: "#5ea67e", 4: "#4E966E", 5: "#3E865E"},
        "A": {1: "#F0D9A0", 2: "#E5C67C", 3: "#deb45c", 4: "#CEA44C", 5: "#BE943C"},
        "N": {1: "#F0A590", 2: "#E88870", 3: "#e17055", 4: "#D16045", 5: "#C15035"},
    }

    for dim in ["O", "C", "E", "A", "N"]:
        score_data: dict[str, object] = score_map.get(dim, {"percentile": 50.0})
        percentile: float = float(score_data.get("percentile", 50.0))
        level: int = _percentile_to_level(percentile)
        color: str = color_map.get(dim, {}).get(level, "#888888")
        spectrum_items.append(
            {
                "dimension": dim,
                "label": OCEAN_LABELS.get(dim, dim),
                "percentile": round(percentile, 1),
                "level": level,
                "color": color,
                "is_high": percentile > 50.0,
            }
        )

    return spectrum_items


def _get_matching_careers(
    archetype_id: int,
    riasec_code: str,
) -> list[Career]:
    """根据原型 ID 和 RIASEC 码查询匹配职业。

    匹配优先级：同时匹配原型和 RIASEC > 仅匹配原型 > 仅匹配 RIASEC。

    :param archetype_id: 原型 ID
    :param riasec_code: RIASEC 码
    :return: 匹配的职业列表（按优先级排序）
    """
    from careers.models import Career

    all_careers: list[Career] = list(Career.objects.filter(is_active=True))
    riasec_letters: list[str] = [c for c in riasec_code.upper() if c]

    matched: list[tuple[int, Career]] = []
    for career in all_careers:
        arch_match: bool = archetype_id in (career.matching_archetypes or [])
        riasec_match: bool = any(r in (career.matching_riasec_codes or []) for r in riasec_letters)
        if arch_match or riasec_match:
            if arch_match and riasec_match:
                priority: int = 0
            elif arch_match:
                priority = 1
            else:
                priority = 2
            matched.append((priority, career))

    matched.sort(key=lambda x: x[0])
    return [c for _, c in matched]


def _get_partner_archetypes(
    best_partner_ids: list[int],
) -> list[PersonalityArchetype]:
    """获取最佳搭档原型列表。

    :param best_partner_ids: 最佳搭档原型 ID 列表
    :return: 原型模型实例列表
    """
    from personality.models import PersonalityArchetype

    if not best_partner_ids:
        return []

    return list(PersonalityArchetype.objects.filter(archetype_id__in=best_partner_ids))


def _get_adjacent_archetypes(
    archetype: PersonalityArchetype,
) -> list[PersonalityArchetype]:
    """获取与当前原型仅差一个维度的相邻原型。

    :param archetype: 当前原型
    :return: 相邻原型列表
    """
    from personality.models import PersonalityArchetype

    current_ranges: list[str] = [
        archetype.o_range,
        archetype.c_range,
        archetype.e_range,
        archetype.a_range,
        archetype.n_range,
    ]
    all_others: list[PersonalityArchetype] = list(
        PersonalityArchetype.objects.exclude(archetype_id=archetype.archetype_id)
    )

    adjacent: list[PersonalityArchetype] = []
    for other in all_others:
        other_ranges: list[str] = [
            other.o_range,
            other.c_range,
            other.e_range,
            other.a_range,
            other.n_range,
        ]
        diff_count: int = sum(1 for a, b in zip(current_ranges, other_ranges, strict=False) if a != b)
        if diff_count == 1:
            adjacent.append(other)

    return adjacent


def _get_dimension_level(dim: str, score_map: dict[str, dict[str, object]]) -> str:
    """获取指定维度的 high/low 标记。

    :param dim: 维度（O/C/E/A/N）
    :param score_map: 归一化后的分数字典
    :return: "high" 或 "low"
    """
    score_data: dict[str, object] = score_map.get(dim, {})
    is_high: bool = bool(score_data.get("is_high", False))
    if not is_high:
        percentile: float = float(score_data.get("percentile", 0.0))
        is_high = percentile > 50.0
    return "high" if is_high else "low"


def _get_riasec_description(riasec_code: str) -> str:
    """根据 RIASEC 码生成兴趣类型描述。

    :param riasec_code: RIASEC 码（如 "IAS"）
    :return: 兴趣类型描述文本
    """
    if not riasec_code:
        return "你的职业兴趣类型尚未确定，建议完成 RIASEC 测评后获取更精准的职业分析。"

    parts: list[str] = []
    for char in riasec_code.upper():
        full_name: str = RIASEC_FULL_NAMES.get(char, "")
        desc: str = RIASEC_DESCRIPTIONS.get(char, "")
        if full_name and desc:
            parts.append(f"<strong>{full_name}（{char}）</strong>：{desc}")

    if not parts:
        return "你的职业兴趣类型尚未确定。"

    return "；".join(parts) + "。"


# ===========================================================================
# 章节生成器（12 章）
# ===========================================================================


def _generate_chapter_1(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 1 章：你的人格画像速览。"""
    spectrum: list[dict[str, object]] = _generate_spectrum_data(ocean_scores)

    spectrum_html: str = "".join(
        f'<li><span style="color:{item["color"]}">●</span> '
        f'{item["label"]}：{item["percentile"]}%（{"高" if item["is_high"] else "低"}）</li>'
        for item in spectrum
    )

    content: str = f"""
    <h3>{archetype.archetype_name}</h3>
    <p><strong>原型编号</strong>：#{archetype.archetype_id}（共 32 种原型）</p>
    <p><strong>一句话描述</strong>：{archetype.archetype_slogan}</p>
    <p><strong>维度组合码</strong>：{archetype.archetype_code}</p>
    <p><strong>RIASEC 职业兴趣码</strong>：{riasec_code or "待确定"}</p>
    <p><strong>稀有度</strong>：{archetype.rarity}（人群中约 {archetype.rarity_percentage}%）</p>
    <h4>五维度色彩光谱</h4>
    <ul>{spectrum_html}</ul>
    <p>你的色彩光谱由大五人格五维度的百分位决定。每个维度的色深代表了你在该维度上的倾向强度——
    颜色越深，说明你在这个维度上的特征越明显。这五个维度的组合构成了你独一无二的人格画像
    「{archetype.archetype_name}」，在 32 种原型中仅占约 {archetype.rarity_percentage}% 的人口比例。</p>
    <p>这一画像融合了你的{OCEAN_LABELS.get('O', '')}、{OCEAN_LABELS.get('C', '')}、
    {OCEAN_LABELS.get('E', '')}、{OCEAN_LABELS.get('A', '')}和{OCEAN_LABELS.get('N', '')}
    五个维度的特征，结合霍兰德职业兴趣码「{riasec_code or "待确定"}」，
    形成了你对世界独特的感知方式和行为模式。接下来的章节将逐层深入解读你的人格全貌。</p>
    """
    return _build_chapter(1, CHAPTER_TITLES[0], content)


def _generate_chapter_2(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 2 章：人格特征分析。"""
    paragraphs: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        score_data: dict[str, object] = score_map.get(dim, {})
        percentile: float = float(score_data.get("percentile", 50.0))
        label: str = OCEAN_LABELS.get(dim, dim)
        paragraphs.append(
            f"<h4>{label}（{dim}）— {data['level_name']}</h4>"
            f"<p>百分位：{percentile:.1f}%</p>"
            f"<p>{data['summary']}</p>"
            f"<p><strong>行为表现</strong>：{data['behavior']}</p>"
        )
    content: str = "\n".join(paragraphs)
    content += (
        f"<p>综合来看，你作为「{archetype.archetype_name}」，"
        f"上述五个维度的组合赋予了你独特的行为风格和人际模式。"
        f"这些特征没有好坏之分，关键在于你如何在不同的场景中灵活运用它们，"
        f"发挥优势、管理盲点，实现自我成长。</p>"
    )
    return _build_chapter(2, CHAPTER_TITLES[1], content)


def _generate_chapter_3(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 3 章：人口比例。"""
    adjacent: list[PersonalityArchetype] = _get_adjacent_archetypes(archetype)

    adjacent_html: str = ""
    if adjacent:
        adjacent_items: list[str] = [
            f"<li>{a.archetype_name}（{a.rarity_percentage}%）— {a.archetype_slogan}</li>" for a in adjacent[:5]
        ]
        adjacent_html = f"<ul>{''.join(adjacent_items)}</ul>"

    content: str = f"""
    <h3>你的原型在人群中的分布</h3>
    <p>根据大五人格五维度的高低组合，人群被划分为 32 种原型。你所属的「{archetype.archetype_name}」
    在人群中约占 <strong>{archetype.rarity_percentage}%</strong>，属于<strong>{archetype.rarity}</strong>类型。</p>
    <p>这意味着在你身边每 100 个人中，大约只有 {archetype.rarity_percentage} 个人与你拥有相同的人格原型。
    {"这种稀有度既意味着你的特质组合较为独特，也可能意味着在日常生活中找到“同类“需要更多的耐心。" if archetype.rarity in ("稀有", "极稀有") else "这种占比说明你的特质组合在人群中相对常见，你并不孤单，有许多人与你拥有相似的人格模式。"}</p>
    <h4>与相邻原型的差异</h4>
    <p>相邻原型是指在五维度中仅有一个维度与你不同的原型。它们与你“最相似但又不同”，
    理解这些差异有助于你更精确地认识自己的独特之处。</p>
    {adjacent_html if adjacent_html else "<p>暂无相邻原型数据。</p>"}
    <p>通过与相邻原型的对比可以看出，你的核心特征在于
    {OCEAN_LABELS.get('O', '')}、{OCEAN_LABELS.get('C', '')}、{OCEAN_LABELS.get('E', '')}、
    {OCEAN_LABELS.get('A', '')}、{OCEAN_LABELS.get('N', '')}五个维度的特定组合方式。
    正是这种组合方式——而非任何单一维度——定义了你作为「{archetype.archetype_name}」的独特性。</p>
    """
    return _build_chapter(3, CHAPTER_TITLES[2], content)


def _generate_chapter_4(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 4 章：相同人格名人。"""
    famous_people: list[str] = list(archetype.famous_people or [])
    if not famous_people:
        famous_people = ["暂无数据"]

    people_html: str = "".join(f"<li>{name}</li>" for name in famous_people)

    content: str = f"""
    <h3>与你同型的知名人物</h3>
    <p>以下知名人物与你拥有相同的人格原型「{archetype.archetype_name}」。当然，人格类型只是理解一个人的一种视角，
    每个人的成长环境、经历和选择都塑造了其独特的人生轨迹。这些名人的共同特质可以为你提供参照和启发。</p>
    <ul>{people_html}</ul>
    <h4>共同特质分析</h4>
    <p>这些人物之所以被归入同一原型，是因为他们在
    {OCEAN_LABELS.get('O', '')}、{OCEAN_LABELS.get('C', '')}、{OCEAN_LABELS.get('E', '')}、
    {OCEAN_LABELS.get('A', '')}、{OCEAN_LABELS.get('N', '')}五个维度上呈现出相似的高低组合模式。
    他们可能在以下方面与你具有共通之处：</p>
    <p>首先，他们都展现了「{archetype.archetype_slogan}」这一核心特质。这意味着在面对挑战和机遇时，
    他们倾向于采取与你类似的认知方式和行动策略。其次，他们在各自领域中取得成就的路径，
    往往与其人格特质高度匹配——这正是“性格决定命运“的一种体现。</p>
    <p>了解这些同型人物的人生故事和决策方式，可以帮助你更好地理解自己的潜力和发展方向。
    你可以从他们的经历中汲取灵感，同时也需记住：你的人生由你自己书写，原型只是起点而非终点。</p>
    """
    return _build_chapter(4, CHAPTER_TITLES[3], content)


def _generate_chapter_5(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 5 章：人格优势。"""
    advantage_items: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        label: str = OCEAN_LABELS.get(dim, dim)
        advantage_items.append(f"<li><strong>{label}（{data['level_name']}）</strong>：{data['advantage']}</li>")

    career_dirs: list[str] = list(archetype.career_directions or [])
    career_html: str = "、".join(career_dirs[:5]) if career_dirs else "待分析"

    content: str = f"""
    <h3>你的核心人格优势</h3>
    <p>作为「{archetype.archetype_name}」，你的人格五维度组合为你带来了以下核心优势。
    这些优势是你天然的“能力底座”，在合适的场景中将转化为强大的竞争力。</p>
    <ul>{''.join(advantage_items)}</ul>
    <h4>优势组合效应</h4>
    <p>单个维度的优势固然重要，但真正的力量来自于维度的<strong>组合效应</strong>。
    你的{OCEAN_LABELS.get('O', '')}与{OCEAN_LABELS.get('C', '')}的组合，
    决定了你是“有创意且能落地“还是“有创意但难执行“或”能执行但缺创意“。
    你的{OCEAN_LABELS.get('E', '')}与{OCEAN_LABELS.get('A', '')}的组合，
    则塑造了你的社交风格——是“温暖的外向者“还是“独立的行动派“。</p>
    <p>这种独特的组合方式使你在以下方向具有天然优势：{career_html}。
    在这些领域中，你的人格特质能够最大程度地转化为实际成就和职业满足感。</p>
    <p>认识到自己的优势是发挥它们的第一步。建议你有意识地在工作和生活中创造发挥这些优势的机会，
    同时寻找能够互补的伙伴来弥补你的短板，形成“1+1>2”的协同效应。</p>
    """
    return _build_chapter(5, CHAPTER_TITLES[4], content)


def _generate_chapter_6(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 6 章：人格劣势。"""
    weakness_items: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        label: str = OCEAN_LABELS.get(dim, dim)
        weakness_items.append(f"<li><strong>{label}（{data['level_name']}）</strong>：{data['weakness']}</li>")

    content: str = f"""
    <h3>潜在盲点与需注意的短板</h3>
    <p>每个人都有盲点。作为「{archetype.archetype_name}」，你的人格组合在带来优势的同时，
    也伴随着以下需要警觉的潜在短板。认识它们并非为了否定自己，而是为了更智慧地管理自己。</p>
    <ul>{''.join(weakness_items)}</ul>
    <h4>盲点的交互效应</h4>
    <p>值得注意的是，多个维度的短板可能产生<strong>交互放大效应</strong>。
    例如，如果你的外向性较低且宜人性也较低，可能在团队沟通中显得既不主动又不够柔和，
    导致人际摩擦被放大。如果你的尽责性较低且神经质较高，则可能在“拖延“和”焦虑“之间形成恶性循环。</p>
    <p>识别这些交互模式是管理盲点的关键。建议你：</p>
    <p>第一，在关键决策前寻求他人反馈，弥补自己的认知盲区；</p>
    <p>第二，在短板影响较大的场景中，主动寻找互补的伙伴或工具来辅助；</p>
    <p>第三，将精力聚焦于“管理“而非“消除“短板——某些特质本身就是一把双刃剑，
    管理好它们的负面影响即可，不必强求全面改变。</p>
    """
    return _build_chapter(6, CHAPTER_TITLES[5], content)


def _generate_chapter_7(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 7 章：成长建议。"""
    growth_items: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        label: str = OCEAN_LABELS.get(dim, dim)
        growth_items.append(f"<li><strong>{label}</strong>：{data['growth']}</li>")

    content: str = f"""
    <h3>针对性发展路径与行动建议</h3>
    <p>基于你「{archetype.archetype_name}」的人格特征，以下是从五个维度出发的成长建议。
    这些建议旨在帮助你在保持核心优势的同时，有意识地拓展自己的舒适区。</p>
    <ul>{''.join(growth_items)}</ul>
    <h4>阶段性行动计划</h4>
    <p>成长不是一蹴而就的，建议你采用<strong>"小步快跑、持续迭代"</strong>的方式：</p>
    <p><strong>短期（1-3 个月）</strong>：从上述建议中选择 1-2 个最迫切的方向，制定具体可执行的行动计划。
    例如，如果你需要提升社交主动性，可以设定“每周主动与一位新同事交流“的微小目标。</p>
    <p><strong>中期（3-6 个月）</strong>：在短期习惯初步建立后，逐步增加挑战难度和覆盖范围。
    定期回顾进展，根据实际效果调整策略。</p>
    <p><strong>长期（6-12 个月）</strong>：将新的行为模式内化为自然习惯，同时开启下一阶段的成长主题。
    成长是螺旋上升的过程，每一次迭代都让你更接近“最好的自己“。</p>
    <p>记住，人格特质具有一定的稳定性，但绝非一成不变。神经科学研究表明，
    大脑具有终身可塑性——只要你持续刻意练习，改变就会发生。</p>
    """
    return _build_chapter(7, CHAPTER_TITLES[6], content)


def _generate_chapter_8(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 8 章：大五人格五维度深度解读。"""
    sections: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        _label: str = OCEAN_LABELS.get(dim, dim)
        full_name: str = OCEAN_FULL_NAMES.get(dim, dim)
        score_data: dict[str, object] = score_map.get(dim, {})
        percentile: float = float(score_data.get("percentile", 50.0))

        sections.append(f"""
        <h4>{full_name} — {data['level_name']}（百分位 {percentile:.1f}%）</h4>
        <p><strong>认知模式</strong>：{data['cognitive']}</p>
        <p><strong>情绪反应</strong>：{data['emotional']}</p>
        <p><strong>行为偏好</strong>：{data['behavior_pref']}</p>
        """)

    content: str = f"""
    <h3>大五人格五维度深度解读</h3>
    <p>大五人格模型（Big Five）是当代人格心理学最成熟、最具科学证据支撑的人格理论框架。
    它将人格分为五个相对独立的维度：开放性（O）、尽责性（C）、外向性（E）、宜人性（A）和神经质（N）。
    以下逐一深入解读你在每个维度上的认知模式、情绪反应和行为偏好。</p>
    {''.join(sections)}
    <h4>五维度的协同与张力</h4>
    <p>大五人格的五个维度并非孤立存在，它们之间的<strong>协同与张力</strong>共同构成了你的人格动态系统。
    例如，高开放性与高尽责性的组合让你既有创意又能落地；而高外向性与低宜人性的组合
    则可能让你成为一个强势但不够亲和的领导者。</p>
    <p>理解这些维度的交互作用，是深度自我认知的关键。它帮助你回答的不只是“我是什么样的人”，
    更是“为什么我是这样的人“以及“我可以如何更好地成为自己“。</p>
    """
    return _build_chapter(8, CHAPTER_TITLES[7], content)


def _generate_chapter_9(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 9 章：人格恋爱专题。"""
    love_items: list[str] = []
    for dim in ["O", "C", "E", "A", "N"]:
        level: str = _get_dimension_level(dim, score_map)
        data: dict[str, str] = DIMENSION_DATA[dim][level]
        label: str = OCEAN_LABELS.get(dim, dim)
        love_items.append(f"<li><strong>{label}（{data['level_name']}）</strong>：{data['love']}</li>")

    e_level: str = _get_dimension_level("E", score_map)
    a_level: str = _get_dimension_level("A", score_map)
    n_level: str = _get_dimension_level("N", score_map)

    if e_level == "high":
        social_style: str = "热情主动"
    else:
        social_style = "内敛深沉"

    if a_level == "high":
        conflict_style: str = "温和包容，倾向于妥协和让步"
    else:
        conflict_style = "直接务实，倾向于就事论事地解决问题"

    if n_level == "high":
        emotional_style: str = "情感丰富而敏感，需要较多的安全感和情感确认"
    else:
        emotional_style = "情绪稳定而从容，为关系提供稳定感"

    content: str = f"""
    <h3>你的人格恋爱专题</h3>
    <p>作为「{archetype.archetype_name}」，你在亲密关系中呈现出独特的表现模式。
    人格特质深刻影响着我们如何选择伴侣、如何表达爱意、如何处理冲突以及如何维护关系的长期稳定。</p>
    <h4>五维度在亲密关系中的表现</h4>
    <ul>{''.join(love_items)}</ul>
    <h4>你的恋爱风格画像</h4>
    <p>综合五个维度，你的恋爱风格可以概括为"<strong>{social_style}</strong>"型。
    在社交互动方面，你{social_style}；在冲突处理方面，你{conflict_style}；
    在情感表达方面，你{emotional_style}。</p>
    <p>这种组合意味着你在关系中既有着独特的魅力，也面临着特定的挑战。
    理解自己的人格如何影响恋爱模式，是建立健康亲密关系的重要一步。
    建议你在选择伴侣时关注互补性——寻找能在你的短板处给予支持、同时欣赏你核心优势的人。</p>
    <p>同时，无论人格类型如何，所有健康的亲密关系都建立在相互尊重、坦诚沟通和持续投入的基础上。
    人格特质影响的是“方式”，而非“能否"——任何人格类型都有能力建立深厚而持久的爱情。</p>
    """
    return _build_chapter(9, CHAPTER_TITLES[8], content)


def _generate_chapter_10(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 10 章：最佳恋爱对象。"""
    best_partner_ids: list[int] = list(archetype.best_partners or [])
    partners: list[PersonalityArchetype] = _get_partner_archetypes(best_partner_ids)

    if partners:
        partner_items: list[str] = []
        for p in partners:
            # 分析互补维度
            partner_ranges: list[tuple[str, str, str]] = [
                ("O", archetype.o_range, p.o_range),
                ("C", archetype.c_range, p.c_range),
                ("E", archetype.e_range, p.e_range),
                ("A", archetype.a_range, p.a_range),
                ("N", archetype.n_range, p.n_range),
            ]
            complementary: list[str] = [
                OCEAN_LABELS.get(dim, dim) for dim, mine, theirs in partner_ranges if mine != theirs
            ]
            similar: list[str] = [OCEAN_LABELS.get(dim, dim) for dim, mine, theirs in partner_ranges if mine == theirs]

            comp_text: str = "、".join(complementary) if complementary else "无明显互补维度"
            sim_text: str = "、".join(similar) if similar else "无明显相似维度"

            partner_items.append(f"""
            <li><strong>{p.archetype_name}</strong>（#{p.archetype_id}，约 {p.rarity_percentage}%）
            — {p.archetype_slogan}
            <br>互补维度：{comp_text}
            <br>相似维度：{sim_text}</li>
            """)
        partner_html = f"<ul>{''.join(partner_items)}</ul>"
    else:
        partner_html = "<p>暂无最佳搭档数据。</p>"

    content: str = f"""
    <h3>最佳恋爱对象推荐</h3>
    <p>基于人格维度的兼容性分析，以下原型与你的「{archetype.archetype_name}」具有天然的互补或共鸣特质，
    是较理想的恋爱对象选择。</p>
    {partner_html}
    <h4>兼容性原理</h4>
    <p>人格兼容性并非简单的“相似相吸“或”互补相吸”，而是两者的动态平衡。</p>
    <p><strong>互补维度</strong>：当对方在你较弱的维度上表现较强时，可以在生活中形成自然的分工与支持。
    例如，如果你尽责性较低而对方较高，对方可以帮助你建立规划和秩序。</p>
    <p><strong>相似维度</strong>：当双方在某些维度上相近时，更容易理解彼此的行为模式和情感需求，
    减少摩擦。例如，双方开放性都高，则更容易在精神层面产生共鸣。</p>
    <p>需要强调的是，人格兼容性只是亲密关系的一个维度。价值观的契合、生活方式的兼容、
    情感投入的深度以及双方共同成长的意愿，同样至关重要——甚至更为重要。
    人格类型提供的是一个“起点参考”，而非“终极答案“。</p>
    """
    return _build_chapter(10, CHAPTER_TITLES[9], content)


def _generate_chapter_11(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 11 章：深度职业专题。"""
    riasec_desc: str = _get_riasec_description(riasec_code)
    career_dirs: list[str] = list(archetype.career_directions or [])
    career_dirs_html: str = "、".join(career_dirs) if career_dirs else "待分析"

    # 根据原型特征分析职业路径
    c_level: str = _get_dimension_level("C", score_map)
    e_level: str = _get_dimension_level("E", score_map)
    o_level: str = _get_dimension_level("O", score_map)

    if o_level == "high" and c_level == "high":
        work_style: str = "你兼具创新思维和执行能力，适合在需要'从 0 到 1'并持续迭代的领域中发展。"
    elif o_level == "high" and c_level == "low":
        work_style = "你创意丰富但执行力有待加强，适合在有完善执行团队支持的环境中发挥创意优势。"
    elif o_level == "low" and c_level == "high":
        work_style = "你务实高效、执行力强，适合在需要稳定输出和质量把控的领域中深耕。"
    else:
        work_style = "你灵活务实，适合在变化较快、不需要高度结构化的环境中发展。"

    if e_level == "high":
        team_role: str = "你适合担任需要大量沟通协调和团队领导的角色。"
    else:
        team_role = "你更适合担任需要深度专注和独立思考的角色。"

    content: str = f"""
    <h3>深度职业专题</h3>
    <p>你的职业发展路径由人格原型「{archetype.archetype_name}」和霍兰德职业兴趣码「{riasec_code or "待确定"}」共同决定。
    前者决定你“如何工作”，后者决定你“想做什么“。</p>
    <h4>霍兰德职业兴趣分析</h4>
    <p>你的 RIASEC 码为「{riasec_code or "待确定"}」，代表你的职业兴趣类型排序：</p>
    <p>{riasec_desc}</p>
    <h4>人格特质与工作风格</h4>
    <p>{work_style}</p>
    <p>{team_role}</p>
    <h4>推荐职业方向</h4>
    <p>基于你的人格原型和职业兴趣，以下方向与你的特质高度匹配：</p>
    <p>{career_dirs_html}</p>
    <h4>行业分析</h4>
    <p>在选择具体行业时，建议你综合考虑以下因素：</p>
    <p><strong>成长性</strong>：选择处于上升期的行业，能让你的职业发展乘势而上；</p>
    <p><strong>匹配度</strong>：行业的工作模式和文化应与你的性格特质相匹配，
    避免长期处于“逆性格“的工作环境中；</p>
    <p><strong>可持续性</strong>：选择能够持续积累经验和资源的领域，让你的职业价值随时间增长而非贬值。</p>
    <p>记住，职业发展是一场马拉松而非短跑。选择一个与你的“本性“契合的方向，
    比追逐短期热点更能带来长期的职业满足感和成就感。</p>
    """
    return _build_chapter(11, CHAPTER_TITLES[10], content)


def _generate_chapter_12(
    archetype: PersonalityArchetype,
    riasec_code: str,
    score_map: dict[str, dict[str, object]],
    ocean_scores: list[dict[str, object]],
    careers: list[Career],
) -> dict[str, object]:
    """第 12 章：合适的职业。"""
    if careers:
        career_items: list[str] = []
        for i, c in enumerate(careers[:12], 1):
            salary: str = c.salary_range or "薪资待查"
            growth: str = c.growth_prospect or "前景待评"
            # 计算匹配理由
            arch_match: bool = archetype.archetype_id in (c.matching_archetypes or [])
            riasec_letters: list[str] = [ch for ch in riasec_code.upper() if ch]
            riasec_match: bool = any(r in (c.matching_riasec_codes or []) for r in riasec_letters)
            if arch_match and riasec_match:
                match_reason: str = "人格原型与职业兴趣双重匹配"
            elif arch_match:
                match_reason = "人格原型匹配"
            else:
                match_reason = "职业兴趣匹配"

            career_items.append(f"""
            <li><strong>{i}. {c.career_name}</strong>
            <br>类别：{c.career_category}
            <br>薪资范围：{salary}
            <br>发展前景：{growth}
            <br>匹配理由：{match_reason}
            <br>职业描述：{c.description}</li>
            """)
        career_html = f"<ol>{''.join(career_items)}</ol>"
    else:
        career_html = "<p>暂无匹配的职业数据，请稍后重试或联系客服。</p>"

    career_dirs: list[str] = list(archetype.career_directions or [])

    content: str = f"""
    <h3>合适的职业推荐</h3>
    <p>以下是基于你的人格原型「{archetype.archetype_name}」（#{archetype.archetype_id}）
    和霍兰德职业兴趣码「{riasec_code or "待确定"}」综合匹配的推荐职业列表。
    排序依据为匹配精度：同时匹配原型和兴趣码的职业优先展示。</p>
    {career_html}
    <h4>职业选择建议</h4>
    <p><strong>优先考虑</strong>：排在前列的职业与你的特质匹配度最高，建议作为首选探索方向。</p>
    <p><strong>拓展探索</strong>：你的人格原型推荐的职业方向还包括：{"、".join(career_dirs) if career_dirs else "待分析"}。
    这些方向虽然可能不在上述列表中，但同样与你的核心特质高度契合。</p>
    <p><strong>灵活运用</strong>：职业匹配不是“唯一答案”，而是“概率参考“。同一人格类型的人可以胜任多种职业，
    关键在于找到那个让你既有成就感又能持续成长的方向。建议你结合个人兴趣、技能储备和市场需求综合判断。</p>
    <p>最后，职业发展是一个动态过程。随着你的成长和环境的变化，适合你的职业也会随之扩展。
    保持开放心态，持续学习和探索，你一定能找到属于自己的职业甜蜜点。</p>
    """
    return _build_chapter(12, CHAPTER_TITLES[11], content)


# 章节生成器映射表
_CHAPTER_GENERATORS: list = [
    _generate_chapter_1,
    _generate_chapter_2,
    _generate_chapter_3,
    _generate_chapter_4,
    _generate_chapter_5,
    _generate_chapter_6,
    _generate_chapter_7,
    _generate_chapter_8,
    _generate_chapter_9,
    _generate_chapter_10,
    _generate_chapter_11,
    _generate_chapter_12,
]


# ===========================================================================
# 公共 API
# ===========================================================================


def generate_deep_report(
    archetype_id: int,
    riasec_code: str,
    ocean_scores: list[dict[str, object]],
    assessment_data: dict[str, object],
) -> dict[str, object]:
    """根据原型 ID、RIASEC 码、OCEAN 分数生成 12 章完整报告内容。

    :param archetype_id: 原型 ID（1-32）
    :param riasec_code: RIASEC 码（如 "IAS"）
    :param ocean_scores: OCEAN 五维度分数列表
    :param assessment_data: 测评附加数据（含 assessment_id、confidence 等）
    :return: 完整报告字典，含 12 章 chapters 列表
    :raises PersonalityArchetype.DoesNotExist: 原型不存在
    """
    logger.info(
        "开始生成深度报告 | archetype_id=%d | riasec_code=%s",
        archetype_id,
        riasec_code,
    )

    archetype: PersonalityArchetype = _get_archetype(archetype_id)
    score_map: dict[str, dict[str, object]] = _normalize_ocean_scores(ocean_scores)

    # 如果 OCEAN 分数为空，使用原型默认分数
    if not score_map:
        ocean_scores = _get_default_ocean_scores(archetype)
        score_map = _normalize_ocean_scores(ocean_scores)
        logger.info("OCEAN 分数为空，使用原型默认分数 | archetype_id=%d", archetype_id)

    # 查询匹配职业
    careers: list[Career] = _get_matching_careers(archetype_id, riasec_code)

    # 生成 12 章
    chapters: list[dict[str, object]] = []
    for generator in _CHAPTER_GENERATORS:
        chapter: dict[str, object] = generator(
            archetype,
            riasec_code,
            score_map,
            ocean_scores,
            careers,
        )
        chapters.append(chapter)

    total_words: int = sum(int(ch.get("word_count", 0)) for ch in chapters)

    report: dict[str, object] = {
        "archetype_id": archetype_id,
        "archetype_name": archetype.archetype_name,
        "archetype_slogan": archetype.archetype_slogan,
        "riasec_code": riasec_code,
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_word_count": total_words,
    }

    logger.info(
        "深度报告生成完成 | archetype_id=%d | chapters=%d | total_words=%d",
        archetype_id,
        len(chapters),
        total_words,
    )

    return report


def get_report_preview(archetype_id: int) -> dict[str, object]:
    """返回免费预览数据（第 1 章完整 + 其余章节标题和预览片段）。

    :param archetype_id: 原型 ID（1-32）
    :return: 预览数据字典，含 free_chapter 和 locked_preview 结构
    :raises PersonalityArchetype.DoesNotExist: 原型不存在
    """
    logger.info("生成报告预览 | archetype_id=%d", archetype_id)

    archetype: PersonalityArchetype = _get_archetype(archetype_id)

    # 使用原型默认分数生成预览内容
    ocean_scores: list[dict[str, object]] = _get_default_ocean_scores(archetype)
    score_map: dict[str, dict[str, object]] = _normalize_ocean_scores(ocean_scores)

    # 预览使用空 RIASEC 码
    riasec_code: str = ""

    # 查询匹配职业
    careers: list[Career] = _get_matching_careers(archetype_id, riasec_code)

    # 生成第 1 章（完整）
    free_chapter: dict[str, object] = _generate_chapter_1(archetype, riasec_code, score_map, ocean_scores, careers)

    # 生成第 2-12 章的预览片段
    preview_chapters: list[dict[str, object]] = []
    for i, generator in enumerate(_CHAPTER_GENERATORS[1:], start=2):
        full_chapter: dict[str, object] = generator(archetype, riasec_code, score_map, ocean_scores, careers)
        full_content: str = str(full_chapter.get("content", ""))
        preview_content: str = _truncate_content(full_content)
        preview_chapters.append(
            {
                "chapter_id": i,
                "title": CHAPTER_TITLES[i - 1],
                "preview_content": preview_content,
                "preview_word_count": _count_words(preview_content),
                "full_word_count": int(full_chapter.get("word_count", 0)),
                "is_locked": True,
            }
        )

    from common.constants import DEEP_REPORT_PRICE

    preview: dict[str, object] = {
        "archetype_id": archetype_id,
        "archetype_name": archetype.archetype_name,
        "archetype_slogan": archetype.archetype_slogan,
        "is_unlocked": False,
        "free_chapter": free_chapter,
        "locked_preview": {
            "preview_chapters": preview_chapters,
            "total_chapters": 12,
            "unlocked_chapters": 1,
            "locked_chapters": 11,
            "price": DEEP_REPORT_PRICE,
            "unlock_hint": f"支付 {DEEP_REPORT_PRICE} 元解锁全部 12 章深度报告",
        },
    }

    logger.info(
        "报告预览生成完成 | archetype_id=%d | preview_chapters=%d",
        archetype_id,
        len(preview_chapters),
    )

    return preview


def get_full_report(assessment_id: int) -> dict[str, object]:
    """校验支付状态后返回完整报告或预览。

    已付费：返回完整 12 章内容。
    未付费：返回预览数据。

    :param assessment_id: 测评记录 ID
    :return: 报告字典（is_unlocked=True 时为完整报告，False 时为预览）
    :raises ValueError: 测评记录不存在
    """
    from assessment.models import Assessment

    logger.info("获取完整报告 | assessment_id=%d", assessment_id)

    try:
        # 使用 .only() 限制查询字段，避免拉取加密答题数据等大字段
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
        ).get(id=assessment_id)
    except Assessment.DoesNotExist:
        logger.error("测评记录不存在 | assessment_id=%d", assessment_id)
        raise ValueError(f"测评记录不存在：{assessment_id}") from None

    # 检查支付状态
    is_paid: bool = check_payment_status(assessment.session_token, assessment_id)

    # 构建 OCEAN 分数
    ocean_scores: list[dict[str, object]] = [
        {
            "dimension": "O",
            "percentile": float(assessment.o_score) if assessment.o_score else 0.0,
            "is_high": float(assessment.o_score) > 50.0 if assessment.o_score else False,
            "level": _percentile_to_level(float(assessment.o_score) if assessment.o_score else 0.0),
        },
        {
            "dimension": "C",
            "percentile": float(assessment.c_score) if assessment.c_score else 0.0,
            "is_high": float(assessment.c_score) > 50.0 if assessment.c_score else False,
            "level": _percentile_to_level(float(assessment.c_score) if assessment.c_score else 0.0),
        },
        {
            "dimension": "E",
            "percentile": float(assessment.e_score) if assessment.e_score else 0.0,
            "is_high": float(assessment.e_score) > 50.0 if assessment.e_score else False,
            "level": _percentile_to_level(float(assessment.e_score) if assessment.e_score else 0.0),
        },
        {
            "dimension": "A",
            "percentile": float(assessment.a_score) if assessment.a_score else 0.0,
            "is_high": float(assessment.a_score) > 50.0 if assessment.a_score else False,
            "level": _percentile_to_level(float(assessment.a_score) if assessment.a_score else 0.0),
        },
        {
            "dimension": "N",
            "percentile": float(assessment.n_score) if assessment.n_score else 0.0,
            "is_high": float(assessment.n_score) > 50.0 if assessment.n_score else False,
            "level": _percentile_to_level(float(assessment.n_score) if assessment.n_score else 0.0),
        },
    ]

    assessment_data: dict[str, object] = {
        "assessment_id": assessment_id,
        "session_token": assessment.session_token,
        "confidence": assessment.confidence,
        "is_valid": assessment.is_valid,
        "duration_seconds": assessment.duration_seconds,
    }

    if is_paid:
        logger.info("测评已付费，返回完整报告 | assessment_id=%d", assessment_id)
        report: dict[str, object] = generate_deep_report(
            assessment.archetype_id,
            assessment.riasec_code or "",
            ocean_scores,
            assessment_data,
        )
        report["is_unlocked"] = True
        report["assessment_id"] = assessment_id
        return report
    else:
        logger.info("测评未付费，返回预览 | assessment_id=%d", assessment_id)
        preview: dict[str, object] = get_report_preview(assessment.archetype_id)
        preview["assessment_id"] = assessment_id
        return preview


def check_payment_status(session_token: str, assessment_id: int) -> bool:
    """检查该测评是否已付费解锁。

    查询关联订单中是否存在已支付（paid）状态的订单。

    :param session_token: 会话令牌
    :param assessment_id: 测评记录 ID
    :return: 是否已付费解锁
    """
    from payment.models import Order

    is_paid: bool = Order.objects.filter(
        session_token=session_token,
        assessment_id=assessment_id,
        status=Order.OrderStatus.PAID,
    ).exists()

    logger.info(
        "支付状态检查 | session=%s | assessment_id=%d | is_paid=%s",
        mask_token(session_token),
        assessment_id,
        is_paid,
    )

    return is_paid
