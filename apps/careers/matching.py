"""职业匹配引擎 — CareerMatcher。

匹配度 = 类型直接匹配(0.6) + 维度强度匹配(0.4)
- 类型直接匹配：用户类型在 mbti_fit 列表 → 100 分；相邻类型 → 70 分；否则 0 分
- 维度强度匹配：用户四维度百分比与职业理想画像的余弦相似度 × 100
- 加权后 < 50 分的职业不展示
- 按 match_score 降序返回 top N

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.7
"""

import math
from typing import List, Dict, Any

from .models import Career


class CareerMatcher:
    """职业匹配引擎。

    Usage::

        matcher = CareerMatcher()
        results = matcher.match('INTJ', dimensions_dict)
        # results: [{career_id, career_name, match_score, category, ...}, ...]
    """

    # 16 型相邻类型（仅一个维度不同）
    NEIGHBOR_TYPES: Dict[str, List[str]] = {
        'INTJ': ['ENTJ', 'INFJ', 'INTP', 'ISTJ'],
        'INTP': ['ENTP', 'INFP', 'INTJ', 'ISTP'],
        'ENTJ': ['INTJ', 'ENTP', 'ESTJ', 'ENFJ'],
        'ENTP': ['INTP', 'ENFP', 'ENTJ', 'ESTP'],
        'INFJ': ['ENFJ', 'INTJ', 'INFP', 'ISFJ'],
        'INFP': ['ENFP', 'INFJ', 'INTP', 'ISFP'],
        'ENFJ': ['INFJ', 'ENTJ', 'ESFJ', 'ENFP'],
        'ENFP': ['INFP', 'ENTP', 'ESFP', 'ENFJ'],
        'ISTJ': ['ESTJ', 'ISFJ', 'INTJ', 'ISTP'],
        'ISFJ': ['ESFJ', 'ISTJ', 'INFJ', 'ISFP'],
        'ESTJ': ['ISTJ', 'ENTJ', 'ESFJ', 'ESTP'],
        'ESFJ': ['ISFJ', 'ENFJ', 'ESTJ', 'ESFP'],
        'ISTP': ['ESTP', 'ISFP', 'INTP', 'ISTJ'],
        'ISFP': ['ESFP', 'ISTP', 'INFP', 'ISFJ'],
        'ESTP': ['ISTP', 'ESFP', 'ENTP', 'ESTJ'],
        'ESFP': ['ISFP', 'ESTP', 'ENFP', 'ESFJ'],
    }

    # 权重配置
    TYPE_WEIGHT = 0.6
    STRENGTH_WEIGHT = 0.4
    # 低于此分数不展示
    MIN_SCORE = 50

    def match(
        self,
        mbti_type: str,
        dimensions: Dict[str, Dict[str, Any]],
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """执行职业匹配。

        Args:
            mbti_type: 用户 MBTI 类型代码，如 'INTJ'。
            dimensions: 评分引擎返回的维度结果字典。
                格式: {'EI': {'percentage': 67, 'label': 'E', ...}, ...}
            top_n: 返回前 N 个匹配结果，默认 5。

        Returns:
            匹配结果列表，按 match_score 降序排列：
            [{career_id, career_name, match_score, category, description,
              salary_range, growth_prospect, match_tags}, ...]
        """
        careers = Career.objects.all()
        results: List[Dict[str, Any]] = []

        for career in careers:
            # 类型直接匹配
            type_score = self._type_match(mbti_type, career.mbti_fit)

            # 维度强度匹配（余弦相似度）
            strength_score = self._cosine_similarity(dimensions, career.mbti_ideal)

            # 加权计算
            final_score = type_score * self.TYPE_WEIGHT + strength_score * self.STRENGTH_WEIGHT

            if final_score >= self.MIN_SCORE:
                results.append({
                    'career_id': career.career_id,
                    'career_name': career.career_name,
                    'match_score': round(final_score),
                    'category': career.category,
                    'description': career.description,
                    'salary_range': career.salary_range,
                    'growth_prospect': career.growth_prospect,
                    'match_tags': career.match_tags,
                })

        # 按 match_score 降序排列
        results.sort(key=lambda x: x['match_score'], reverse=True)

        return results[:top_n]

    def _type_match(self, user_type: str, fit_list: List[str]) -> float:
        """类型直接匹配评分。

        - 用户类型在适配列表 → 100 分
        - 相邻类型（仅一个维度不同）在列表 → 70 分
        - 否则 → 0 分

        Args:
            user_type: 用户 MBTI 类型代码。
            fit_list: 职业的 MBTI 适配列表。

        Returns:
            匹配分数（0 / 70 / 100）。
        """
        if user_type in fit_list:
            return 100.0

        neighbors = self.NEIGHBOR_TYPES.get(user_type, [])
        if any(n in fit_list for n in neighbors):
            return 70.0

        return 0.0

    def _cosine_similarity(
        self,
        user_dims: Dict[str, Dict[str, Any]],
        ideal_json: Dict[str, int],
    ) -> float:
        """计算用户四维度倾向与职业理想画像的余弦相似度。

        用户向量从 dimensions 字典提取 percentage 值，
        职业向量从 mbti_ideal 字典提取 E/S/T/J 值。

        Args:
            user_dims: {'EI': {'percentage': 67, ...}, 'SN': {...}, ...}
            ideal_json: {'E': 40, 'S': 60, 'T': 70, 'J': 60}

        Returns:
            余弦相似度 × 100（0-100 范围）。
        """
        # 用户向量：EI 百分比 → E 倾向，SN 百分比 → S 倾向
        # percentage 是 A 极（E/S/T/J）的占比
        user_vec = [
            user_dims.get('EI', {}).get('percentage', 50),
            user_dims.get('SN', {}).get('percentage', 50),
            user_dims.get('TF', {}).get('percentage', 50),
            user_dims.get('JP', {}).get('percentage', 50),
        ]

        ideal_vec = [
            ideal_json.get('E', 50),
            ideal_json.get('S', 50),
            ideal_json.get('T', 50),
            ideal_json.get('J', 50),
        ]

        dot = sum(a * b for a, b in zip(user_vec, ideal_vec))
        norm_a = math.sqrt(sum(a ** 2 for a in user_vec))
        norm_b = math.sqrt(sum(b ** 2 for b in ideal_vec))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return (dot / (norm_a * norm_b)) * 100
