"""支付订单模型。

对应数据库表 order，管理 2.99 元深度报告的支付订单。
订单状态机：pending → paid / failed / expired。
包含 6 道支付安全防线中的数据库层防护。
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone


class Order(models.Model):
    """支付订单表。

    金额由服务端硬编码为 Decimal('2.99')，不从前端读取。
    同一 assessment 仅允许一个 paid 订单（数据库唯一约束）。
    订单 15 分钟自动过期。
    """

    STATUS_CHOICES = [
        ('pending', '待支付'),
        ('paid', '已支付'),
        ('failed', '支付失败'),
        ('expired', '已过期'),
        ('refunded', '已退款'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('wechat', '微信支付'),
        ('alipay', '支付宝'),
    ]

    order_no = models.CharField(max_length=32, unique=True, db_index=True, verbose_name='订单号')
    uuid = models.CharField(max_length=36, db_index=True, verbose_name='用户会话ID')
    assessment_id = models.BigIntegerField(verbose_name='关联测评记录ID')
    amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('2.99'), verbose_name='支付金额')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name='订单状态')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True, verbose_name='支付方式')
    payment_id = models.CharField(max_length=64, null=True, blank=True, verbose_name='第三方支付流水号')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='支付成功时间')
    expires_at = models.DateTimeField(verbose_name='过期时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'order'
        verbose_name = '订单'
        verbose_name_plural = '订单'
        constraints = [
            # 同一 assessment 只允许一个 paid 订单
            models.UniqueConstraint(
                fields=['assessment_id'],
                condition=models.Q(status='paid'),
                name='unique_paid_order_per_assessment',
            ),
        ]
        indexes = [
            models.Index(fields=['uuid'], name='idx_order_uuid'),
            models.Index(fields=['status'], name='idx_order_status'),
            models.Index(fields=['order_no'], name='idx_order_no'),
        ]

    def __str__(self) -> str:
        return f'{self.order_no} ({self.status})'

    @property
    def is_expired(self) -> bool:
        """检查订单是否已过期（pending 状态且超过 expires_at）。"""
        return self.status == 'pending' and self.expires_at < timezone.now()

    @property
    def is_paid(self) -> bool:
        """检查订单是否已支付。"""
        return self.status == 'paid'

    def mark_as_paid(self, payment_id: str, payment_method: str = '') -> None:
        """标记订单为已支付，含状态校验。

        Args:
            payment_id: 第三方支付流水号。
            payment_method: 支付方式（wechat/alipay）。

        Raises:
            ValueError: 订单状态不为 pending 时抛出异常。
        """
        if self.status != 'pending':
            raise ValueError(f'订单状态为 {self.status}，不能标记为已支付')
        self.status = 'paid'
        self.payment_id = payment_id
        if payment_method:
            self.payment_method = payment_method
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'payment_id', 'payment_method', 'paid_at'])

    def mark_as_expired(self) -> None:
        """标记订单为已过期。"""
        if self.status != 'pending':
            return
        self.status = 'expired'
        self.save(update_fields=['status'])
