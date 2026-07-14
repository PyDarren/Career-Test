# 画己职测 — payment 模型定义（1 张表：Order）

from django.db import models


class Order(models.Model):
    """订单表 — 存储深度报告支付订单。"""

    class OrderStatus(models.TextChoices):
        PENDING = "pending", "待支付"
        PAID = "paid", "已支付"
        EXPIRED = "expired", "已过期"
        FAILED = "failed", "支付失败"
        REFUNDED = "refunded", "已退款"

    id: models.BigAutoField = models.BigAutoField(primary_key=True)
    order_id: models.CharField = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="订单号")
    session_token: models.CharField = models.CharField(max_length=36, db_index=True, verbose_name="会话令牌")
    assessment_id: models.BigIntegerField = models.BigIntegerField(null=True, verbose_name="关联的测评 ID")
    device_fingerprint: models.CharField = models.CharField(max_length=64, verbose_name="设备指纹")
    amount: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="金额")
    product_name: models.CharField = models.CharField(
        max_length=100,
        default="职业人格深度报告",
        verbose_name="商品名称",
    )
    status: models.CharField = models.CharField(
        max_length=10,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="订单状态",
    )
    payment_channel: models.CharField = models.CharField(max_length=20, null=True, verbose_name="支付渠道")
    transaction_id: models.CharField = models.CharField(max_length=64, null=True, verbose_name="交易号")
    signature: models.CharField = models.CharField(max_length=128, verbose_name="HMAC-SHA256 签名")
    paid_at: models.DateTimeField = models.DateTimeField(null=True, verbose_name="支付时间")
    expired_at: models.DateTimeField = models.DateTimeField(null=True, verbose_name="过期时间")
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table: str = "order"
        ordering: list[str] = ["-created_at"]
        verbose_name: str = "订单"
        verbose_name_plural: str = "订单"

    def __str__(self) -> str:
        return f"Order#{self.order_id} | {self.status}"
