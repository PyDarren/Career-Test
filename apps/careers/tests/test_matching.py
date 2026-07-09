"""CareerMatcher 单元测试。

覆盖职业匹配引擎的核心逻辑：
1. 类型直接匹配（100 分）/ 相邻类型匹配（70 分）/ 无匹配（0 分）
2. 维度强度余弦相似度计算
3. 匹配结果排序、过滤、截断
4. 16 型相邻类型映射完整性

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.7
"""

import math

from django.test import TestCase

from apps.careers.matching import CareerMatcher
from apps.careers.models import Career


class CareerMatcherTest(TestCase):
    """CareerMatcher 测试套件。"""

    fixtures = ['careers.json']

    def setUp(self):
        self.matcher = CareerMatcher()

    # ------------------------------------------------------------------
    # 类型匹配测试
    # ------------------------------------------------------------------

    def test_direct_type_match(self):
        """用户类型在 mbti_fit 列表 → type_score=100。"""
        score = self.matcher._type_match('INTJ', ['INTJ', 'ENTJ', 'ISTJ', 'ESTJ'])
        self.assertEqual(score, 100.0)

    def test_neighbor_type_match(self):
        """相邻类型在列表 → type_score=70。

        INTJ 的相邻类型为 ENTJ、INFJ、INTP、ISTJ。
        """
        score = self.matcher._type_match('INTJ', ['ENTJ', 'ESTJ', 'ISTJ'])
        self.assertEqual(score, 70.0)

    def test_no_type_match(self):
        """不相关类型 → type_score=0。

        ESFP、ISFP、ESTP 均非 INTJ 的相邻类型。
        """
        score = self.matcher._type_match('INTJ', ['ESFP', 'ISFP', 'ESTP'])
        self.assertEqual(score, 0.0)

    # ------------------------------------------------------------------
    # 余弦相似度测试
    # ------------------------------------------------------------------

    def test_cosine_similarity(self):
        """验证余弦相似度计算。

        用户向量 = [67, 30, 70, 60]
        职业向量 = [40, 60, 70, 60]
        """
        user_dims = {
            'EI': {'percentage': 67},
            'SN': {'percentage': 30},
            'TF': {'percentage': 70},
            'JP': {'percentage': 60},
        }
        ideal_json = {'E': 40, 'S': 60, 'T': 70, 'J': 60}

        result = self.matcher._cosine_similarity(user_dims, ideal_json)

        # 手动计算预期值
        dot = 67 * 40 + 30 * 60 + 70 * 70 + 60 * 60
        norm_a = math.sqrt(67 ** 2 + 30 ** 2 + 70 ** 2 + 60 ** 2)
        norm_b = math.sqrt(40 ** 2 + 60 ** 2 + 70 ** 2 + 60 ** 2)
        expected = (dot / (norm_a * norm_b)) * 100

        self.assertAlmostEqual(result, expected, places=2)
        self.assertGreater(result, 90)  # 两个向量方向接近，相似度应较高

    # ------------------------------------------------------------------
    # 匹配结果测试
    # ------------------------------------------------------------------

    def test_match_returns_sorted(self):
        """match() 返回结果按 match_score 降序。"""
        dimensions = {
            'EI': {'percentage': 60, 'label': 'E'},
            'SN': {'percentage': 50, 'label': 'S'},
            'TF': {'percentage': 70, 'label': 'T'},
            'JP': {'percentage': 55, 'label': 'J'},
        }
        results = self.matcher.match('INTJ', dimensions, top_n=20)

        scores = [r['match_score'] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_match_filters_low_scores(self):
        """匹配分数 < 50 的职业不返回。"""
        dimensions = {
            'EI': {'percentage': 60, 'label': 'E'},
            'SN': {'percentage': 50, 'label': 'S'},
            'TF': {'percentage': 70, 'label': 'T'},
            'JP': {'percentage': 55, 'label': 'J'},
        }
        results = self.matcher.match('INTJ', dimensions, top_n=100)

        for r in results:
            self.assertGreaterEqual(r['match_score'], CareerMatcher.MIN_SCORE)

    def test_match_returns_top_n(self):
        """match() 返回最多 top_n 个结果（默认 5）。"""
        dimensions = {
            'EI': {'percentage': 60, 'label': 'E'},
            'SN': {'percentage': 50, 'label': 'S'},
            'TF': {'percentage': 70, 'label': 'T'},
            'JP': {'percentage': 55, 'label': 'J'},
        }
        # 自定义 top_n=3
        results_3 = self.matcher.match('INTJ', dimensions, top_n=3)
        self.assertLessEqual(len(results_3), 3)

        # 默认 top_n=5
        results_default = self.matcher.match('INTJ', dimensions)
        self.assertLessEqual(len(results_default), 5)

    def test_match_with_intj(self):
        """INTJ 类型 → 返回包含高匹配职业（如软件工程师、投资银行分析师）。

        使用 A 极（E/S/T/J）百分比构造维度向量：
        - EI: 低 E%（INTJ 偏内向）→ percentage=20
        - SN: 低 S%（INTJ 偏直觉）→ percentage=20
        - TF: 高 T%（INTJ 偏思考）→ percentage=80
        - JP: 高 J%（INTJ 偏判断）→ percentage=80
        """
        dimensions = {
            'EI': {'percentage': 20, 'label': 'I'},
            'SN': {'percentage': 20, 'label': 'N'},
            'TF': {'percentage': 80, 'label': 'T'},
            'JP': {'percentage': 80, 'label': 'J'},
        }
        results = self.matcher.match('INTJ', dimensions, top_n=20)

        career_names = [r['career_name'] for r in results]
        high_match_careers = [
            '软件工程师',
            '投资银行分析师',
            '数据科学家',
            '系统架构师',
            '机器学习工程师',
        ]
        self.assertTrue(
            any(name in career_names for name in high_match_careers),
            f'返回的职业中应包含 INTJ 高匹配职业，实际返回: {career_names}',
        )

        # 验证直接匹配的职业得分较高
        for r in results:
            self.assertGreaterEqual(r['match_score'], 50)

    # ------------------------------------------------------------------
    # 相邻类型映射测试
    # ------------------------------------------------------------------

    def test_neighbor_types_map(self):
        """验证 16 型相邻类型映射完整性（每个类型有 4 个相邻类型）。"""
        neighbor_map = CareerMatcher.NEIGHBOR_TYPES

        # 确保有 16 个类型
        all_types = {
            'INTJ', 'INTP', 'ENTJ', 'ENTP',
            'INFJ', 'INFP', 'ENFJ', 'ENFP',
            'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
            'ISTP', 'ISFP', 'ESTP', 'ESFP',
        }
        self.assertEqual(set(neighbor_map.keys()), all_types)

        for mbti_type, neighbors in neighbor_map.items():
            # 每个类型恰好 4 个相邻类型
            self.assertEqual(
                len(neighbors), 4,
                f'{mbti_type} 应有 4 个相邻类型，实际 {len(neighbors)}',
            )

            # 相邻类型应与当前类型仅有一个字母不同
            for neighbor in neighbors:
                diff_count = sum(
                    1 for a, b in zip(mbti_type, neighbor) if a != b
                )
                self.assertEqual(
                    diff_count, 1,
                    f'{neighbor} 与 {mbti_type} 应仅有一个维度不同，'
                    f'实际 {diff_count} 个',
                )

            # 相邻类型不应包含自身
            self.assertNotIn(mbti_type, neighbors)

            # 所有相邻类型都应是合法的 16 型
            for n in neighbors:
                self.assertIn(n, all_types)
