"""Celery tasks for the stats app.

Contains 4 scheduled tasks:
① expire_pending_orders - every 60 seconds
② cleanup_old_assessments - daily at 02:00
③ generate_daily_stats - daily at 03:00
④ refresh_completed_count - every hour
"""

import logging
from datetime import timedelta
from decimal import Decimal

try:
    from celery import shared_task
except ImportError:
    from apps.common.celery_compat import shared_task
from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.assessment.models import Assessment
from apps.payment.models import Order
from .models import StatsDaily, TrackingEvent

logger = logging.getLogger(__name__)


@shared_task(name='apps.stats.tasks.expire_pending_orders')
def expire_pending_orders():
    """Expire pending orders that have passed their 15-minute timeout.

    Runs every 60 seconds. Finds all orders with status='pending' and
    expires_at < now(), then marks them as 'expired'.
    """
    now = timezone.now()
    expired_count = 0

    pending_orders = Order.objects.filter(
        status='pending',
        expires_at__lt=now,
    )

    for order in pending_orders:
        try:
            with transaction.atomic():
                order.mark_as_expired()
                expired_count += 1
        except Exception as e:
            logger.error('Failed to expire order %s: %s', order.order_no, e)

    if expired_count > 0:
        logger.info('Expired %d pending orders', expired_count)

    return expired_count


@shared_task(name='apps.stats.tasks.cleanup_old_assessments')
def cleanup_old_assessments():
    """Clean up old unpaid assessment records.

    Runs daily at 02:00. Deletes assessment records older than 30 days
    that have no associated paid order.
    """
    cutoff = timezone.now() - timedelta(days=30)

    # Find assessment IDs that have paid orders
    paid_assessment_ids = Order.objects.filter(
        status='paid'
    ).values_list('assessment_id', flat=True)

    # Delete old assessments without paid orders
    deleted, _ = Assessment.objects.filter(
        created_at__lt=cutoff,
    ).exclude(
        id__in=list(paid_assessment_ids),
    ).delete()

    if deleted > 0:
        logger.info('Cleaned up %d old assessment records', deleted)

    return deleted


@shared_task(name='apps.stats.tasks.generate_daily_stats')
def generate_daily_stats():
    """Generate daily statistics from the previous day.

    Runs daily at 03:00. Aggregates UV/PV/completion/payment data from
    tracking events and writes a StatsDaily record.
    """
    yesterday = (timezone.now() - timedelta(days=1)).date()

    # Check if already generated
    if StatsDaily.objects.filter(date=yesterday).exists():
        logger.info('Daily stats for %s already exist, skipping', yesterday)
        return 0

    # Aggregate from tracking events
    day_start = timezone.make_aware(
        timezone.datetime.combine(yesterday, timezone.datetime.min.time())
    )
    day_end = day_start + timedelta(days=1)

    events = TrackingEvent.objects.filter(created_at__gte=day_start, created_at__lt=day_end)

    # Count unique UUIDs (UV)
    uv = events.values('uuid').distinct().count()

    # Count page views (PV)
    pv = events.filter(event_name='page_view').count()

    # Count assessment starts
    assessment_starts = events.filter(event_name='assessment_start').count()

    # Count assessment completions
    assessment_completes = events.filter(event_name='assessment_submit').count()

    # Count payment clicks
    payment_clicks = events.filter(event_name='payment_click').count()

    # Count payment successes
    payment_successes = events.filter(event_name='payment_success').count()

    # Count share clicks
    share_clicks = events.filter(event_name='share_click').count()

    # Count referral visits
    referral_visits = events.filter(event_name='referral_landing').count()

    # Calculate revenue from paid orders
    revenue = Order.objects.filter(
        status='paid',
        paid_at__gte=day_start,
        paid_at__lt=day_end,
    ).aggregate(
        total=Sum('amount'),
    )['total'] or Decimal('0')

    # Create stats record
    stats, created = StatsDaily.objects.update_or_create(
        date=yesterday,
        defaults={
            'uv': uv,
            'pv': pv,
            'assessment_starts': assessment_starts,
            'assessment_completes': assessment_completes,
            'payment_clicks': payment_clicks,
            'payment_successes': payment_successes,
            'revenue': revenue,
            'share_clicks': share_clicks,
            'referral_visits': referral_visits,
        },
    )

    logger.info(
        'Daily stats for %s: UV=%d PV=%d completes=%d revenue=%s',
        yesterday, uv, pv, assessment_completes, revenue,
    )

    return 1 if created else 0


@shared_task(name='apps.stats.tasks.refresh_completed_count')
def refresh_completed_count():
    """Refresh the completed count cache in Redis.

    Runs every hour. Counts total assessments and updates the Redis
    key ``stats:completed_count``.
    """
    count = Assessment.objects.count()
    cache.set('stats:completed_count', count, None)

    logger.info('Refreshed completed count: %d', count)
    return count
