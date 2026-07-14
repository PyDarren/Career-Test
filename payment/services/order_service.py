# 画己职测 — 订单服务
#
# 本模块负责订单的创建与查询业务逻辑：
#   1. 创建订单（生成订单号、签名、入库）
#   2. 查询订单状态
#   3. 按 session_token 查询订单列表
#   4. 查询订单详情

import logging
import secrets
from datetime import datetime

from django.conf import settings
from django.db import transaction

from common.constants import DEEP_REPORT_PRICE, PAYMENT_CHANNELS
from common.utils import generate_order_signature, mask_token
from payment.models import Order

logger = logging.getLogger(__name__)


def _generate_order_id() -> str:
    """生成订单号：CT + yyyyMMddHHmmss + 6 位随机十六进制。

    :return: 订单号字符串
    """
    timestamp: str = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part: str = secrets.token_hex(3)  # 6 位十六进制
    order_id: str = f"CT{timestamp}{random_part}"
    return order_id


def _format_order_brief(order: Order) -> dict[str, object]:
    """将订单对象格式化为简要信息字典。

    :param order: 订单模型实例
    :return: 简要信息字典
    """
    return {
        "order_id": order.order_id,
        "session_token": order.session_token,
        "assessment_id": order.assessment_id,
        "amount": str(order.amount),
        "product_name": order.product_name,
        "status": order.status,
        "payment_channel": order.payment_channel,
        "transaction_id": order.transaction_id,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "",
        "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
    }


def _format_order_detail(order: Order) -> dict[str, object]:
    """将订单对象格式化为详情字典。

    :param order: 订单模型实例
    :return: 详情字典
    """
    return {
        "order_id": order.order_id,
        "session_token": order.session_token,
        "assessment_id": order.assessment_id,
        "device_fingerprint": order.device_fingerprint,
        "amount": str(order.amount),
        "product_name": order.product_name,
        "status": order.status,
        "payment_channel": order.payment_channel,
        "transaction_id": order.transaction_id,
        "signature": order.signature,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "",
        "updated_at": order.updated_at.strftime("%Y-%m-%d %H:%M:%S") if order.updated_at else "",
        "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
        "expired_at": order.expired_at.strftime("%Y-%m-%d %H:%M:%S") if order.expired_at else "",
    }


def create_order(
    session_token: str,
    device_fingerprint: str,
    assessment_id: int | None,
    payment_channel: str,
) -> dict[str, object]:
    """创建支付订单。

    流程：
      1. 校验 session_token 和 device_fingerprint 非空
      2. 校验 payment_channel 合法
      3. 生成订单号（CT + 时间戳 + 6 位随机）
      4. 金额固定 2.99 元
      5. HMAC-SHA256 签名
      6. 入库并返回订单信息

    :param session_token: 会话令牌
    :param device_fingerprint: 设备指纹
    :param assessment_id: 关联的测评 ID（可为 None）
    :param payment_channel: 支付渠道（wechat_pay / alipay）
    :return: 订单信息字典
    :raises ValueError: 参数校验失败
    """
    # 校验 session_token
    if not session_token:
        logger.warning("创建订单失败 | 原因=session_token 为空")
        raise ValueError("session_token 不能为空")

    # 校验 device_fingerprint
    if not device_fingerprint:
        logger.warning("创建订单失败 | 原因=device_fingerprint 为空")
        raise ValueError("device_fingerprint 不能为空")

    # 校验支付渠道
    if payment_channel not in PAYMENT_CHANNELS:
        logger.warning(
            "创建订单失败 | 原因=不支持的支付渠道 | channel=%s",
            payment_channel,
        )
        raise ValueError(f"不支持的支付渠道：{payment_channel}，支持：{PAYMENT_CHANNELS}")

    # 生成订单号
    order_id: str = _generate_order_id()

    # 金额固定 2.99 元
    amount: float = DEEP_REPORT_PRICE

    # 生成时间戳（用于签名）
    timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # HMAC-SHA256 签名
    secret: str = getattr(settings, "ORDER_SIGNATURE_SECRET", "")
    signature: str = generate_order_signature(order_id, amount, timestamp, secret)

    logger.info(
        "创建订单 | order_id=%s | amount=%.2f | channel=%s | session=%s",
        order_id,
        amount,
        payment_channel,
        mask_token(session_token),
    )

    # 入库
    with transaction.atomic():
        order: Order = Order.objects.create(
            order_id=order_id,
            session_token=session_token,
            assessment_id=assessment_id,
            device_fingerprint=device_fingerprint,
            amount=amount,
            product_name="职业人格深度报告",
            status=Order.OrderStatus.PENDING,
            payment_channel=payment_channel,
            signature=signature,
        )

    logger.info("订单创建成功 | order_id=%s | id=%d", order.order_id, order.id)

    return _format_order_detail(order)


def get_order_status(order_id: str) -> dict[str, object] | None:
    """查询订单状态。

    :param order_id: 订单号
    :return: 订单状态字典，不存在时返回 None
    """
    try:
        order: Order = Order.objects.only(
            "order_id", "status", "amount", "payment_channel", "transaction_id", "created_at", "paid_at"
        ).get(order_id=order_id)
    except Order.DoesNotExist:
        logger.warning("查询订单状态失败 | 订单不存在 | order_id=%s", order_id)
        return None

    return {
        "order_id": order.order_id,
        "status": order.status,
        "amount": str(order.amount),
        "payment_channel": order.payment_channel,
        "transaction_id": order.transaction_id,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if order.created_at else "",
        "paid_at": order.paid_at.strftime("%Y-%m-%d %H:%M:%S") if order.paid_at else "",
    }


def get_orders_by_session(session_token: str) -> list[dict[str, object]]:
    """按 session_token 查询订单列表。

    :param session_token: 会话令牌
    :return: 订单简要信息列表
    """
    if not session_token:
        logger.warning("查询订单列表失败 | session_token 为空")
        return []

    # 使用 .only() 限制查询字段，避免拉取不必要的列（如 signature）
    orders: list[Order] = list(
        Order.objects.filter(session_token=session_token)
        .only(
            "order_id",
            "session_token",
            "assessment_id",
            "amount",
            "product_name",
            "status",
            "payment_channel",
            "transaction_id",
            "created_at",
            "paid_at",
        )
        .order_by("-created_at")
    )

    logger.info(
        "查询订单列表 | session=%s | count=%d",
        mask_token(session_token),
        len(orders),
    )

    return [_format_order_brief(o) for o in orders]


def get_order_detail(order_id: str) -> dict[str, object] | None:
    """查询订单详情。

    :param order_id: 订单号
    :return: 订单详情字典，不存在时返回 None
    """
    try:
        order: Order = Order.objects.only(
            "order_id",
            "session_token",
            "assessment_id",
            "device_fingerprint",
            "amount",
            "product_name",
            "status",
            "payment_channel",
            "transaction_id",
            "signature",
            "created_at",
            "updated_at",
            "paid_at",
            "expired_at",
        ).get(order_id=order_id)
    except Order.DoesNotExist:
        logger.warning("查询订单详情失败 | 订单不存在 | order_id=%s", order_id)
        return None

    logger.info("查询订单详情 | order_id=%s | status=%s", order_id, order.status)

    return _format_order_detail(order)
