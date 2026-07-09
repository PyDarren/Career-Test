"""MBTI 16 型配置模型。

对应数据库表 mbti_type，存储 16 种 MBTI 类型的完整配置数据，
包括基本信息、认知功能栈、以及 12 章深度报告的内容模板。
"""

from django.db import models


class MBTIType(models.Model):
    """MBTI 类型配置（16 行固定数据）。

    包含类型基本信息、稀有度、名人、最佳搭子、3D 人偶 URL、
    认知功能栈，以及 12 章深度报告的内容模板（使用 {{placeholder}} 占位符）。
    """

    type_code = models.CharField(max_length=4, unique=True, verbose_name='类型代码')
    type_name = models.CharField(max_length=32, verbose_name='类型名称')
    type_slogan = models.CharField(max_length=64, verbose_name='类型标语')
    role_group = models.CharField(max_length=16, verbose_name='角色组')
    rarity = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='稀有度百分比')
    rarity_label = models.CharField(max_length=32, verbose_name='稀有度标签')
    famous_people = models.JSONField(verbose_name='代表名人')
    best_partners = models.JSONField(verbose_name='最佳搭档')
    romantic_matches = models.JSONField(verbose_name='恋爱适配')
    mascot_url = models.CharField(max_length=256, verbose_name='人偶图片URL')
    type_description = models.TextField(verbose_name='类型简述')
    cognitive_stack = models.JSONField(verbose_name='认知功能栈')

    # 深度报告内容模板（按章节存储，渲染时替换占位符）
    report_personality_analysis = models.TextField(verbose_name='第二章：人格特征分析')
    report_strengths = models.JSONField(verbose_name='第五章：4项优势')
    report_weaknesses = models.JSONField(verbose_name='第六章：4项劣势')
    report_growth = models.JSONField(verbose_name='第七章：4条成长建议')
    report_cognitive = models.JSONField(verbose_name='第八章：荣格八维解读')
    report_romance = models.TextField(verbose_name='第九章：恋爱专题')
    report_romantic_matches = models.JSONField(verbose_name='第十章：3个最佳恋爱对象')
    report_career = models.JSONField(verbose_name='第十一章：职业专题')
    report_career_list = models.JSONField(verbose_name='第十二章：按行业分类职业')

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name='更新时间')

    class Meta:
        db_table = 'mbti_type'
        verbose_name = 'MBTI类型'
        verbose_name_plural = 'MBTI类型'

    def __str__(self) -> str:
        return f'{self.type_code} {self.type_name}'

    def to_dict(self) -> dict:
        """返回完整的类型配置字典（用于 API 响应）。"""
        return {
            'type_code': self.type_code,
            'type_name': self.type_name,
            'type_slogan': self.type_slogan,
            'role_group': self.role_group,
            'rarity': float(self.rarity),
            'rarity_label': self.rarity_label,
            'famous_people': self.famous_people,
            'best_partners': self.best_partners,
            'romantic_matches': self.romantic_matches,
            'mascot_url': self.mascot_url,
            'type_description': self.type_description,
            'cognitive_stack': self.cognitive_stack,
        }
