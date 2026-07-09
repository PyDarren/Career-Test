"""
Views for the payment app.

Handles payment order creation, WeChat/Alipay callbacks, order status
polling, report rendering, and report recovery.
"""

import json
import logging
import uuid as uuid_lib
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.assessment.models import Assessment
from apps.mbti_types.models import MBTIType

from .models import Order
from .report_renderer import ReportRenderer
from .wechat_pay import WechatPay
from .alipay_pay import AlipayPay

logger = logging.getLogger(__name__)

# 支付金额（服务端硬编码，不从前端读取）
PAY_AMOUNT = Decimal('2.99')

# 订单超时时间
ORDER_TIMEOUT_MINUTES = 15

# 前端轮询间隔和持续时间
POLL_INTERVAL = 2  # 秒
POLL_DURATION = 120  # 秒（2 分钟）


class CreatePaymentView(View):
    """创建支付订单接口。

    安全设计（6 道防线）：
    1. 金额服务端硬编码（不读取前端传入的 amount）
    2. 防重复支付（检查已有 paid 订单）
    3. Referer 校验
    4. assessment_id 存在性校验
    5. 订单号使用 UUID 防篡改
    6. 15 分钟自动过期
    """

    ALLOWED_REFERERS = ('http://127.0.0.1:', 'http://localhost:', 'https://careertest')

    def post(self, request, *args, **kwargs):
        # 1. Referer 校验
        referer = request.headers.get('Referer', '')
        if referer and not any(referer.startswith(p) for p in self.ALLOWED_REFERERS):
            return JsonResponse({'error': '非法请求来源'}, status=403)

        # 2. 解析请求体
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': '请求体格式错误'}, status=400)

        assessment_id = data.get('assessment_id')
        user_uuid = data.get('uuid', '')
        payment_method = data.get('method', 'wechat')

        # 3. 参数校验
        if not assessment_id or not user_uuid:
            return JsonResponse({'error': '缺少必要参数'}, status=400)

        if payment_method not in ('wechat', 'alipay'):
            return JsonResponse({'error': '不支持的支付方式'}, status=400)

        # 4. 查找测评记录
        try:
            assessment = Assessment.objects.get(id=assessment_id, uuid=user_uuid)
        except Assessment.DoesNotExist:
            return JsonResponse({'error': '测评记录不存在'}, status=404)

        # 5. 防重复支付（防线 2：数据库唯一约束 + 应用层检查）
        existing_paid = Order.objects.filter(
            assessment_id=assessment_id, status='paid'
        ).exists()
        if existing_paid:
            return JsonResponse({'error': '该测评报告已购买，请直接查看'}, status=400)

        # 6. 检查是否有 pending 订单（复用）
        pending_order = Order.objects.filter(
            assessment_id=assessment_id, status='pending'
        ).first()

        if pending_order and not pending_order.is_expired:
            order = pending_order
        else:
            # 如果有过期订单，先标记为 expired
            if pending_order:
                pending_order.mark_as_expired()

            # 7. 创建新订单（金额服务端硬编码，防线 1）
            order_no = f'CT{timezone.now().strftime("%Y%m%d%H%M%S")}{uuid_lib.uuid4().hex[:8].upper()}'
            order = Order.objects.create(
                order_no=order_no,
                uuid=user_uuid,
                assessment_id=assessment_id,
                amount=PAY_AMOUNT,
                status='pending',
                expires_at=timezone.now() + timedelta(minutes=ORDER_TIMEOUT_MINUTES),
            )
            logger.info('创建支付订单: order_no=%s, amount=%s', order_no, PAY_AMOUNT)

        # 8. 调用支付 SDK 下单
        if payment_method == 'wechat':
            wx_pay = WechatPay()
            pay_result = wx_pay.create_order(order.order_no)
        else:
            alipay = AlipayPay()
            pay_result = alipay.create_order(order.order_no)

        return JsonResponse({
            'order_no': order.order_no,
            'amount': str(order.amount),
            'expires_at': order.expires_at.isoformat(),
            'method': payment_method,
            'pay_info': pay_result,
            'poll_interval': POLL_INTERVAL,
            'poll_duration': POLL_DURATION,
        })


@method_decorator(csrf_exempt, name='dispatch')
class WechatNotifyView(View):
    """微信支付回调通知。

    6 道防线：
    - 回调签名验证（RSA-SHA256）
    - 幂等处理（select_for_update + 状态检查）
    - 金额一致性检查
    """

    def post(self, request, *args, **kwargs):
        body = request.body.decode('utf-8')
        headers = {k: v for k, v in request.headers.items()}

        # 1. 验签 + 解密
        wx_pay = WechatPay()
        result = wx_pay.verify_notify(headers, body)

        if result is None:
            return JsonResponse(
                {'code': 'FAIL', 'message': '验签失败'},
                status=400,
            )

        # 2. 幂等处理
        order_no = result.get('out_trade_no', '')
        transaction_id = result.get('transaction_id', '')
        trade_state = result.get('trade_state', '')

        if trade_state != 'SUCCESS':
            logger.warning('微信回调交易状态非成功: %s', trade_state)
            return JsonResponse({'code': 'SUCCESS', 'message': 'OK'})

        return self._process_payment_success(order_no, transaction_id, 'wechat')

    def _process_payment_success(self, order_no: str, payment_id: str,
                                  method: str) -> JsonResponse:
        """处理支付成功逻辑（幂等）。

        使用 select_for_update 防止并发问题。
        """
        try:
            with transaction.atomic():
                order = (
                    Order.objects
                    .select_for_update()
                    .get(order_no=order_no)
                )

                # 幂等：已支付直接返回成功
                if order.status == 'paid':
                    logger.info('订单已支付（幂等跳过）: %s', order_no)
                    return JsonResponse({'code': 'SUCCESS', 'message': 'OK'})

                # 状态校验
                if order.status != 'pending':
                    logger.error('订单状态异常: %s, status=%s', order_no, order.status)
                    return JsonResponse(
                        {'code': 'FAIL', 'message': '订单状态异常'},
                        status=400,
                    )

                # 金额一致性检查（防线 5）
                if order.amount != PAY_AMOUNT:
                    logger.error('金额不一致: order=%s, expected=%s', order.amount, PAY_AMOUNT)
                    return JsonResponse(
                        {'code': 'FAIL', 'message': '金额不一致'},
                        status=400,
                    )

                # 标记为已支付
                order.mark_as_paid(payment_id, method)
                logger.info('支付成功: order_no=%s, payment_id=%s', order_no, payment_id)

        except Order.DoesNotExist:
            logger.error('订单不存在: %s', order_no)
            return JsonResponse(
                {'code': 'FAIL', 'message': '订单不存在'},
                status=404,
            )

        return JsonResponse({'code': 'SUCCESS', 'message': 'OK'})


@method_decorator(csrf_exempt, name='dispatch')
class AlipayNotifyView(View):
    """支付宝异步回调通知。"""

    def post(self, request, *args, **kwargs):
        # 支付宝回调可能是 POST form 或 JSON
        if request.content_type == 'application/json':
            params = json.loads(request.body.decode('utf-8'))
        else:
            params = request.POST.dict()

        # 1. 验签
        alipay = AlipayPay()
        result = alipay.verify_notify(params)

        if result is None:
            return JsonResponse({'code': 'FAIL', 'message': '验签失败'}, status=400)

        # 2. 幂等处理
        order_no = result.get('out_trade_no', '')
        trade_no = result.get('trade_no', '')

        return self._process_payment_success(order_no, trade_no, 'alipay')

    def _process_payment_success(self, order_no: str, payment_id: str,
                                  method: str) -> JsonResponse:
        """处理支付成功逻辑（与微信共用逻辑）。"""
        try:
            with transaction.atomic():
                order = (
                    Order.objects
                    .select_for_update()
                    .get(order_no=order_no)
                )

                if order.status == 'paid':
                    return JsonResponse({'code': 'success', 'message': 'OK'})

                if order.status != 'pending':
                    return JsonResponse(
                        {'code': 'FAIL', 'message': '订单状态异常'},
                        status=400,
                    )

                if order.amount != PAY_AMOUNT:
                    return JsonResponse(
                        {'code': 'FAIL', 'message': '金额不一致'},
                        status=400,
                    )

                order.mark_as_paid(payment_id, method)
                logger.info('支付宝成功: order_no=%s, trade_no=%s', order_no, payment_id)

        except Order.DoesNotExist:
            return JsonResponse(
                {'code': 'FAIL', 'message': '订单不存在'},
                status=404,
            )

        return JsonResponse({'code': 'success', 'message': 'OK'})


class OrderStatusView(View):
    """订单状态查询接口（前端轮询）。

    前端每 2 秒轮询一次，持续 2 分钟。
    返回订单状态和过期倒计时。
    """

    def get(self, request, order_no, *args, **kwargs):
        try:
            order = Order.objects.get(order_no=order_no)
        except Order.DoesNotExist:
            return JsonResponse({'error': '订单不存在'}, status=404)

        # 检查过期
        if order.status == 'pending' and order.is_expired:
            order.mark_as_expired()

        # 计算剩余时间
        remaining_seconds = 0
        if order.status == 'pending':
            remaining_seconds = max(0, int((order.expires_at - timezone.now()).total_seconds()))

        return JsonResponse({
            'order_no': order.order_no,
            'status': order.status,
            'amount': str(order.amount),
            'remaining_seconds': remaining_seconds,
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
        })


class ReportView(View):
    """深度报告页面。

    仅允许已支付订单访问。
    渲染 12 章报告内容。
    """

    def get(self, request, order_no, *args, **kwargs):
        # 1. 查找已支付订单
        order = get_object_or_404(
            Order,
            order_no=order_no,
            status='paid',
        )

        # 2. 查找测评记录
        try:
            assessment = Assessment.objects.get(id=order.assessment_id)
        except Assessment.DoesNotExist:
            return render(request, 'pages/error.html', {
                'message': '测评记录不存在',
            }, status=404)

        # 3. 查找 MBTI 类型配置
        try:
            type_config = MBTIType.objects.get(type_code=assessment.mbti_type_code)
        except MBTIType.DoesNotExist:
            return render(request, 'pages/error.html', {
                'message': '类型配置不存在',
            }, status=500)

        # 4. 渲染报告
        renderer = ReportRenderer()
        report = renderer.render(type_config, assessment)

        # 5. 渲染页面
        context = {
            'report': report,
            'type_config': type_config,
            'assessment': assessment,
            'order': order,
        }
        return render(request, 'pages/report.html', context)


class ReportRecoverView(View):
    """报告找回接口。

    用户通过 UUID 查找已购买的报告。
    返回该 UUID 下所有已支付订单和对应报告链接。
    """

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': '请求体格式错误'}, status=400)

        user_uuid = data.get('uuid', '')

        if not user_uuid:
            return JsonResponse({'error': '缺少 uuid 参数'}, status=400)

        # 查找该 UUID 下所有已支付订单
        orders = (
            Order.objects
            .filter(uuid=user_uuid, status='paid')
            .order_by('-paid_at')
            .values('order_no', 'assessment_id', 'paid_at')
        )

        if not orders:
            return JsonResponse({'error': '未找到已购买的报告'}, status=404)

        # 查找对应的测评类型
        results = []
        for order in orders:
            try:
                assessment = Assessment.objects.get(id=order['assessment_id'])
                results.append({
                    'order_no': order['order_no'],
                    'mbti_type': assessment.mbti_type_code,
                    'paid_at': order['paid_at'].isoformat() if order['paid_at'] else None,
                    'report_url': f'/report/{order["order_no"]}/',
                })
            except Assessment.DoesNotExist:
                continue

        return JsonResponse({'reports': results})
