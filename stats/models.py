# 画己职测 — stats 模型定义（4 张表：Feedback, CustomerServiceMessage,
# TrackingEvent, StatsDaily）

from django.db import models


class Feedback(models.Model):
    """用户反馈表。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    session_token: models.CharField = models.CharField(max_length=36, db_index=True, verbose_name="会话令牌")
    device_fingerprint: models.CharField = models.CharField(max_length=64, verbose_name="设备指纹")
    content: models.TextField = models.TextField(verbose_name="反馈内容")
    rating: models.IntegerField = models.IntegerField(null=True, verbose_name="评分 1-5")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "feedback"
        verbose_name: str = "用户反馈"
        verbose_name_plural: str = "用户反馈"

    def __str__(self) -> str:
        return f"Feedback#{self.id} | rating={self.rating}"


class CustomerServiceMessage(models.Model):
    """客服消息表。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    session_token: models.CharField = models.CharField(max_length=36, db_index=True, verbose_name="会话令牌")
    device_fingerprint: models.CharField = models.CharField(max_length=64, verbose_name="设备指纹")
    content: models.TextField = models.TextField(verbose_name="消息内容")
    is_from_user: models.BooleanField = models.BooleanField(default=True, verbose_name="是否用户发送")
    is_read: models.BooleanField = models.BooleanField(default=False, verbose_name="是否已读")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "customer_service_message"
        verbose_name: str = "客服消息"
        verbose_name_plural: str = "客服消息"

    def __str__(self) -> str:
        sender: str = "用户" if self.is_from_user else "客服"
        return f"CSMessage#{self.id} | {sender}"


class TrackingEvent(models.Model):
    """埋点事件表。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    session_token: models.CharField = models.CharField(max_length=36, db_index=True, verbose_name="会话令牌")
    device_fingerprint: models.CharField = models.CharField(max_length=64, db_index=True, verbose_name="设备指纹")
    event_type: models.CharField = models.CharField(
        max_length=30,
        db_index=True,
        verbose_name="事件类型",
        help_text="page_view/start_assessment/submit_answer/generate_card/" "click_pay/pay_success/share/report_read",
    )
    event_data: models.JSONField = models.JSONField(default=dict, verbose_name="事件数据")
    page_name: models.CharField = models.CharField(max_length=50, null=True, verbose_name="页面名称")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "tracking_event"
        ordering: list[str] = ["-created_at"]
        verbose_name: str = "埋点事件"
        verbose_name_plural: str = "埋点事件"

    def __str__(self) -> str:
        return f"Event#{self.id} | {self.event_type}"


class StatsDaily(models.Model):
    """每日统计表。"""

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    date: models.DateField = models.DateField(unique=True, db_index=True, verbose_name="日期")
    dau: models.IntegerField = models.IntegerField(default=0, verbose_name="日活")
    assessment_count: models.IntegerField = models.IntegerField(default=0, verbose_name="测评完成数")
    completion_rate: models.FloatField = models.FloatField(default=0.0, verbose_name="完成率")
    payment_count: models.IntegerField = models.IntegerField(default=0, verbose_name="付费数")
    conversion_rate: models.FloatField = models.FloatField(default=0.0, verbose_name="转化率")
    share_count: models.IntegerField = models.IntegerField(default=0, verbose_name="分享数")
    share_rate: models.FloatField = models.FloatField(default=0.0, verbose_name="分享率")
    revenue: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="收入")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table: str = "stats_daily"
        ordering: list[str] = ["-date"]
        verbose_name: str = "每日统计"
        verbose_name_plural: str = "每日统计"

    def __str__(self) -> str:
        return f"StatsDaily | {self.date}"
