"""ReportRenderer 单元测试。

覆盖深度报告渲染器的核心逻辑：
1. 12 章报告结构完整性
2. {{placeholder}} 占位符替换（已知 / 未知）
3. 列表（含 dict）渲染
4. JSON 安全解析（dict / 字符串 / 无效）
5. 真实 fixture 数据端到端渲染

关联文档：TECH_DESIGN.md v1.2 / IMPLEMENTATION_PLAN.md 4.8
"""

from django.test import TestCase

from apps.assessment.models import Assessment
from apps.mbti_types.models import MBTIType
from apps.payment.report_renderer import ReportRenderer


class ReportRendererTest(TestCase):
    """ReportRenderer 测试套件。"""

    fixtures = ['questions.json', 'mbti_types.json', 'careers.json']

    def setUp(self):
        self.assessment = Assessment.objects.create(
            uuid='test-render-uuid',
            mbti_type_code='INTJ',
            dimension_scores={
                'EI': {'percentage': 33, 'label': 'I', 'score_a': 12, 'score_b': 24, 'strength': 'moderate'},
                'SN': {'percentage': 25, 'label': 'N', 'score_a': 9, 'score_b': 27, 'strength': 'distinct'},
                'TF': {'percentage': 75, 'label': 'T', 'score_a': 27, 'score_b': 9, 'strength': 'distinct'},
                'JP': {'percentage': 70, 'label': 'J', 'score_a': 25, 'score_b': 11, 'strength': 'distinct'},
            },
            facet_scores=[],
            consistency_flag='normal',
        )
        self.type_config = MBTIType.objects.get(type_code='INTJ')
        self.renderer = ReportRenderer()

    # ------------------------------------------------------------------
    # render 完整报告
    # ------------------------------------------------------------------

    def test_render_returns_12_chapters(self):
        """render() 返回含 12 个 key。"""
        report = self.renderer.render(self.type_config, self.assessment)
        self.assertEqual(len(report), 12)
        expected_keys = {
            'cover', 'personality_analysis', 'dimensions', 'facets',
            'strengths', 'weaknesses', 'growth', 'cognitive',
            'romance', 'romantic_matches', 'career', 'career_list',
        }
        self.assertEqual(set(report.keys()), expected_keys)

    # ------------------------------------------------------------------
    # 占位符替换
    # ------------------------------------------------------------------

    def test_placeholder_replacement(self):
        """含 {{dim_EI_percentage}} 的文本被替换为实际值。"""
        text = '你的内向倾向为 {{dim_EI_percentage}}%'
        ctx = {'dim_EI_percentage': 33}
        result = self.renderer._replace(text, ctx)
        self.assertEqual(result, '你的内向倾向为 33%')

    def test_unknown_placeholder_kept(self):
        """未知占位符保持原样。"""
        text = '未知 {{unknown_key}} 占位符'
        result = self.renderer._replace(text, {})
        self.assertEqual(result, '未知 {{unknown_key}} 占位符')

    def test_render_list_with_dicts(self):
        """列表中含 dict 的占位符替换。"""
        items = [
            {'name': '{{dim_EI_label}}', 'desc': 'desc {{dim_EI_percentage}}'},
            'plain {{dim_EI_label}}',
        ]
        ctx = {'dim_EI_label': 'I', 'dim_EI_percentage': 33}
        result = self.renderer._render_list(items, ctx)
        self.assertEqual(result[0]['name'], 'I')
        self.assertEqual(result[0]['desc'], 'desc 33')
        self.assertEqual(result[1], 'plain I')

    # ------------------------------------------------------------------
    # JSON 解析
    # ------------------------------------------------------------------

    def test_parse_json_dict(self):
        """传入 dict → 原样返回。"""
        data = {'a': 1, 'b': 2}
        result = ReportRenderer._parse_json(data)
        self.assertEqual(result, data)

    def test_parse_json_string(self):
        """传入 JSON 字符串 → 解析为 dict。"""
        result = ReportRenderer._parse_json('{"a": 1, "b": 2}')
        self.assertEqual(result, {'a': 1, 'b': 2})

    def test_parse_json_invalid(self):
        """传入无效 JSON → 返回 {}。"""
        result = ReportRenderer._parse_json('not-json')
        self.assertEqual(result, {})

    # ------------------------------------------------------------------
    # 端到端渲染
    # ------------------------------------------------------------------

    def test_render_with_real_data(self):
        """使用 fixture 数据渲染完整报告。"""
        report = self.renderer.render(self.type_config, self.assessment)
        # 封面信息来自类型配置
        self.assertEqual(report['cover']['type_code'], 'INTJ')
        self.assertEqual(report['cover']['type_name'], '建筑师')
        # 维度数据来自 assessment
        self.assertIn('EI', report['dimensions'])
        self.assertEqual(report['dimensions']['EI']['percentage'], 33)
        # 人格分析已渲染为字符串
        self.assertIsInstance(report['personality_analysis'], str)
        # 优势 / 劣势 / 成长 / 认知为列表且非空
        self.assertIsInstance(report['strengths'], list)
        self.assertIsInstance(report['weaknesses'], list)
        self.assertIsInstance(report['growth'], list)
        self.assertIsInstance(report['cognitive'], list)
        self.assertGreater(len(report['strengths']), 0)
        self.assertGreater(len(report['cognitive']), 0)
