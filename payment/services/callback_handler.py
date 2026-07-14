# 画己职测 — 支付回调处理器
#
# 本模块负责统一处理各支付渠道的回调通知，实现支付安全六道防线：
#   防线1：来源校验 — 校验回调来源渠道合法
#   防线2：签名验证 — 验证回调签名（开发环境用简化 HMAC 验证）
#   防线3：幂等去重 — 检查订单是否已支付，防止重复处理
#   防线4：订单存在性校验 — 确保回调对应的订单存在
#   防线5：金额一致性校验 — callback amount == order.amount == 2.99
#   防线6：状态机校验 — 订单状态必须为 pending 才能转为 paid
#
# 使用 @transaction.atomic + select_for_update 保证并发安全。

import logging

from django.db import transaction
from django.utils import timezone

from common.constants import DEEP_REPORT_PRICE
from common.utils import mask_token
from payment.models import Order
from payment.services import alipay as alipay_service
from payment.services import wechat_pay as wechat_service

logger = logging.getLogger(__name__)


def handle_payment_callback(raw_callback: dict[str, object], channel: str) -> dict[str, object]:
    """统一回调处理。

    处理流程（六道防线）：
      防线1：来源校验 — 校验 channel 合法
      防线2：签名验证 — 调用对应渠道的 verify_callback
      防线3：幂等去重 — 检查订单是否已支付
      防线4：订单存在性校验
      防线5：金额一致性校验
      防线6：状态机校验
      → 更新订单状态为 paid，解锁深度报告

    :param raw_callback: 回调原始数据
    :param channel: 支付渠道（wechat_pay / alipay）
    :return: 处理结果字典 {"success", "duplicated", "rejected", "reason"}
    """
    # 防线1：来源校验 — 校验渠道合法
    if channel not in ("wechat_pay", "alipay"):
        logger.warning("回调来源校验失败 | 不支持的渠道 | channel=%s", channel)
        return {
            "success": False,
            "duplicated": False,
            "rejected": True,
            "reason": f"不支持的支付渠道：{channel}",
        }

    # 防线2：签名验证
    if channel == "wechat_pay":
        signature_valid: bool = wechat_service.verify_callback(raw_callback)
    else:
        signature_valid = alipay_service.verify_callback(raw_callback)

    if not signature_valid:
        logger.warning("回调签名验证失败 | channel=%s", channel)
        return {
            "success": False,
            "duplicated": False,
            "rejected": True,
            "reason": "签名验证失败",
        }

    # 解析回调数据
    if channel == "wechat_pay":
        parsed: dict[str, object] = wechat_service.parse_callback(raw_callback)
    else:
        parsed = alipay_service.parse_callback(raw_callback)

    out_trade_no: str = str(parsed.get("out_trade_no", ""))
    transaction_id: str = str(parsed.get("transaction_id", ""))
    callback_amount: float = float(parsed.get("amount", 0))
    callback_status: str = str(parsed.get("status", ""))

    # 回调状态非 paid，拒绝处理
    if callback_status != "paid":
        logger.warning(
            "回调状态非已支付 | order_id=%s | status=%s",
            out_trade_no,
            callback_status,
        )
        return {
            "success": False,
            "duplicated": False,
            "rejected": True,
            "reason": f"回调状态异常：{callback_status}",
        }

    # 防线3/4/5/6 在事务中处理
    with transaction.atomic():
        # 防线4：订单存在性校验 + 行级锁
        try:
            order: Order = Order.objects.select_for_update().get(order_id=out_trade_no)
        except Order.DoesNotExist:
            logger.warning("回调订单不存在 | order_id=%s", out_trade_no)
            return {
                "success": False,
                "duplicated": False,
                "rejected": True,
                "reason": f"订单不存在：{out_trade_no}",
            }

        # 防线3：幂等去重 — 检查订单是否已支付
        if order.status == Order.OrderStatus.PAID:
            logger.info(
                "回调幂等去重 | 订单已支付 | order_id=%s | transaction_id=%s",
                order.order_id,
                order.transaction_id,
            )
            return {
                "success": True,
                "duplicated": True,
                "rejected": False,
                "reason": "订单已支付，幂等处理",
            }

        # 防线6：状态机校验 — 订单必须为 pending
        if order.status != Order.OrderStatus.PENDING:
            logger.warning(
                "回调状态机校验失败 | order_id=%s | current_status=%s",
                order.order_id,
                order.status,
            )
            return {
                "success": False,
                "duplicated": False,
                "rejected": True,
                "reason": f"订单状态不允许支付：{order.status}",
            }

        # 防线5：金额一致性校验
        order_amount: float = float(order.amount)
        expected_amount: float = DEEP_REPORT_PRICE

        if callback_amount != order_amount or order_amount != expected_amount:
            logger.error(
                "回调金额一致性校验失败 | order_id=%s | callback=%.2f | order=%.2f | expected=%.2f",
                order.order_id,
                callback_amount,
                order_amount,
                expected_amount,
            )
            return {
                "success": False,
                "duplicated": False,
                "rejected": True,
                "reason": (
                    f"金额不一致：callback={callback_amount}, " f"order={order_amount}, expected={expected_amount}"
                ),
            }

        # 所有防线通过，更新订单状态
        order.status = Order.OrderStatus.PAID
        order.transaction_id = transaction_id
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "transaction_id", "paid_at", "updated_at"])

        logger.info(
            "回调处理成功 | 订单已支付 | order_id=%s | transaction_id=%s | amount=%.2f",
            order.order_id,
            transaction_id,
            order_amount,
        )

    # 解锁深度报告
    _unlock_deep_report(order)

    return {
        "success": True,
        "duplicated": False,
        "rejected": False,
        "reason": "支付成功",
    }


def _unlock_deep_report(order: Order) -> None:
    """解锁深度报告。

    支付成功后，将关联测评的深度报告解锁。
    在 M3 阶段，订单状态为 paid 即表示深度报告已解锁，
    后续可通过 order.assessment_id 查询关联测评并生成报告。

    :param order: 已支付的订单
    """
    logger.info(
        "深度报告解锁 | order_id=%s | assessment_id=%s | session=%s",
        order.order_id,
        order.assessment_id,
        mask_token(order.session_token),
    )

    # M3 阶段：订单状态为 paid 即代表解锁成功
    # M4 阶段：在此处触发报告生成或设置缓存标记
