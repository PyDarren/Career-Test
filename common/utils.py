# 画己职测 — 工具函数

import base64
import hashlib
import hmac
import logging
import secrets
import uuid

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def generate_session_token() -> str:
    """生成 UUID4 session token。"""
    token: str = str(uuid.uuid4())
    logger.debug("生成 session | masked=%s", mask_token(token))
    return token


def generate_device_fingerprint() -> str:
    """生成设备指纹（基于 secrets 生成的 64 位十六进制字符串）。"""
    fingerprint: str = secrets.token_hex(32)
    logger.debug("生成 device_fingerprint | fingerprint=%s", fingerprint)
    return fingerprint


def encrypt_data(data: str, key: str) -> str:
    """AES-256-CBC 加密数据，返回 base64 编码字符串。

    :param data: 待加密的明文字符串
    :param key: 加密密钥（将取 SHA-256 前 32 字节作为 AES 密钥）
    :return: base64 编码的密文，格式为 iv_hex + ":" + ciphertext_base64
    """
    key_bytes: bytes = hashlib.sha256(key.encode("utf-8")).digest()
    iv: bytes = secrets.token_bytes(16)

    # PKCS7 填充
    pad_len: int = 16 - (len(data.encode("utf-8")) % 16)
    padded_data: bytes = data.encode("utf-8") + bytes([pad_len] * pad_len)

    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext: bytes = encryptor.update(padded_data) + encryptor.finalize()

    result: str = iv.hex() + ":" + base64.b64encode(ciphertext).decode("utf-8")
    return result


def decrypt_data(encrypted: str, key: str) -> str:
    """AES-256-CBC 解密数据。

    :param encrypted: encrypt_data 返回的加密字符串
    :param key: 解密密钥
    :return: 解密后的明文字符串
    """
    key_bytes: bytes = hashlib.sha256(key.encode("utf-8")).digest()

    iv_hex, ciphertext_b64 = encrypted.split(":", 1)
    iv: bytes = bytes.fromhex(iv_hex)
    ciphertext: bytes = base64.b64decode(ciphertext_b64)

    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data: bytes = decryptor.update(ciphertext) + decryptor.finalize()

    # 移除 PKCS7 填充
    pad_len: int = padded_data[-1]
    data: str = padded_data[:-pad_len].decode("utf-8")
    return data


def generate_order_signature(order_id: str, amount: float, timestamp: str, secret: str) -> str:
    """生成 HMAC-SHA256 订单签名。

    :param order_id: 订单号
    :param amount: 金额
    :param timestamp: 时间戳字符串
    :param secret: 签名密钥
    :return: 十六进制签名字符串
    """
    message: str = f"{order_id}:{amount:.2f}:{timestamp}"
    signature: str = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def verify_order_signature(
    order_id: str,
    amount: float,
    timestamp: str,
    secret: str,
    signature: str,
) -> bool:
    """验证 HMAC-SHA256 订单签名。

    :param order_id: 订单号
    :param amount: 金额
    :param timestamp: 时间戳字符串
    :param secret: 签名密钥
    :param signature: 待验证的签名
    :return: 验证是否通过
    """
    expected: str = generate_order_signature(order_id, amount, timestamp, secret)
    result: bool = hmac.compare_digest(expected, signature)
    if not result:
        logger.warning("签名验证失败 | order_id=%s", order_id)
    return result


def get_client_ip(request: HttpRequest) -> str:
    """获取客户端 IP 地址。"""
    x_forwarded_for: str = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if x_forwarded_for:
        ip: str = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    return ip


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****1234。"""
    if len(phone) < 7:
        return "****"
    return phone[:3] + "****" + phone[-4:]


def mask_answers(count: int) -> str:
    """答题数据脱敏：[***80 items***]。"""
    return f"[***{count} items***]"


def mask_token(token: str) -> str:
    """session_token 脱敏：只显示前 8 位 + ***。

    用于日志记录中避免泄露完整 session_token，防止越权访问。

    :param token: 完整的 session_token
    :return: 脱敏后的字符串，如 "abcdefgh***"
    """
    if not token:
        return ""
    if len(token) <= 8:
        return token[:4] + "***"
    return token[:8] + "***"
