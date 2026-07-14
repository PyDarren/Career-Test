# 画己职测 — 微信支付服务
#
# 本模块负责微信支付相关的业务逻辑：
#   1. 创建微信支付订单（JSAPI 支付 — 微信内）
#   2. 创建微信支付订单（H5 支付 — 微信外）
#   3. 验证微信支付回调签名
#   4. 解析微信支付回调数据
#
# 开发环境使用模拟模式，不调用真实微信 API。
# 读取 settings.WECHAT_PAY 配置，若 appid/mchid 为空则启用模拟模式。

import hashlib
import hmac
import logging
import secrets
from datetime import datetime

from django.conf import settings

logger = logging.getLogger(__name__)


def _is_mock_mode() -> bool:
    """判断是否为模拟模式。

    当 WECHAT_PAY 配置中 appid 或 mchid 为空时，启用模拟模式。

    :return: 是否模拟模式
    """
    wechat_config: dict[str, str] = getattr(settings, "WECHAT_PAY", {})
    appid: str = wechat_config.get("appid", "")
    mchid: str = wechat_config.get("mchid", "")
    is_mock: bool = not appid or not mchid
    if is_mock:
        logger.debug("微信支付模拟模式已启用 | appid 为空或 mchid 为空")
    return is_mock


def _get_api_key() -> str:
    """获取微信支付 API V3 密钥。

    :return: API V3 密钥
    """
    wechat_config: dict[str, str] = getattr(settings, "WECHAT_PAY", {})
    return wechat_config.get("api_v3_key", "")


def _generate_mock_prepay_id(order_id: str) -> str:
    """生成模拟的预支付 ID。

    :param order_id: 订单号
    :return: 模拟预支付 ID
    """
    return "wx" + secrets.token_hex(16)


def create_jsapi_payment(order_id: str, amount: float, openid: str) -> dict[str, object]:
    """创建 JSAPI 支付订单（微信内 H5）。

    开发环境模拟模式下，返回模拟的支付参数。
    生产环境将调用微信支付统一下单 API。

    :param order_id: 订单号
    :param amount: 金额（元）
    :param openid: 微信用户的 openid
    :return: JSAPI 支付参数字典
    """
    logger.info(
        "创建 JSAPI 支付 | order_id=%s | amount=%.2f | openid=%s",
        order_id,
        amount,
        openid[:8] + "***" if len(openid) > 8 else openid,
    )

    if _is_mock_mode():
        prepay_id: str = _generate_mock_prepay_id(order_id)
        nonce_str: str = secrets.token_hex(16)
        timestamp_str: str = str(int(datetime.now().timestamp()))
        pay_sign: str = hmac.new(
            _get_api_key().encode("utf-8") or b"mock-key",
            f"{prepay_id}{nonce_str}{timestamp_str}".encode(),
            hashlib.sha256,
        ).hexdigest()

        result: dict[str, object] = {
            "mock": True,
            "appId": getattr(settings, "WECHAT_PAY", {}).get("appid", "mock-appid"),
            "timeStamp": timestamp_str,
            "nonceStr": nonce_str,
            "package": f"prepay_id={prepay_id}",
            "signType": "HMAC-SHA256",
            "paySign": pay_sign,
        }
        logger.info("JSAPI 支付模拟参数生成 | order_id=%s | prepay_id=%s", order_id, prepay_id)
        return result

    # 生产环境：调用微信支付统一下单 API
    # M4 阶段接入真实微信支付 SDK
    logger.warning("生产环境微信支付尚未接入，返回模拟参数 | order_id=%s", order_id)
    prepay_id = _generate_mock_prepay_id(order_id)
    return {
        "mock": True,
        "appId": getattr(settings, "WECHAT_PAY", {}).get("appid", ""),
        "timeStamp": str(int(datetime.now().timestamp())),
        "nonceStr": secrets.token_hex(16),
        "package": f"prepay_id={prepay_id}",
        "signType": "HMAC-SHA256",
        "paySign": "",
    }


def create_h5_payment(order_id: str, amount: float, client_ip: str) -> dict[str, object]:
    """创建 H5 支付订单（微信外浏览器）。

    开发环境模拟模式下，返回模拟的支付跳转链接。
    生产环境将调用微信支付 H5 统一下单 API。

    :param order_id: 订单号
    :param amount: 金额（元）
    :param client_ip: 客户端 IP
    :return: H5 支付参数字典
    """
    logger.info(
        "创建 H5 支付 | order_id=%s | amount=%.2f | ip=%s",
        order_id,
        amount,
        client_ip,
    )

    if _is_mock_mode():
        prepay_id: str = _generate_mock_prepay_id(order_id)
        mock_url: str = f"https://mock.pay.example.com/h5?order_id={order_id}&prepay_id={prepay_id}"
        result: dict[str, object] = {
            "mock": True,
            "h5_url": mock_url,
            "prepay_id": prepay_id,
        }
        logger.info("H5 支付模拟链接生成 | order_id=%s | url=%s", order_id, mock_url)
        return result

    # 生产环境：调用微信支付 H5 统一下单 API
    # M4 阶段接入真实微信支付 SDK
    logger.warning("生产环境微信支付尚未接入，返回模拟参数 | order_id=%s", order_id)
    prepay_id = _generate_mock_prepay_id(order_id)
    return {
        "mock": True,
        "h5_url": f"https://mock.pay.example.com/h5?order_id={order_id}&prepay_id={prepay_id}",
        "prepay_id": prepay_id,
    }


def verify_callback(raw_data: dict[str, object]) -> bool:
    """验证微信支付回调签名。

    开发环境使用简化 HMAC 验证：
    - 如果 raw_data 中包含 "signature" 字段，使用 API V3 密钥做 HMAC-SHA256 验证
    - 模拟模式下，如果没有 signature 字段，视为验证通过（便于测试）

    :param raw_data: 回调原始数据
    :return: 签名验证是否通过
    """
    api_key: str = _get_api_key()
    signature: str = str(raw_data.get("signature", ""))

    # 模拟模式下，无签名视为通过
    if _is_mock_mode() and not signature:
        logger.debug("模拟模式下无签名，回调验证通过")
        return True

    if not signature:
        logger.warning("微信回调验证失败 | 缺少 signature 字段")
        return False

    # 构造待签名字符串：out_trade_no + transaction_id + amount
    out_trade_no: str = str(raw_data.get("out_trade_no", ""))
    transaction_id: str = str(raw_data.get("transaction_id", ""))
    amount_str: str = str(raw_data.get("amount", ""))
    message: str = f"{out_trade_no}{transaction_id}{amount_str}"

    expected: str = hmac.new(
        api_key.encode("utf-8") or b"mock-key",
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    result: bool = hmac.compare_digest(expected, signature)
    if not result:
        logger.warning(
            "微信回调签名验证失败 | order_id=%s | expected=%s | got=%s",
            out_trade_no,
            expected,
            signature,
        )
    return result


def parse_callback(raw_data: dict[str, object]) -> dict[str, object]:
    """解析微信支付回调数据。

    :param raw_data: 回调原始数据
    :return: 解析后的字典 {out_trade_no, transaction_id, amount, status}
    """
    out_trade_no: str = str(raw_data.get("out_trade_no", ""))
    transaction_id: str = str(raw_data.get("transaction_id", ""))
    amount_raw: object = raw_data.get("amount", 0)

    # 微信回调金额单位为分，转换为元
    if isinstance(amount_raw, (int, float)):
        amount: float = float(amount_raw) / 100.0
    else:
        amount = float(amount_raw)

    # 回调中的 trade_state：SUCCESS / REFUND / NOTPAY / CLOSED / REVOKED / USERPAYING / PAYERROR
    trade_state: str = str(raw_data.get("trade_state", raw_data.get("status", "")))
    status: str = "paid" if trade_state == "SUCCESS" else "failed"

    result: dict[str, object] = {
        "out_trade_no": out_trade_no,
        "transaction_id": transaction_id,
        "amount": amount,
        "status": status,
    }

    logger.info(
        "微信回调解析完成 | order_id=%s | transaction_id=%s | amount=%.2f | status=%s",
        out_trade_no,
        transaction_id,
        amount,
        status,
    )
    return result
