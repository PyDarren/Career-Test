# 画己职测 — payment DRF 序列化器
#
# 本模块定义支付订单相关的所有 DRF 序列化器：
#   - CreateOrderSerializer: 创建订单（接收 payment_channel, assessment_id, coupon_code）
#   - OrderStatusSerializer: 订单状态
#   - OrderListSerializer: 订单列表项
#   - OrderDetailSerializer: 订单详情
#   - CouponSerializer: 优惠券验证

import logging

from rest_framework import serializers

from common.constants import PAYMENT_CHANNELS

logger = logging.getLogger(__name__)


class CreateOrderSerializer(serializers.Serializer):
    """创建订单序列化器。"""

    payment_channel = serializers.ChoiceField(
        choices=[(ch, ch) for ch in PAYMENT_CHANNELS],
        help_text="支付渠道：wechat_pay / alipay",
    )
    assessment_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="关联的测评 ID（可选）",
    )
    coupon_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=32,
        help_text="优惠券码（可选）",
    )

    def validate_coupon_code(self, value: str) -> str:
        """验证优惠券码格式（仅格式校验，具体业务在 M4 实现）。"""
        if value and len(value) < 4:
            raise serializers.ValidationError("优惠券码长度至少 4 位")
        return value


class OrderStatusSerializer(serializers.Serializer):
    """订单状态序列化器。"""

    order_id = serializers.CharField()
    status = serializers.CharField()
    amount = serializers.CharField()
    payment_channel = serializers.CharField(allow_null=True)
    transaction_id = serializers.CharField(allow_null=True)
    created_at = serializers.CharField()
    paid_at = serializers.CharField(allow_null=True)


class OrderListSerializer(serializers.Serializer):
    """订单列表项序列化器。"""

    order_id = serializers.CharField()
    session_token = serializers.CharField()
    assessment_id = serializers.IntegerField(allow_null=True)
    amount = serializers.CharField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    payment_channel = serializers.CharField(allow_null=True)
    transaction_id = serializers.CharField(allow_null=True)
    created_at = serializers.CharField()
    paid_at = serializers.CharField(allow_null=True)


class OrderDetailSerializer(serializers.Serializer):
    """订单详情序列化器。"""

    order_id = serializers.CharField()
    session_token = serializers.CharField()
    assessment_id = serializers.IntegerField(allow_null=True)
    device_fingerprint = serializers.CharField()
    amount = serializers.CharField()
    product_name = serializers.CharField()
    status = serializers.CharField()
    payment_channel = serializers.CharField(allow_null=True)
    transaction_id = serializers.CharField(allow_null=True)
    signature = serializers.CharField()
    created_at = serializers.CharField()
    updated_at = serializers.CharField()
    paid_at = serializers.CharField(allow_null=True)
    expired_at = serializers.CharField(allow_null=True)


class CouponSerializer(serializers.Serializer):
    """优惠券验证序列化器。"""

    coupon_code = serializers.CharField(
        max_length=32,
        help_text="优惠券码",
    )
    assessment_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="关联的测评 ID（可选）",
    )

    def validate_coupon_code(self, value: str) -> str:
        """验证优惠券码格式。"""
        if not value or len(value) < 4:
            raise serializers.ValidationError("优惠券码长度至少 4 位")
        return value
