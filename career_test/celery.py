"""画己职测 — Celery 应用与定时任务调度配置。

品牌：画己职测
项目：career_test
说明：创建 Celery 应用，从 Django settings 读取 CELERY_* 配置，
     自动发现各应用 tasks 模块，并注册定时任务（beat_schedule）。
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

# 确保 Django 配置模块可用，便于独立启动 worker/beat
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "career_test.settings.dev")

# 创建 Celery 应用
app: Celery = Celery("career_test")

# 从 Django settings 读取以 CELERY_ 为前缀的配置
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现各应用下的 tasks 模块
app.autodiscover_tasks()


# 定时任务调度表
beat_schedule: dict[str, dict[str, object]] = {
    # 订单过期检查：每 60 秒
    "order_expire": {
        "task": "stats.expire_orders",
        "schedule": timedelta(seconds=60),
    },
    # 过期数据清理：每日 02:00
    "data_cleanup": {
        "task": "stats.cleanup_expired_data",
        "schedule": crontab(hour=2, minute=0),
    },
    # 日报生成：每日 03:00
    "daily_report": {
        "task": "stats.generate_daily_report",
        "schedule": crontab(hour=3, minute=0),
    },
    # 缓存刷新：每小时整点
    "cache_refresh": {
        "task": "stats.refresh_cache",
        "schedule": crontab(minute=0),
    },
    # 支付对账：每日 02:30
    "reconciliation": {
        "task": "stats.reconcile_payments",
        "schedule": crontab(hour=2, minute=30),
    },
}

app.conf.beat_schedule = beat_schedule
