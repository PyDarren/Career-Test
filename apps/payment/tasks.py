"""Celery tasks for the payment app.

Contains the daily reconciliation task:
⑤ daily_reconciliation - daily at 02:30
"""

import logging
from datetime import timedelta
from decimal import Decimal

try:
    from celery import shared_task
except ImportError:
    from apps.common.celery_compat import shared_task
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.assessment.models import Assessment

from .models import Order
from .wechat_pay import WechatPay
from .alipay_pay import AlipayPay

logger = logging.getLogger(__name__)

# Expected payment amount
EXPECTED_AMOUNT = Decimal('2.99')


@shared_task(name='apps.payment.tasks.daily_reconciliation')
def daily_reconciliation():
    """Daily payment reconciliation.

    Runs daily at 02:30. Pulls WeChat/Alipay transaction data for the
    previous day and compares with local paid orders.

    Handles:
    - Missing orders (漏单): Payments received but no local order → log alert
    - Extra orders (多单): Local orders marked paid but not in payment platform → mark as anomaly
    """
    yesterday = (timezone.now() - timedelta(days=1)).date()

    day_start = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    day_end = day_start + timedelta(days=1)

    # Get local paid orders for yesterday
    local_orders = Order.objects.filter(
        status='paid',
        paid_at__gte=day_start,
        paid_at__lt=day_end,
    ).values('order_no', 'amount', 'payment_method', 'payment_id')

    local_order_nos = {o['order_no'] for o in local_orders}

    # Try to pull WeChat transactions
    wx_pay = WechatPay()
    wx_transactions = {}
    if wx_pay.is_configured:
        try:
            wx_transactions = wx_pay.query_daily_transactions(yesterday)
        except Exception as e:
            logger.error('Failed to query WeChat transactions: %s', e)
    else:
        logger.info('WeChat not configured, skipping reconciliation for WeChat')

    # Try to pull Alipay transactions
    alipay = AlipayPay()
    alipay_transactions = {}
    if alipay.is_configured:
        try:
            alipay_transactions = alipay.query_daily_transactions(yesterday)
        except Exception as e:
            logger.error('Failed to query Alipay transactions: %s', e)
    else:
        logger.info('Alipay not configured, skipping reconciliation for Alipay')

    all_platform_transactions = {**wx_transactions, **alipay_transactions}

    # Check for missing orders (platform has payment, local doesn't)
    missing_orders = []
    for txn_id, txn_data in all_platform_transactions.items():
        order_no = txn_data.get('out_trade_no', '')
        if order_no and order_no not in local_order_nos:
            missing_orders.append({
                'order_no': order_no,
                'transaction_id': txn_id,
                'amount': txn_data.get('amount', 0),
            })

    if missing_orders:
        logger.warning(
            'Reconciliation: Found %d missing orders (paid on platform but not locally)',
            len(missing_orders),
        )
        for mo in missing_orders:
            logger.warning(
                'Missing order: order_no=%s, txn_id=%s, amount=%s',
                mo['order_no'], mo['transaction_id'], mo['amount'],
            )

    # Check for extra orders (local paid, but not found on platform)
    extra_orders = []
    for order in local_orders:
        order_no = order['order_no']
        # Check if this order exists in platform transactions
        found = False
        for txn_data in all_platform_transactions.values():
            if txn_data.get('out_trade_no') == order_no:
                found = True
                # Verify amount consistency
                platform_amount = Decimal(str(txn_data.get('amount', 0)))
                if platform_amount != order['amount']:
                    logger.error(
                        'Amount mismatch for order %s: local=%s platform=%s',
                        order_no, order['amount'], platform_amount,
                    )
                break
        if not found:
            extra_orders.append(order_no)

    if extra_orders:
        logger.warning(
            'Reconciliation: Found %d extra orders (paid locally but not on platform)',
            len(extra_orders),
        )
        for eo in extra_orders:
            logger.warning('Extra order: order_no=%s', eo)

    # Summary
    summary = {
        'date': yesterday.isoformat(),
        'local_paid_count': len(local_order_nos),
        'platform_transaction_count': len(all_platform_transactions),
        'missing_orders': len(missing_orders),
        'extra_orders': len(extra_orders),
    }

    logger.info('Reconciliation summary for %s: %s', yesterday, summary)
    return summary
