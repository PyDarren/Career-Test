# 画己职测 — assessment 模型定义（2 张表：Question, Assessment）

from django.db import models


class Question(models.Model):
    """题库表 — 存储所有测评题目。"""

    class QuestionType(models.TextChoices):
        OCEAN = "ocean", "大五人格"
        RIASEC = "riasec", "RIASEC"
        VALIDITY = "validity", "效度题"

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    question_text: models.TextField = models.TextField(verbose_name="题目陈述")
    dimension_prefix: models.CharField = models.CharField(
        max_length=2,
        verbose_name="维度前缀",
        help_text="BO/BC/BE/BA/BN/RR/RI/RA/RS/RE/RC",
    )
    is_reverse: models.BooleanField = models.BooleanField(default=False, verbose_name="是否反向计分")
    question_type: models.CharField = models.CharField(
        max_length=10,
        choices=QuestionType.choices,
        verbose_name="题目类型",
    )
    order: models.IntegerField = models.IntegerField(verbose_name="题目顺序")
    is_active: models.BooleanField = models.BooleanField(default=True, verbose_name="是否启用")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table: str = "question"
        ordering: list[str] = ["order"]
        verbose_name: str = "题目"
        verbose_name_plural: str = "题目"

    def __str__(self) -> str:
        return f"[{self.dimension_prefix}] Q{self.order}"


class Assessment(models.Model):
    """测评记录表 — 存储用户每次测评的完整记录。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    session_token: models.CharField = models.CharField(max_length=36, db_index=True, verbose_name="会话令牌")
    device_fingerprint: models.CharField = models.CharField(max_length=64, db_index=True, verbose_name="设备指纹")
    answers: models.TextField = models.TextField(
        verbose_name="答题数据",
        help_text="AES-256 加密的答题数据（JSON 格式）",
    )
    archetype_id: models.IntegerField = models.IntegerField(null=True, verbose_name="画像原型 ID")
    archetype_name: models.CharField = models.CharField(max_length=50, null=True, verbose_name="画像名")
    riasec_code: models.CharField = models.CharField(max_length=3, null=True, verbose_name="RIASEC 码")
    o_score: models.FloatField = models.FloatField(null=True, verbose_name="开放性百分位")
    c_score: models.FloatField = models.FloatField(null=True, verbose_name="尽责性百分位")
    e_score: models.FloatField = models.FloatField(null=True, verbose_name="外向性百分位")
    a_score: models.FloatField = models.FloatField(null=True, verbose_name="宜人性百分位")
    n_score: models.FloatField = models.FloatField(null=True, verbose_name="神经质百分位")
    confidence: models.FloatField = models.FloatField(null=True, verbose_name="置信度")
    is_valid: models.BooleanField = models.BooleanField(default=True, verbose_name="测评是否有效")
    duration_seconds: models.IntegerField = models.IntegerField(null=True, verbose_name="答题耗时（秒）")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "assessment"
        ordering: list[str] = ["-created_at"]
        verbose_name: str = "测评记录"
        verbose_name_plural: str = "测评记录"

    def __str__(self) -> str:
        return f"Assessment#{self.id} | {self.session_token[:8]}"
