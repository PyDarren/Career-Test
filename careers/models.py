# 画己职测 — careers 模型定义（1 张表：Career）

from django.db import models


class Career(models.Model):
    """职业表 — 存储职业推荐数据。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    career_name: models.CharField = models.CharField(max_length=100, verbose_name="职业名称")
    career_category: models.CharField = models.CharField(max_length=50, verbose_name="职业类别")
    description: models.TextField = models.TextField(verbose_name="职业描述")
    matching_archetypes: models.JSONField = models.JSONField(default=list, verbose_name="匹配的画像 ID 列表")
    matching_riasec_codes: models.JSONField = models.JSONField(default=list, verbose_name="匹配的 RIASEC 码列表")
    salary_range: models.CharField = models.CharField(max_length=50, null=True, verbose_name="薪资范围")
    growth_prospect: models.CharField = models.CharField(max_length=20, null=True, verbose_name="发展前景")
    is_active: models.BooleanField = models.BooleanField(default=True, verbose_name="是否启用")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "career"
        ordering: list[str] = ["career_name"]
        verbose_name: str = "职业"
        verbose_name_plural: str = "职业"

    def __str__(self) -> str:
        return str(self.career_name)
