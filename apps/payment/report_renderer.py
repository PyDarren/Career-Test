"""
深度报告渲染器 — ReportRenderer。

将 MBTI 类型配置中的模板占位符替换为用户实际得分。

模板使用 {{placeholder}} 格式，渲染时逐字段替换。
"""

import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ReportRenderer:
    """深度报告渲染器。

    将 ``MBTIType`` 模型中的 ``report_*`` 字段中的 ``{{placeholder}}``
    替换为用户实际得分和维度数据。

    Usage::

        renderer = ReportRenderer()
        report = renderer.render(type_config, assessment)
    """

    # 占位符正则：{{key}}
    PLACEHOLDER_RE = re.compile(r'\{\{(\w+)\}\}')

    def render(self, type_config, assessment: Any) -> Dict[str, Any]:
        """渲染完整报告。

        Args:
            type_config: MBTIType 模型实例，包含 report_* 字段。
            assessment: Assessment 模型实例或兼容对象，需有
                       dimension_scores、facet_scores 属性。

        Returns:
            12 章报告内容字典。
        """
        # 解析评分数据（兼容 dict 和 JSON 字符串）
        scores = self._parse_json(assessment.dimension_scores)
        facets = self._parse_json(assessment.facet_scores)
        cognitive = self._parse_json(
            getattr(assessment, 'cognitive_stack', None)
        ) if hasattr(assessment, 'cognitive_stack') else type_config.cognitive_stack

        # 构建占位符上下文
        ctx = self._build_context(scores, facets, cognitive)

        # 逐章渲染
        report: Dict[str, Any] = {}

        # 第一章：封面（由模板处理，无需渲染）
        report['cover'] = {
            'type_code': type_config.type_code,
            'type_name': type_config.type_name,
            'type_slogan': type_config.type_slogan,
            'mascot_url': type_config.mascot_url,
        }

        # 第二章：人格特征分析
        report['personality_analysis'] = self._replace(
            type_config.report_personality_analysis, ctx
        )

        # 第三章：四维度详解（由模板渲染时使用 dimensions）
        report['dimensions'] = scores

        # 第四章：面向层级解析（由模板渲染时使用 facets）
        report['facets'] = facets

        # 第五章：优势
        report['strengths'] = self._render_list(
            self._parse_json(type_config.report_strengths), ctx
        )

        # 第六章：劣势
        report['weaknesses'] = self._render_list(
            self._parse_json(type_config.report_weaknesses), ctx
        )

        # 第七章：成长建议
        report['growth'] = self._render_list(
            self._parse_json(type_config.report_growth), ctx
        )

        # 第八章：荣格八维认知功能
        report['cognitive'] = self._render_list(
            self._parse_json(type_config.report_cognitive), ctx
        )

        # 第九章：恋爱专题
        report['romance'] = self._replace(
            type_config.report_romance, ctx
        )

        # 第十章：最佳恋爱对象
        report['romantic_matches'] = self._parse_json(
            type_config.report_romantic_matches
        )

        # 第十一章：职业专题
        report['career'] = self._render_list(
            self._parse_json(type_config.report_career), ctx
        )

        # 第十二章：按行业分类职业推荐（直接使用，无需渲染）
        report['career_list'] = self._parse_json(
            type_config.report_career_list
        )

        return report

    def _build_context(
        self,
        scores: Dict[str, Any],
        facets: List[Dict[str, Any]],
        cognitive: Dict[str, str],
    ) -> Dict[str, Any]:
        """构建占位符 → 实际值的映射。

        生成如下占位符：
        - dim_EI_percentage, dim_EI_label, dim_EI_strength
        - facet_EI_社交能量_percentage, ...
        - cog_dominant, cog_auxiliary, cog_tertiary, cog_inferior
        """
        ctx: Dict[str, Any] = {}

        # 维度级占位符
        for dim, data in scores.items():
            ctx[f'dim_{dim}_percentage'] = data.get('percentage', 50)
            ctx[f'dim_{dim}_label'] = data.get('label', 'X')
            ctx[f'dim_{dim}_strength'] = data.get('strength', 'slight')
            ctx[f'dim_{dim}_score_a'] = data.get('score_a', 18)
            ctx[f'dim_{dim}_score_b'] = data.get('score_b', 18)

        # 面向级占位符
        if isinstance(facets, list):
            for f in facets:
                dim = f.get('dimension', '')
                facet = f.get('facet', '')
                key = f'facet_{dim}_{facet}'
                ctx[f'{key}_pole'] = f.get('pole', '')
                ctx[f'{key}_percentage'] = f.get('percentage', 50)

        # 认知功能占位符
        if isinstance(cognitive, dict):
            for role, func in cognitive.items():
                ctx[f'cog_{role}'] = func

        return ctx

    def _replace(self, text: str, ctx: Dict[str, Any]) -> str:
        """替换 {{placeholder}} 格式的占位符。

        未找到的占位符保持原样（便于调试）。
        """
        if not text:
            return ''

        def replacer(match):
            key = match.group(1).strip()
            return str(ctx.get(key, match.group(0)))

        return self.PLACEHOLDER_RE.sub(replacer, text)

    def _render_list(
        self,
        items: List[Any],
        ctx: Dict[str, Any],
    ) -> List[Any]:
        """渲染列表中每个字符串元素的占位符。"""
        if not isinstance(items, list):
            return []
        result = []
        for item in items:
            if isinstance(item, str):
                result.append(self._replace(item, ctx))
            elif isinstance(item, dict):
                result.append({
                    k: self._replace(v, ctx) if isinstance(v, str) else v
                    for k, v in item.items()
                })
            else:
                result.append(item)
        return result

    @staticmethod
    def _parse_json(value: Any) -> Any:
        """安全解析 JSON：兼容 dict/list 和 JSON 字符串。"""
        if value is None:
            return {}
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return {}
        return {}
