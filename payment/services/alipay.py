# 画己职测 — 支付宝支付服务
#
# 本模块负责支付宝支付相关的业务逻辑：
#   1. 创建支付宝订单（手机网站支付 H5）
#   2. 验证支付宝回调签名
#   3. 解析支付宝回调数据
#
# 开发环境使用模拟模式，不调用真实支付宝 API。
# 读取 settings.ALIPAY 配置，若 app_id 为空则启用模拟模式。

import hashlib
import hmac
import logging
import secrets

from django.conf import settings

logger = logging.getLogger(__name__)


def _is_mock_mode() -> bool:
    """判断是否为模拟模式。

    当 ALIPAY 配置中 app_id 为空时，启用模拟模式。

    :return: 是否模拟模式
    """
    alipay_config: dict[str, str] = getattr(settings, "ALIPAY", {})
    app_id: str = alipay_config.get("app_id", "")
    is_mock: bool = not app_id
    if is_mock:
        logger.debug("支付宝模拟模式已启用 | app_id 为空")
    return is_mock


def _get_private_key() -> str:
    """获取支付宝私钥。

    :return: 私钥字符串
    """
    alipay_config: dict[str, str] = getattr(settings, "ALIPAY", {})
    return alipay_config.get("private_key", "")


def create_h5_payment(order_id: str, amount: float) -> dict[str, object]:
    """创建支付宝手机网站支付订单（H5）。

    开发环境模拟模式下，返回模拟的支付跳转链接。
    生产环境将调用支付宝统一下单 API。

    :param order_id: 订单号
    :param amount: 金额（元）
    :return: H5 支付参数字典
    """
    logger.info(
        "创建支付宝 H5 支付 | order_id=%s | amount=%.2f",
        order_id,
        amount,
    )

    if _is_mock_mode():
        mock_url: str = f"https://mock.alipay.example.com/h5?order_id={order_id}&amount={amount:.2f}"
        trade_no: str = "alipay" + secrets.token_hex(16)
        result: dict[str, object] = {
            "mock": True,
            "pay_url": mock_url,
            "trade_no": trade_no,
        }
        logger.info(
            "支付宝 H5 支付模拟链接生成 | order_id=%s | url=%s",
            order_id,
            mock_url,
        )
        return result

    # 生产环境：调用支付宝手机网站支付 API
    # M4 阶段接入真实支付宝 SDK
    logger.warning("生产环境支付宝尚未接入，返回模拟参数 | order_id=%s", order_id)
    trade_no = "alipay" + secrets.token_hex(16)
    return {
        "mock": True,
        "pay_url": f"https://mock.alipay.example.com/h5?order_id={order_id}&amount={amount:.2f}",
        "trade_no": trade_no,
    }


def verify_callback(raw_data: dict[str, object]) -> bool:
    """验证支付宝回调签名。

    开发环境使用简化 HMAC 验证：
    - 如果 raw_data 中包含 "sign" 字段，使用私钥做 HMAC-SHA256 验证
    - 模拟模式下，如果没有 sign 字段，视为验证通过（便于测试）

    :param raw_data: 回调原始数据
    :return: 签名验证是否通过
    """
    private_key: str = _get_private_key()
    sign: str = str(raw_data.get("sign", ""))

    # 模拟模式下，无签名视为通过
    if _is_mock_mode() and not sign:
        logger.debug("模拟模式下无签名，回调验证通过")
        return True

    if not sign:
        logger.warning("支付宝回调验证失败 | 缺少 sign 字段")
        return False

    # 构造待签名字符串：out_trade_no + trade_no + total_amount
    out_trade_no: str = str(raw_data.get("out_trade_no", ""))
    trade_no: str = str(raw_data.get("trade_no", ""))
    total_amount: str = str(raw_data.get("total_amount", ""))
    message: str = f"{out_trade_no}{trade_no}{total_amount}"

    expected: str = hmac.new(
        private_key.encode("utf-8") or b"mock-key",
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    result: bool = hmac.compare_digest(expected, sign)
    if not result:
        logger.warning(
            "支付宝回调签名验证失败 | order_id=%s | expected=%s | got=%s",
            out_trade_no,
            expected,
            sign,
        )
    return result


def parse_callback(raw_data: dict[str, object]) -> dict[str, object]:
    """解析支付宝回调数据。

    :param raw_data: 回调原始数据
    :return: 解析后的字典 {out_trade_no, transaction_id, amount, status}
    """
    out_trade_no: str = str(raw_data.get("out_trade_no", ""))
    trade_no: str = str(raw_data.get("trade_no", ""))
    total_amount_raw: object = raw_data.get("total_amount", 0)

    # 支付宝回调金额单位为元（字符串）
    if isinstance(total_amount_raw, (int, float)):
        amount: float = float(total_amount_raw)
    else:
        try:
            amount = float(total_amount_raw)
        except (ValueError, TypeError):
            amount = 0.0

    # 支付宝回调中的 trade_status
    trade_status: str = str(raw_data.get("trade_status", ""))
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        status: str = "paid"
    else:
        status = "failed"

    result: dict[str, object] = {
        "out_trade_no": out_trade_no,
        "transaction_id": trade_no,
        "amount": amount,
        "status": status,
    }

    logger.info(
        "支付宝回调解析完成 | order_id=%s | trade_no=%s | amount=%.2f | status=%s",
        out_trade_no,
        trade_no,
        amount,
        status,
    )
    return result
