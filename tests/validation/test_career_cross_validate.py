"""职业数据库交叉验证 — 验证职业数据质量与匹配引擎完整性。

覆盖范围：
- 数据规模：职业总数 ≥ 80、分类数 ≥ 6
- 字段完整性：每个职业都有 mbti_fit 和维度画像（mbti_ideal）
- 类型有效性：mbti_fit 中的类型均为合法的 16 种 MBTI 之一
- 匹配引擎：对 16 种 MBTI 类型均能返回匹配职业，分数在 0-100 区间
- 数据一致性：职业名称无重复

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md Phase 7
"""

from django.test import TestCase

from apps.careers.matching import CareerMatcher
from apps.careers.models import Career


# 16 种合法 MBTI 类型
VALID_MBTI_TYPES = frozenset({
    'INTJ', 'INTP', 'ENTJ', 'ENTP',
    'INFJ', 'INFP', 'ENFJ', 'ENFP',
    'ISTJ', 'ISFJ', 'ESTJ', 'ESFJ',
    'ISTP', 'ISFP', 'ESTP', 'ESFP',
})

# 维度画像应包含的四个极性键
DIMENSION_PROFILE_KEYS = {'E', 'S', 'T', 'J'}


def dimensions_for_type(mbti_type):
    """根据 MBTI 类型构造维度百分比（A 极 E/S/T/J 占比）。

    用于驱动 CareerMatcher.match() 的余弦相似度计算：
    - 偏向 A 极（E/S/T/J）的类型 → 高百分比
    - 偏向 B 极（I/N/F/P）的类型 → 低百分比
    """
    return {
        'EI': {'percentage': 70 if mbti_type[0] == 'E' else 30,
               'label': mbti_type[0]},
        'SN': {'percentage': 70 if mbti_type[1] == 'S' else 30,
               'label': mbti_type[1]},
        'TF': {'percentage': 70 if mbti_type[2] == 'T' else 30,
               'label': mbti_type[2]},
        'JP': {'percentage': 70 if mbti_type[3] == 'J' else 30,
               'label': mbti_type[3]},
    }


class CareerCrossValidateTest(TestCase):
    """职业数据库交叉验证测试套件。"""

    fixtures = ['careers.json']

    def setUp(self):
        self.matcher = CareerMatcher()
        self.careers = list(Career.objects.all())

    # ------------------------------------------------------------------
    # 数据规模
    # ------------------------------------------------------------------

    def test_career_count(self):
        """职业总数 ≥ 80。"""
        count = Career.objects.count()
        self.assertGreaterEqual(
            count, 80,
            f'职业总数 {count} 不足 80',
        )

    def test_career_categories(self):
        """职业分类数 ≥ 6。"""
        categories = (
            Career.objects
            .values_list('category', flat=True)
            .distinct()
        )
        category_count = len(set(categories))
        self.assertGreaterEqual(
            category_count, 6,
            f'职业分类数 {category_count} 不足 6',
        )

    # ------------------------------------------------------------------
    # 字段完整性
    # ------------------------------------------------------------------

    def test_all_careers_have_mbti_fit(self):
        """每个职业都有 mbti_fit 字段（非空列表）。"""
        for career in self.careers:
            self.assertTrue(
                career.mbti_fit,
                f'职业 {career.career_id} ({career.career_name}) '
                f'缺少 mbti_fit 或为空',
            )
            self.assertIsInstance(
                career.mbti_fit, list,
                f'职业 {career.career_id} 的 mbti_fit 应为列表',
            )

    def test_all_careers_have_dimension_profile(self):
        """每个职业都有维度画像（mbti_ideal 含 E/S/T/J）。"""
        for career in self.careers:
            self.assertTrue(
                career.mbti_ideal,
                f'职业 {career.career_id} ({career.career_name}) '
                f'缺少 mbti_ideal 维度画像',
            )
            self.assertIsInstance(
                career.mbti_ideal, dict,
                f'职业 {career.career_id} 的 mbti_ideal 应为字典',
            )
            missing = DIMENSION_PROFILE_KEYS - set(career.mbti_ideal.keys())
            self.assertFalse(
                missing,
                f'职业 {career.career_id} 的 mbti_ideal 缺少维度: {missing}',
            )

    # ------------------------------------------------------------------
    # 类型有效性
    # ------------------------------------------------------------------

    def test_mbti_fit_valid_types(self):
        """mbti_fit 中的类型都是有效的 MBTI 类型（16 种之一）。"""
        for career in self.careers:
            for mbti_type in career.mbti_fit:
                self.assertIn(
                    mbti_type, VALID_MBTI_TYPES,
                    f'职业 {career.career_id} ({career.career_name}) '
                    f'的 mbti_fit 含非法类型: {mbti_type}',
                )

    # ------------------------------------------------------------------
    # 匹配引擎完整性
    # ------------------------------------------------------------------

    def test_career_matcher_returns_results(self):
        """CareerMatcher 对每种 MBTI 类型都能返回至少 3 个匹配职业。"""
        for mbti_type in VALID_MBTI_TYPES:
            results = self.matcher.match(mbti_type, dimensions_for_type(mbti_type))
            self.assertGreaterEqual(
                len(results), 3,
                f'MBTI 类型 {mbti_type} 的匹配职业数 {len(results)} 不足 3',
            )

    def test_career_match_score_range(self):
        """匹配分数在 0-100 之间。"""
        for mbti_type in VALID_MBTI_TYPES:
            results = self.matcher.match(mbti_type, dimensions_for_type(mbti_type))
            for r in results:
                self.assertGreaterEqual(
                    r['match_score'], 0,
                    f'{mbti_type} 匹配职业 {r["career_name"]} '
                    f'分数 {r["match_score"]} 低于 0',
                )
                self.assertLessEqual(
                    r['match_score'], 100,
                    f'{mbti_type} 匹配职业 {r["career_name"]} '
                    f'分数 {r["match_score"]} 超过 100',
                )

    def test_all_16_types_have_matches(self):
        """对 16 种 MBTI 类型都能匹配到职业（至少 1 个）。"""
        for mbti_type in VALID_MBTI_TYPES:
            results = self.matcher.match(mbti_type, dimensions_for_type(mbti_type))
            self.assertGreaterEqual(
                len(results), 1,
                f'MBTI 类型 {mbti_type} 未匹配到任何职业',
            )

    # ------------------------------------------------------------------
    # 数据一致性
    # ------------------------------------------------------------------

    def test_no_duplicate_career_names(self):
        """职业名称无重复。"""
        names = [c.career_name for c in self.careers]
        seen = set()
        duplicates = set()
        for name in names:
            if name in seen:
                duplicates.add(name)
            seen.add(name)
        self.assertEqual(
            duplicates, set(),
            f'存在重复职业名称: {duplicates}',
        )
