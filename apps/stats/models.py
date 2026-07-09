"""统计模块模型。

包含 Feedback（用户反馈）、CustomerServiceMessage（客服留言）、
TrackingEvent（前端埋点事件）、StatsDaily（日报统计）四张表。
"""

from django.db import models


class Feedback(models.Model):
    """用户反馈表。

    支持四种反馈类型：职业推荐不匹配、部分匹配、报告评分、报告文字反馈。
    同一 uuid + assessment_id 防重复提交。
    """

    FEEDBACK_TYPE_CHOICES = [
        ('career_mismatch', '方向完全不对'),
        ('career_partial', '部分匹配'),
        ('report_rating', '报告评分'),
        ('report_text', '报告文字反馈'),
    ]

    RATING_CHOICES = [
        ('up', '赞'),
        ('down', '踩'),
    ]

    uuid = models.CharField(max_length=36, db_index=True, verbose_name='用户会话ID')
    assessment_id = models.BigIntegerField(null=True, blank=True, db_index=True, verbose_name='关联测评记录ID')
    order_no = models.CharField(max_length=64, null=True, blank=True, verbose_name='相关订单号')
    mbti_type = models.CharField(max_length=4, verbose_name='测评结果类型')
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES, verbose_name='反馈类型')
    career_id = models.CharField(max_length=20, null=True, blank=True, verbose_name='相关职业ID')
    rating = models.CharField(max_length=4, choices=RATING_CHOICES, null=True, blank=True, verbose_name='评分')
    content = models.TextField(null=True, blank=True, verbose_name='反馈内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'feedback'
        verbose_name = '用户反馈'
        verbose_name_plural = '用户反馈'
        indexes = [
            models.Index(fields=['uuid'], name='idx_fb_uuid'),
            models.Index(fields=['assessment_id'], name='idx_fb_assess'),
            models.Index(fields=['career_id'], name='idx_fb_career'),
        ]

    def __str__(self) -> str:
        return f'{self.uuid[:8]}... {self.feedback_type} ({self.created_at:%Y-%m-%d})'


class CustomerServiceMessage(models.Model):
    """客服留言表。

    用户可通过留言表单提交问题描述（必填，限 500 字）、
    联系方式（选填）、订单号（选填）。
    """

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('replied', '已回复'),
        ('closed', '已关闭'),
    ]

    uuid = models.CharField(max_length=36, null=True, blank=True, db_index=True, verbose_name='用户会话ID')
    contact = models.CharField(max_length=100, null=True, blank=True, verbose_name='联系方式')
    message = models.TextField(verbose_name='问题描述')
    order_no = models.CharField(max_length=64, null=True, blank=True, verbose_name='相关订单号')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='处理状态')
    reply = models.TextField(null=True, blank=True, verbose_name='回复内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='回复时间')

    class Meta:
        db_table = 'customer_service_message'
        verbose_name = '客服留言'
        verbose_name_plural = '客服留言'
        indexes = [
            models.Index(fields=['uuid'], name='idx_cs_uuid'),
            models.Index(fields=['status'], name='idx_cs_status'),
        ]

    def __str__(self) -> str:
        return f'{self.uuid[:8] if self.uuid else "匿名"}... ({self.status})'


class TrackingEvent(models.Model):
    """前端埋点事件表（低频事件直接入库）。

    高频事件（如 assessment_answer）存 Redis list，低频事件直接写入此表。
    17 个事件类型覆盖用户全流程行为。
    """

    uuid = models.CharField(max_length=36, db_index=True, verbose_name='用户会话ID')
    event_name = models.CharField(max_length=50, db_index=True, verbose_name='事件名称')
    event_data = models.JSONField(null=True, blank=True, verbose_name='事件数据')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')

    class Meta:
        db_table = 'tracking_event'
        verbose_name = '埋点事件'
        verbose_name_plural = '埋点事件'
        indexes = [
            models.Index(fields=['uuid'], name='idx_track_uuid'),
            models.Index(fields=['event_name'], name='idx_track_event'),
            models.Index(fields=['created_at'], name='idx_track_created'),
        ]

    def __str__(self) -> str:
        return f'{self.event_name} ({self.created_at:%Y-%m-%d %H:%M})'


class StatsDaily(models.Model):
    """日报统计表。

    每日聚合前一天的 UV/PV/完成率/付费数/收入等核心指标，
    由 Celery 定时任务 generate_daily_stats 在每天 03:00 生成。
    """

    date = models.DateField(unique=True, verbose_name='日期')
    uv = models.IntegerField(default=0, verbose_name='独立访客数')
    pv = models.IntegerField(default=0, verbose_name='页面浏览量')
    assessment_starts = models.IntegerField(default=0, verbose_name='测评开始数')
    assessment_completes = models.IntegerField(default=0, verbose_name='测评完成数')
    payment_clicks = models.IntegerField(default=0, verbose_name='支付点击数')
    payment_successes = models.IntegerField(default=0, verbose_name='支付成功数')
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='收入')
    share_clicks = models.IntegerField(default=0, verbose_name='分享点击数')
    referral_visits = models.IntegerField(default=0, verbose_name='分享回流数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'stats_daily'
        verbose_name = '日报统计'
        verbose_name_plural = '日报统计'

    def __str__(self) -> str:
        return f'{self.date} (UV:{self.uv} 完成:{self.assessment_completes} 收入:{self.revenue})'
