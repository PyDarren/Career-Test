"""职业数据库模型。

对应数据库表 career，存储 80-120 个职业的完整数据，
用于职业推荐匹配算法。
"""

from django.db import models


class Career(models.Model):
    """职业数据库（80-120 行）。

    每个职业包含 MBTI 适配列表、维度理想画像、认知功能适配、
    工作风格、技能要求、薪资范围、发展前景等字段。
    匹配算法使用 mbti_fit 和 mbti_ideal 进行类型匹配和维度相似度计算。
    """

    career_id = models.CharField(max_length=16, unique=True, verbose_name='职业ID')
    career_name = models.CharField(max_length=64, verbose_name='职业名称')
    category = models.CharField(max_length=32, db_index=True, verbose_name='职业大类')
    mbti_fit = models.JSONField(verbose_name='适配MBTI类型')
    mbti_ideal = models.JSONField(verbose_name='维度理想画像')
    cognitive_fit = models.JSONField(verbose_name='适配认知功能')
    work_style = models.CharField(max_length=256, verbose_name='理想工作环境')
    skill_required = models.JSONField(verbose_name='核心能力要求')
    salary_range = models.CharField(max_length=128, verbose_name='薪资参考范围')
    growth_prospect = models.CharField(max_length=256, verbose_name='发展前景')
    description = models.TextField(verbose_name='职业简介')
    match_tags = models.JSONField(verbose_name='匹配关键词')

    class Meta:
        db_table = 'career'
        verbose_name = '职业'
        verbose_name_plural = '职业'
        indexes = [
            models.Index(fields=['category'], name='idx_category'),
        ]

    def __str__(self) -> str:
        return f'{self.career_id} {self.career_name}'

    def to_dict(self) -> dict:
        """返回职业信息的精简字典（用于 API 响应）。"""
        return {
            'career_id': self.career_id,
            'career_name': self.career_name,
            'category': self.category,
            'salary_range': self.salary_range,
            'growth_prospect': self.growth_prospect,
            'description': self.description,
            'match_tags': self.match_tags,
        }
