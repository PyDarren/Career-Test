"""测评模块模型。

包含 Question（量表题目表）和 Assessment（测评记录表）。
"""

from django.db import models


class Question(models.Model):
    """量表题目（48 行固定数据）。

    4 维度 × 3 面向 × 4 题 = 48 题，每维度 12 题，含 12 道反向题。
    使用 6 点刻度迫选格式，display_order 为打乱后的展示顺序。
    """

    DIMENSION_CHOICES = [
        ('EI', '外向-内向'),
        ('SN', '实感-直觉'),
        ('TF', '思考-情感'),
        ('JP', '判断-感知'),
    ]

    question_order = models.IntegerField(unique=True, verbose_name='题目顺序')
    dimension = models.CharField(max_length=2, choices=DIMENSION_CHOICES, verbose_name='所属维度')
    facet = models.CharField(max_length=32, verbose_name='面向名称')
    facet_order = models.IntegerField(verbose_name='面向内序号')
    text_a = models.CharField(max_length=256, verbose_name='A极描述')
    text_b = models.CharField(max_length=256, verbose_name='B极描述')
    pole_a = models.CharField(max_length=2, verbose_name='A极字母')
    pole_b = models.CharField(max_length=2, verbose_name='B极字母')
    is_reverse = models.BooleanField(default=False, verbose_name='是否反向题')
    display_order = models.IntegerField(verbose_name='展示顺序')

    class Meta:
        db_table = 'question'
        verbose_name = '题目'
        verbose_name_plural = '题目'
        indexes = [
            models.Index(fields=['dimension'], name='idx_dimension'),
            models.Index(fields=['dimension', 'facet_order'], name='idx_facet'),
        ]

    def __str__(self) -> str:
        return f'Q{self.question_order}: {self.text_a[:20]}...'


class Assessment(models.Model):
    """测评记录表。

    仅存储结果（类型代码 + 得分），不存储原始答题数据。
    原始刻度位置仅存浏览器 localStorage，提交评分后丢弃。
    """

    CONSISTENCY_CHOICES = [
        ('normal', '正常'),
        ('facet_inconsistent', '面向不一致'),
        ('reverse_inconsistent', '反向题不一致'),
        ('extreme_response', '极端作答'),
        ('facet_and_extreme', '面向不一致且极端作答'),
    ]

    uuid = models.CharField(max_length=36, db_index=True, verbose_name='用户会话ID')
    browser_fingerprint = models.CharField(max_length=64, null=True, blank=True, db_index=True, verbose_name='浏览器指纹')
    mbti_type_code = models.CharField(max_length=4, verbose_name='测评结果类型')
    dimension_scores = models.JSONField(verbose_name='维度得分')
    facet_scores = models.JSONField(verbose_name='面向得分')
    consistency_flag = models.CharField(max_length=32, choices=CONSISTENCY_CHOICES, default='normal', verbose_name='一致性标记')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        db_table = 'assessment'
        verbose_name = '测评记录'
        verbose_name_plural = '测评记录'
        indexes = [
            models.Index(fields=['uuid'], name='idx_assess_uuid'),
            models.Index(fields=['browser_fingerprint'], name='idx_assess_fp'),
            models.Index(fields=['created_at'], name='idx_assess_created'),
        ]

    def __str__(self) -> str:
        return f'{self.uuid[:8]}... → {self.mbti_type_code} ({self.created_at:%Y-%m-%d})'
