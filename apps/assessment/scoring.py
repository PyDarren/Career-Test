"""
评分引擎 — ScoringEngine

10 步评分算法实现：
1. 题目计分（POSITION_MAP 映射）
2. 面向计分（4 题/面向）
3. 维度计分（12 题/维度，满分 36）
4. 倾向强度计算（百分比）
5. 类型判定（临界 → X）
6. 一致性检测（面向一致性 + 反向题 + 极端作答）
7. 认知功能栈查表推导
8. 评分结果缓存
9. 综合返回

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.5
"""

from collections import defaultdict
from typing import List, Dict, Any
import hashlib
import json

# ============================================================
# 常量定义
# ============================================================

# 6 点刻度位置 → (分数, 极性) 映射
# position 1-3 → A 极（递减分数），4-6 → B 极（递增分数）
POSITION_MAP = {
    1: (3, 'a'),   # 强烈同意 A → A极 +3
    2: (2, 'a'),   # 同意 A     → A极 +2
    3: (1, 'a'),   # 轻微同意 A → A极 +1
    4: (1, 'b'),   # 轻微同意 B → B极 +1
    5: (2, 'b'),   # 同意 B     → B极 +2
    6: (3, 'b'),   # 强烈同意 B → B极 +3
}

# 维度满分 = 12 题 × 3 分 = 36
DIMENSION_MAX = 36

# 认知功能栈配置表（16 型完整映射）
# 依据荣格八维认知功能理论
# dominant（主导）> auxiliary（辅助）> tertiary（第三）> inferior（劣势）
COGNITIVE_STACK_MAP = {
    # ---- 分析师 (NT) ----
    'INTJ': {'dominant': 'Ni', 'auxiliary': 'Te', 'tertiary': 'Fi', 'inferior': 'Se'},
    'INTP': {'dominant': 'Ti', 'auxiliary': 'Ne', 'tertiary': 'Si', 'inferior': 'Fe'},
    'ENTJ': {'dominant': 'Te', 'auxiliary': 'Ni', 'tertiary': 'Se', 'inferior': 'Fi'},
    'ENTP': {'dominant': 'Ne', 'auxiliary': 'Ti', 'tertiary': 'Fe', 'inferior': 'Si'},
    # ---- 外交家 (NF) ----
    'INFJ': {'dominant': 'Ni', 'auxiliary': 'Fe', 'tertiary': 'Ti', 'inferior': 'Se'},
    'INFP': {'dominant': 'Fi', 'auxiliary': 'Ne', 'tertiary': 'Si', 'inferior': 'Te'},
    'ENFJ': {'dominant': 'Fe', 'auxiliary': 'Ni', 'tertiary': 'Se', 'inferior': 'Ti'},
    'ENFP': {'dominant': 'Ne', 'auxiliary': 'Fi', 'tertiary': 'Te', 'inferior': 'Si'},
    # ---- 哨兵型 (SJ) ----
    'ISTJ': {'dominant': 'Si', 'auxiliary': 'Te', 'tertiary': 'Fi', 'inferior': 'Ne'},
    'ISFJ': {'dominant': 'Si', 'auxiliary': 'Fe', 'tertiary': 'Ti', 'inferior': 'Ne'},
    'ESTJ': {'dominant': 'Te', 'auxiliary': 'Si', 'tertiary': 'Ne', 'inferior': 'Fi'},
    'ESFJ': {'dominant': 'Fe', 'auxiliary': 'Si', 'tertiary': 'Ne', 'inferior': 'Ti'},
    # ---- 探索家 (SP) ----
    'ISTP': {'dominant': 'Ti', 'auxiliary': 'Se', 'tertiary': 'Ni', 'inferior': 'Fe'},
    'ISFP': {'dominant': 'Fi', 'auxiliary': 'Se', 'tertiary': 'Ni', 'inferior': 'Te'},
    'ESTP': {'dominant': 'Se', 'auxiliary': 'Ti', 'tertiary': 'Fe', 'inferior': 'Ni'},
    'ESFP': {'dominant': 'Se', 'auxiliary': 'Fi', 'tertiary': 'Te', 'inferior': 'Ni'},
}

# 维度定义
DIMENSIONS = {
    'EI': {'pole_a': 'E', 'pole_b': 'I', 'label_a': '外向', 'label_b': '内向'},
    'SN': {'pole_a': 'S', 'pole_b': 'N', 'label_a': '实感', 'label_b': '直觉'},
    'TF': {'pole_a': 'T', 'pole_b': 'F', 'label_a': '思考', 'label_b': '情感'},
    'JP': {'pole_a': 'J', 'pole_b': 'P', 'label_a': '判断', 'label_b': '感知'},
}

# 倾向强度等级
def get_strength_label(percentage: int) -> str:
    """根据百分比返回倾向强度标签"""
    if percentage >= 75:
        return 'distinct'   # 明显倾向
    elif percentage >= 55:
        return 'moderate'   # 中等倾向
    else:
        return 'slight'     # 轻微倾向


# ============================================================
# 评分引擎
# ============================================================

class ScoringEngine:
    """
    MBTI 评分引擎

    10 步算法：
    1. POSITION_MAP 映射（position → 分数 + 极性）
    2. 面向计分（4 题/面向，3 面向/维度）
    3. 维度计分（12 题/维度，满分 36）
    4. 倾向强度计算（百分比 = pole_a_score / DIMENSION_MAX × 100）
    5. 类型判定（临界 18:18 → X）
    6. 一致性检测（面向一致性 + 反向题 + 极端作答 ≥ 8 题连续）
    7. 认知功能栈查表 COGNITIVE_STACK_MAP
    """

    def __init__(self):
        self.position_map = POSITION_MAP
        self.dimension_max = DIMENSION_MAX
        self.cognitive_stack_map = COGNITIVE_STACK_MAP

    def calculate(self, answers: List[Dict[str, Any]], questions: List[dict]) -> dict:
        """
        执行完整评分流程

        Args:
            answers: 用户作答列表，每项 {question_id, position}
                     position ∈ [1, 6]
            questions: 题目元数据列表，每项含 question_id, dimension, facet,
                       facet_order, pole_a, pole_b, is_reverse

        Returns:
            dict: {
                mbti_type, dimensions, facets, cognitive_stack,
                consistency_flag, answers_fingerprint
            }
        """
        # 构建题目索引
        q_map = {q['id']: q for q in questions}

        # 步骤 1-2: 题目计分 + 面向计分
        facet_groups = defaultdict(lambda: {'a': 0, 'b': 0, 'details': []})
        for ans in answers:
            q = q_map[ans['question_id']]
            score, pole = self._position_to_score(ans['position'])

            # 反向题处理：交换 A/B 极
            if q.get('is_reverse', False):
                pole = 'b' if pole == 'a' else 'a'

            facet_key = f"{q['dimension']}_{q['facet']}"
            facet_groups[facet_key]['a' if pole == 'a' else 'b'] += score
            facet_groups[facet_key]['details'].append({
                'question_id': ans['question_id'],
                'position': ans['position'],
                'score': score,
                'pole': pole,
                'is_reverse': q.get('is_reverse', False),
            })

        # 步骤 3-4: 维度计分 + 倾向强度
        dimension_results = self._calculate_dimensions(facet_groups, q_map)

        # 步骤 5: 类型判定
        mbti_type = self._determine_type(dimension_results)

        # 步骤 6: 一致性检测
        consistency_flag = self._check_consistency(answers, facet_groups, dimension_results)

        # 步骤 7: 认知功能栈推导
        cognitive_stack = self.cognitive_stack_map.get(mbti_type, {})

        # 答案指纹（用于缓存）
        answers_fingerprint = self._generate_fingerprint(answers)

        # 构建面向结果
        facet_results = self._build_facet_results(facet_groups, q_map)

        return {
            'mbti_type': mbti_type,
            'dimensions': dimension_results,
            'facets': facet_results,
            'cognitive_stack': cognitive_stack,
            'consistency_flag': consistency_flag,
            'answers_fingerprint': answers_fingerprint,
        }

    # --------------------------------------------------------
    # 步骤 1: 刻度位置 → 分值
    # --------------------------------------------------------
    def _position_to_score(self, position: int) -> tuple:
        """position 1-6 → (score, pole)"""
        return self.position_map[position]

    # --------------------------------------------------------
    # 步骤 3-4: 维度计分 + 倾向强度
    # --------------------------------------------------------
    def _calculate_dimensions(self, facet_groups: dict, q_map: dict) -> dict:
        """
        聚合面向分数到维度级别，计算倾向百分比

        Returns:
            {
                'EI': {'pole_a': 'E', 'score_a': 24, 'score_b': 12,
                        'percentage': 67, 'label': 'E', 'strength': 'moderate'},
                ...
            }
        """
        dim_totals = defaultdict(lambda: {'a': 0, 'b': 0})

        for facet_key, data in facet_groups.items():
            dim = facet_key.split('_')[0]  # e.g. 'EI_社交能量' → 'EI'
            dim_totals[dim]['a'] += data['a']
            dim_totals[dim]['b'] += data['b']

        results = {}
        for dim, config in DIMENSIONS.items():
            score_a = dim_totals[dim]['a']
            score_b = dim_totals[dim]['b']
            total = score_a + score_b

            # 百分比：A 极占比
            if total > 0:
                percentage = round(score_a / total * 100)
            else:
                percentage = 50

            # 判定倾向极
            if score_a > score_b:
                label = config['pole_a']
            elif score_b > score_a:
                label = config['pole_b']
                percentage = 100 - percentage
            else:
                label = 'X'  # 临界

            results[dim] = {
                'pole_a': config['pole_a'],
                'pole_b': config['pole_b'],
                'score_a': score_a,
                'score_b': score_b,
                'percentage': percentage,
                'label': label,
                'strength': get_strength_label(max(percentage, 100 - percentage)),
            }

        return results

    # --------------------------------------------------------
    # 步骤 5: 类型判定
    # --------------------------------------------------------
    def _determine_type(self, dimension_results: dict) -> str:
        """
        根据四维度结果判定 MBTI 类型

        临界（score_a == score_b）→ X
        """
        type_code = ''
        for dim in ['EI', 'SN', 'TF', 'JP']:
            label = dimension_results[dim]['label']
            type_code += label
        return type_code

    # --------------------------------------------------------
    # 步骤 6: 一致性检测
    # --------------------------------------------------------
    def _check_consistency(self, answers: list, facet_groups: dict,
                           dimension_results: dict) -> str:
        """
        一致性检测：
        - 面向一致性：同一维度内 3 个面向倾向是否一致
        - 反向题一致性：反向题翻转后是否与正向题一致
        - 极端作答检测：≥ 8 题连续选择极端位置（1 或 6）

        Returns:
            'normal' | 'facet_inconsistent' | 'reverse_inconsistent'
            | 'extreme_response' | 'facet_and_extreme'
        """
        flags = []

        # 面向一致性检测
        facet_inconsistent = self._check_facet_consistency(facet_groups)
        if facet_inconsistent:
            flags.append('facet_inconsistent')

        # 极端作答检测
        extreme = self._check_extreme_response(answers)
        if extreme:
            flags.append('extreme_response')

        if not flags:
            return 'normal'
        elif len(flags) == 1:
            return flags[0]
        else:
            return 'facet_and_extreme'

    def _check_facet_consistency(self, facet_groups: dict) -> bool:
        """检查同一维度内 3 个面向的倾向是否一致"""
        dim_facets = defaultdict(list)
        for facet_key, data in facet_groups.items():
            parts = facet_key.split('_', 1)
            dim = parts[0]
            facet_name = parts[1] if len(parts) > 1 else ''
            if data['a'] > data['b']:
                dim_facets[dim].append('a')
            elif data['b'] > data['a']:
                dim_facets[dim].append('b')
            else:
                dim_facets[dim].append('tie')

        for dim, poles in dim_facets.items():
            non_tie = [p for p in poles if p != 'tie']
            if len(non_tie) >= 2 and len(set(non_tie)) > 1:
                return True
        return False

    def _check_extreme_response(self, answers: list) -> bool:
        """检测连续 ≥ 8 题选择极端位置（1 或 6）"""
        consecutive = 0
        for ans in answers:
            pos = ans.get('position', 0)
            if pos in (1, 6):
                consecutive += 1
                if consecutive >= 8:
                    return True
            else:
                consecutive = 0
        return False

    # --------------------------------------------------------
    # 辅助方法
    # --------------------------------------------------------
    def _build_facet_results(self, facet_groups: dict, q_map: dict) -> list:
        """构建面向级别结果列表"""
        results = []
        for facet_key, data in sorted(facet_groups.items()):
            parts = facet_key.split('_', 1)
            dim = parts[0]
            facet_name = parts[1] if len(parts) > 1 else ''

            total = data['a'] + data['b']
            percentage = round(data['a'] / total * 100) if total > 0 else 50

            dim_config = DIMENSIONS.get(dim, {})
            pole = dim_config.get('pole_a', 'A')
            if data['b'] > data['a']:
                pole = dim_config.get('pole_b', 'B')
                percentage = 100 - percentage

            results.append({
                'dimension': dim,
                'facet': facet_name,
                'pole': pole,
                'score_a': data['a'],
                'score_b': data['b'],
                'percentage': percentage,
            })
        return results

    def _generate_fingerprint(self, answers: list) -> str:
        """生成答案指纹 MD5（用于缓存 key）"""
        answer_str = json.dumps(
            [(a['question_id'], a['position']) for a in answers],
            sort_keys=True
        )
        return hashlib.md5(answer_str.encode()).hexdigest()
