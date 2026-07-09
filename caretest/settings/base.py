"""
Base settings for the caretest project.

This module contains configuration shared across all environments.
Environment-specific overrides live in ``development.py`` and
``production.py``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path

try:
    from celery.schedules import crontab
except ImportError:
    crontab = None

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# caretest/settings/base.py -> settings/ -> caretest/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Security
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-$s62im37z#4w_*3t)e5)!%-f*t6&p)1qkv3av_yl!yyl4e0mf6",
)


# Application definition

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "apps.assessment",
    "apps.mbti_types",
    "apps.careers",
    "apps.payment",
    "apps.stats",
    "apps.common",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.ExceptionMiddleware",
    "apps.common.middleware.RateLimitMiddleware",
]

ROOT_URLCONF = "caretest.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "apps.common.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "caretest.wsgi.application"


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "zh-hans"

TIME_ZONE = "Asia/Shanghai"

USE_I18N = True

USE_TZ = True


# Sessions
# https://docs.djangoproject.com/en/5.0/topics/http/sessions/
# Cookie-based sessions avoid a database dependency for session storage.

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_AGE = 86400 * 90  # 90 days


# Site configuration
SITE_CONFIG = {
    "site_name": "职探",
    "product_name": "职探",
    "slogan": "八分钟，看见你的职业性格",
}


# Payment configuration
# Values are read from environment variables with safe defaults so the
# project remains runnable without a full production configuration.

WECHAT_PAY = {
    "app_id": os.environ.get("WECHAT_APP_ID", ""),
    "mch_id": os.environ.get("WECHAT_MCH_ID", ""),
    "api_key": os.environ.get("WECHAT_API_KEY", ""),
    "notify_url": os.environ.get("WECHAT_NOTIFY_URL", ""),
}

ALIPAY = {
    "app_id": os.environ.get("ALIPAY_APP_ID", ""),
    "private_key": os.environ.get("ALIPAY_PRIVATE_KEY", ""),
    "alipay_public_key": os.environ.get("ALIPAY_PUBLIC_KEY", ""),
    "notify_url": os.environ.get("ALIPAY_NOTIFY_URL", ""),
    "sandbox": os.environ.get("ALIPAY_SANDBOX", "true").lower() == "true",
}


# Celery configuration
# https://docs.celeryq.dev/en/stable/userguide/configuration.html

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://127.0.0.1:6379/2")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/3")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit per task
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit

# Beat schedule: 4 scheduled tasks + 1 reconciliation task
# crontab may be None when Celery is not installed
if crontab is not None:
    CELERY_BEAT_SCHEDULE = {
        # ① Expire pending orders every 60 seconds
        'expire-pending-orders': {
            'task': 'apps.stats.tasks.expire_pending_orders',
            'schedule': 60.0,
        },
        # ② Clean up old unpaid assessments daily at 02:00
        'cleanup-old-assessments': {
            'task': 'apps.stats.tasks.cleanup_old_assessments',
            'schedule': crontab(hour=2, minute=0),
        },
        # ③ Generate daily stats at 03:00
        'generate-daily-stats': {
            'task': 'apps.stats.tasks.generate_daily_stats',
            'schedule': crontab(hour=3, minute=0),
        },
        # ④ Refresh completed count cache every hour
        'refresh-completed-count': {
            'task': 'apps.stats.tasks.refresh_completed_count',
            'schedule': 3600.0,
        },
        # ⑤ Daily payment reconciliation at 02:30
        'daily-reconciliation': {
            'task': 'apps.payment.tasks.daily_reconciliation',
            'schedule': crontab(hour=2, minute=30),
        },
    }
else:
    CELERY_BEAT_SCHEDULE = {}
