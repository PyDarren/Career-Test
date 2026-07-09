"""ScoringEngine 单元测试。

覆盖 10 步评分算法的核心逻辑：
1. POSITION_MAP 题目计分
2. 面向计分 / 维度计分
3. 倾向强度计算
4. 类型判定（含临界 X）
5. 一致性检测（面向一致性 + 极端作答）
6. 认知功能栈查表
7. 答案指纹生成

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.5
"""

from django.test import TestCase

from apps.assessment.models import Question
from apps.assessment.scoring import (
    ScoringEngine,
    POSITION_MAP,
    COGNITIVE_STACK_MAP,
    DIMENSIONS,
)


class ScoringEngineTest(TestCase):
    """ScoringEngine 测试套件。"""

    fixtures = ['questions.json']

    def setUp(self):
        self.engine = ScoringEngine()
        self.questions = list(
            Question.objects
            .order_by('display_order')
            .values(
                'id',
                'dimension',
                'facet',
                'facet_order',
                'pole_a',
                'pole_b',
                'is_reverse',
                'display_order',
            )
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _build_answers(self, positions_list):
        """从位置列表构造答案。"""
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'facet', 'is_reverse')
        )
        return [
            {'question_id': q['id'], 'position': pos}
            for q, pos in zip(questions, positions_list)
        ]

    def _build_all_same(self, position):
        """所有题选同一位置。"""
        return self._build_answers([position] * 48)

    def _build_type_answers(self, target_type='INTJ'):
        """构造特定 MBTI 类型的答案（使用极端位置 1/6）。

        target_type: 4 字母 MBTI 代码，如 'INTJ'。
        """
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'is_reverse')
        )
        type_map = {
            'EI': target_type[0],
            'SN': target_type[1],
            'TF': target_type[2],
            'JP': target_type[3],
        }
        dim_poles = {
            'EI': ('E', 'I'),
            'SN': ('S', 'N'),
            'TF': ('T', 'F'),
            'JP': ('J', 'P'),
        }
        answers = []
        for q in questions:
            dim = q['dimension']
            target_pole = type_map[dim]
            pole_a, pole_b = dim_poles[dim]
            position = 1 if target_pole == pole_a else 6
            if q['is_reverse']:
                position = 7 - position
            answers.append({'question_id': q['id'], 'position': position})
        return answers

    def _build_type_answers_moderate(self, target_type='INTJ'):
        """构造特定 MBTI 类型的答案（使用非极端位置 2/5）。

        用于测试正常一致性场景，避免触发 extreme_response。
        """
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'is_reverse')
        )
        type_map = {
            'EI': target_type[0],
            'SN': target_type[1],
            'TF': target_type[2],
            'JP': target_type[3],
        }
        dim_poles = {
            'EI': ('E', 'I'),
            'SN': ('S', 'N'),
            'TF': ('T', 'F'),
            'JP': ('J', 'P'),
        }
        answers = []
        for q in questions:
            dim = q['dimension']
            target_pole = type_map[dim]
            pole_a, pole_b = dim_poles[dim]
            position = 2 if target_pole == pole_a else 5
            if q['is_reverse']:
                position = 7 - position
            answers.append({'question_id': q['id'], 'position': position})
        return answers

    def _build_facet_inconsistent_answers(self):
        """构造 EI 维度内面向不一致的答案。

        EI 的 facet_order=1 和 3 倾向 A 极（位置 2），
        facet_order=2 倾向 B 极（位置 5），
        其他维度使用位置 2。
        """
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'facet', 'facet_order', 'is_reverse')
        )
        answers = []
        for q in questions:
            if q['dimension'] == 'EI' and q['facet_order'] == 2:
                pos = 5  # 倾向 B 极
            else:
                pos = 2  # 倾向 A 极
            answers.append({'question_id': q['id'], 'position': pos})
        return answers

    def _build_critical_dimension_answers(self, critical_dim='EI'):
        """构造某个维度为临界（score_a == score_b）的答案。

        对 critical_dim 维度：
        - 6 道正向题选位置 1（→ A 极 +3）
        - 3 道正向题选位置 6（→ B 极 +3）
        - 3 道反向题选位置 1（→ 翻转后 B 极 +3）
        总计 score_a=18, score_b=18 → label='X'

        其他维度全部选位置 2（→ A 极，非极端）。
        """
        questions = list(
            Question.objects
            .order_by('display_order')
            .values('id', 'dimension', 'is_reverse')
        )
        dim_questions = [q for q in questions if q['dimension'] == critical_dim]
        non_reverse = [q for q in dim_questions if not q['is_reverse']]
        reverse_qs = [q for q in dim_questions if q['is_reverse']]

        # 6 道正向题 → 位置 1，3 道正向题 → 位置 6
        assignments = {}
        for i, q in enumerate(non_reverse):
            assignments[q['id']] = 1 if i < 6 else 6
        # 3 道反向题 → 位置 1（翻转后归入 B 极）
        for q in reverse_qs:
            assignments[q['id']] = 1

        answers = []
        for q in questions:
            if q['dimension'] == critical_dim:
                pos = assignments[q['id']]
            else:
                pos = 2
            answers.append({'question_id': q['id'], 'position': pos})
        return answers

    # ------------------------------------------------------------------
    # 测试用例
    # ------------------------------------------------------------------

    def test_all_position_1_returns_extreme_a(self):
        """所有题选位置 1 → A 极占优，类型为 ESTJ，strength='distinct'。"""
        answers = self._build_all_same(1)
        result = self.engine.calculate(answers, self.questions)

        for dim_code, dim_result in result['dimensions'].items():
            # 位置 1 → (3, 'a')；反向题翻转后归入 B 极
            # 每维度 9 道正向 + 3 道反向
            non_reverse = sum(
                1 for q in self.questions
                if q['dimension'] == dim_code and not q['is_reverse']
            )
            reverse = sum(
                1 for q in self.questions
                if q['dimension'] == dim_code and q['is_reverse']
            )
            self.assertEqual(dim_result['score_a'], non_reverse * 3)
            self.assertEqual(dim_result['score_b'], reverse * 3)
            self.assertGreater(dim_result['score_a'], dim_result['score_b'])
            self.assertEqual(dim_result['label'], dim_result['pole_a'])
            self.assertEqual(dim_result['strength'], 'distinct')

        # 四维度均倾向 A 极 → ESTJ
        self.assertEqual(result['mbti_type'], 'ESTJ')

    def test_all_position_6_returns_extreme_b(self):
        """所有题选位置 6 → B 极占优，类型为 INFP，strength='distinct'。"""
        answers = self._build_all_same(6)
        result = self.engine.calculate(answers, self.questions)

        for dim_code, dim_result in result['dimensions'].items():
            non_reverse = sum(
                1 for q in self.questions
                if q['dimension'] == dim_code and not q['is_reverse']
            )
            reverse = sum(
                1 for q in self.questions
                if q['dimension'] == dim_code and q['is_reverse']
            )
            # 位置 6 → (3, 'b')；反向题翻转后归入 A 极
            self.assertEqual(dim_result['score_a'], reverse * 3)
            self.assertEqual(dim_result['score_b'], non_reverse * 3)
            self.assertGreater(dim_result['score_b'], dim_result['score_a'])
            self.assertEqual(dim_result['label'], dim_result['pole_b'])
            self.assertEqual(dim_result['strength'], 'distinct')

        # 四维度均倾向 B 极 → INFP
        self.assertEqual(result['mbti_type'], 'INFP')

    def test_critical_dimension_returns_x(self):
        """某维度 score_a == score_b → label='X'。"""
        answers = self._build_critical_dimension_answers('EI')
        result = self.engine.calculate(answers, self.questions)

        ei_result = result['dimensions']['EI']
        self.assertEqual(ei_result['score_a'], ei_result['score_b'])
        self.assertEqual(ei_result['label'], 'X')

    def test_extreme_response_detection(self):
        """连续 8+ 题选位置 1 或 6 → consistency_flag 包含 'extreme_response'。"""
        # 所有题选位置 1 → 48 题连续极端
        answers = self._build_all_same(1)
        result = self.engine.calculate(answers, self.questions)
        self.assertIn('extreme_response', result['consistency_flag'])

    def test_normal_consistency(self):
        """正常作答（混合位置 2/5）→ consistency_flag='normal'。"""
        answers = self._build_type_answers_moderate('INTJ')
        result = self.engine.calculate(answers, self.questions)
        self.assertEqual(result['consistency_flag'], 'normal')

    def test_cognitive_stack_intj(self):
        """构造答案得到 INTJ → cognitive_stack dominant='Ni', inferior='Se'。"""
        answers = self._build_type_answers('INTJ')
        result = self.engine.calculate(answers, self.questions)

        self.assertEqual(result['mbti_type'], 'INTJ')
        stack = result['cognitive_stack']
        self.assertEqual(stack['dominant'], 'Ni')
        self.assertEqual(stack['auxiliary'], 'Te')
        self.assertEqual(stack['tertiary'], 'Fi')
        self.assertEqual(stack['inferior'], 'Se')

    def test_cognitive_stack_enfp(self):
        """构造答案得到 ENFP → cognitive_stack dominant='Ne', inferior='Si'。"""
        answers = self._build_type_answers('ENFP')
        result = self.engine.calculate(answers, self.questions)

        self.assertEqual(result['mbti_type'], 'ENFP')
        stack = result['cognitive_stack']
        self.assertEqual(stack['dominant'], 'Ne')
        self.assertEqual(stack['auxiliary'], 'Fi')
        self.assertEqual(stack['tertiary'], 'Te')
        self.assertEqual(stack['inferior'], 'Si')

    def test_facet_inconsistent(self):
        """同一维度内面向倾向不一致 → consistency_flag 包含 'facet_inconsistent'。"""
        answers = self._build_facet_inconsistent_answers()
        result = self.engine.calculate(answers, self.questions)
        self.assertIn('facet_inconsistent', result['consistency_flag'])

    def test_answers_fingerprint(self):
        """相同答案 → 相同指纹；不同答案 → 不同指纹。"""
        answers_a = self._build_type_answers('INTJ')
        answers_b = self._build_type_answers('INTJ')
        answers_c = self._build_type_answers('ENFP')

        fp_a = self.engine._generate_fingerprint(answers_a)
        fp_b = self.engine._generate_fingerprint(answers_b)
        fp_c = self.engine._generate_fingerprint(answers_c)

        self.assertEqual(fp_a, fp_b)
        self.assertNotEqual(fp_a, fp_c)

    def test_position_map(self):
        """验证 POSITION_MAP 的 6 个映射正确。"""
        expected = {
            1: (3, 'a'),
            2: (2, 'a'),
            3: (1, 'a'),
            4: (1, 'b'),
            5: (2, 'b'),
            6: (3, 'b'),
        }
        self.assertEqual(POSITION_MAP, expected)

        # 验证每个 position 都能正确映射
        for pos in range(1, 7):
            score, pole = self.engine._position_to_score(pos)
            self.assertEqual((score, pole), expected[pos])
