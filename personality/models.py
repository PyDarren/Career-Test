# 画己职测 — personality 模型定义（1 张表：PersonalityArchetype）

from django.db import models


class PersonalityArchetype(models.Model):
    """人格原型配置表 — 32 种大五人格原型（2^5 = 32）。"""

    class DimensionRange(models.TextChoices):
        HIGH = "high", "高"
        LOW = "low", "低"

    archetype_id: models.IntegerField = models.IntegerField(primary_key=True, verbose_name="原型编号")
    archetype_code: models.CharField = models.CharField(max_length=20, verbose_name="维度组合码")
    archetype_name: models.CharField = models.CharField(max_length=50, verbose_name="中文画像名")
    archetype_slogan: models.CharField = models.CharField(max_length=200, verbose_name="一句话描述")
    rarity: models.CharField = models.CharField(max_length=20, verbose_name="稀有度标签")
    rarity_percentage: models.FloatField = models.FloatField(verbose_name="人口占比")
    famous_people: models.JSONField = models.JSONField(default=list, verbose_name="同型名人列表")
    best_partners: models.JSONField = models.JSONField(default=list, verbose_name="最佳协作原型 ID 列表")
    career_directions: models.JSONField = models.JSONField(default=list, verbose_name="推荐职业方向")
    o_range: models.CharField = models.CharField(
        max_length=4,
        choices=DimensionRange.choices,
        verbose_name="开放性区间",
    )
    c_range: models.CharField = models.CharField(
        max_length=4,
        choices=DimensionRange.choices,
        verbose_name="尽责性区间",
    )
    e_range: models.CharField = models.CharField(
        max_length=4,
        choices=DimensionRange.choices,
        verbose_name="外向性区间",
    )
    a_range: models.CharField = models.CharField(
        max_length=4,
        choices=DimensionRange.choices,
        verbose_name="宜人性区间",
    )
    n_range: models.CharField = models.CharField(
        max_length=4,
        choices=DimensionRange.choices,
        verbose_name="神经质区间",
    )
    mascot_url: models.CharField = models.CharField(max_length=200, verbose_name="吉祥物图片路径")

    class Meta:
        db_table: str = "personality_archetype"
        verbose_name: str = "人格原型"
        verbose_name_plural: str = "人格原型"

    def __str__(self) -> str:
        return f"#{self.archetype_id} {self.archetype_name}"
