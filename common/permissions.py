# 画己职测 — 权限类

import logging

from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request

from common.utils import mask_token

logger = logging.getLogger(__name__)


class AdminPermission(BasePermission):
    """权限类：校验 Admin API 请求头 X-Admin-Token。

    由于项目当前无 Django auth 用户系统（使用匿名 session），
    通过请求头 X-Admin-Token 与 settings.ADMIN_TOKEN 比对来鉴权。
    生产环境必须通过环境变量 ADMIN_TOKEN 设置真实值。
    """

    message: str = "管理员认证失败"

    def has_permission(self, request: Request, view: object) -> bool:
        admin_token: str = getattr(settings, "ADMIN_TOKEN", "")
        if not admin_token:
            logger.warning("Admin API 认证失败 | 原因=settings.ADMIN_TOKEN 未配置")
            return False

        request_token: str = request.META.get("HTTP_X_ADMIN_TOKEN", "")
        if not request_token:
            return False

        # 使用 hmac.compare_digest 防止时序攻击
        import hmac

        result: bool = hmac.compare_digest(request_token, admin_token)
        if not result:
            logger.warning("Admin API 认证失败 | 原因=X-Admin-Token 不匹配")
        return result


class IsOwnerOrReadOnly(BasePermission):
    """权限类：检查 device_fingerprint 是否匹配。
    安全方法（GET/HEAD/OPTIONS）允许所有用户访问；
    写操作仅允许设备指纹匹配的拥有者操作。"""

    def has_permission(self, request: Request, view: object) -> bool:
        if request.method in SAFE_METHODS:
            return True
        device_fingerprint: str = getattr(request, "device_fingerprint", "")
        return bool(device_fingerprint)

    def has_object_permission(self, request: Request, view: object, obj: object) -> bool:
        if request.method in SAFE_METHODS:
            return True
        obj_fingerprint: str = getattr(obj, "device_fingerprint", "")
        request_fingerprint: str = getattr(request, "device_fingerprint", "")
        return obj_fingerprint == request_fingerprint


class HasPaidForReport(BasePermission):
    """权限类：检查用户是否已支付深度报告。
    通过查询订单表判断该 session_token 对应的订单是否已支付。"""

    message: str = "请先购买深度报告"

    def has_permission(self, request: Request, view: object) -> bool:
        session_token: str = getattr(request, "session_token", "")
        if not session_token:
            return False

        from payment.models import Order

        paid_exists: bool = Order.objects.filter(
            session_token=session_token,
            status="paid",
        ).exists()
        if not paid_exists:
            logger.info("权限拒绝 — 未支付报告 | session=%s", mask_token(session_token))
        return paid_exists
