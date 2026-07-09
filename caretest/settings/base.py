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
