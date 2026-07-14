"""画己职测 — Django 基础配置（所有环境共享）。

品牌：画己职测
项目：career_test
说明：通过 django-environ 读取 .env 环境变量，包含应用、中间件、数据库、
     缓存、Celery、REST framework、CORS、安全密钥及业务常量等公共配置。
     开发环境见 dev.py，生产环境见 prod.py。
"""

from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# 路径与环境变量
# ---------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

env: environ.Env = environ.Env()
# 读取项目根目录下的 .env（文件不存在时 django-environ 会自动跳过）
environ.Env.read_env(str(BASE_DIR / ".env"))

SECRET_KEY: str = env(
    "DJANGO_SECRET_KEY",
    default="dev-insecure-secret-key-change-in-production",
)
DEBUG: bool = env.bool("DEBUG", default=False)
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# 应用
# ---------------------------------------------------------------------------
INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "django_celery_beat",
    # 业务应用
    "common",
    "assessment",
    "personality",
    "careers",
    "payment",
    "stats",
]

# ---------------------------------------------------------------------------
# 中间件
# ---------------------------------------------------------------------------
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.DeviceFingerprintMiddleware",
]

# ---------------------------------------------------------------------------
# URL 与模板
# ---------------------------------------------------------------------------
ROOT_URLCONF: str = "career_test.urls"

TEMPLATES: list[dict[str, object]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION: str = "career_test.wsgi.application"

# ---------------------------------------------------------------------------
# 数据库（MySQL - 生产默认；开发环境在 dev.py 中覆盖为 SQLite）
# ---------------------------------------------------------------------------
DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="caretest"),
        "USER": env("DB_USER", default="caretest"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
    }
}

# ---------------------------------------------------------------------------
# 密码校验
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS: list[dict[str, str]] = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# 国际化与时区
# ---------------------------------------------------------------------------
LANGUAGE_CODE: str = "zh-hans"
TIME_ZONE: str = "Asia/Shanghai"
USE_I18N: bool = True
USE_TZ: bool = True

# ---------------------------------------------------------------------------
# 静态与媒体文件
# ---------------------------------------------------------------------------
STATIC_URL: str = "static/"
# 静态文件搜索路径：templates/ 目录下的 16p-assets/ 和 assets/ 也作为静态资源提供
_STATICFILES_DIR_CANDIDATES: list[Path] = [BASE_DIR / "static", BASE_DIR / "templates"]
STATICFILES_DIRS: list[Path] = [d for d in _STATICFILES_DIR_CANDIDATES if d.is_dir()]
STATIC_ROOT: Path = BASE_DIR / "staticfiles"

MEDIA_URL: str = "media/"
MEDIA_ROOT: Path = BASE_DIR / "media"

DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# 缓存（Redis）
# ---------------------------------------------------------------------------
REDIS_URL: str = env("REDIS_URL", default="redis://127.0.0.1:6379/1")

CACHES: dict[str, dict[str, object]] = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL: str = REDIS_URL
CELERY_RESULT_BACKEND: str = REDIS_URL
CELERY_TIMEZONE: str = "Asia/Shanghai"
CELERY_ENABLE_UTC: bool = False
CELERY_BEAT_SCHEDULER: str = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# Django REST framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK: dict[str, object] = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    # 统一 JSON 响应：仅启用 JSON 渲染器
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework.authentication.SessionAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
}

# ---------------------------------------------------------------------------
# CORS（跨域，从环境变量读取白名单）
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# 安全密钥（M4 阶段生产环境必须设置真实值）
# ---------------------------------------------------------------------------
# AES-256 加密密钥：测评答案加密存储
AES_ENCRYPTION_KEY: str = env("AES_ENCRYPTION_KEY", default="change-me-to-a-32-byte-aes-key")
# HMAC-SHA256 签名密钥：订单防篡改
HMAC_SECRET_KEY: str = env("HMAC_SECRET_KEY", default="change-me-to-a-hmac-secret-key")

# ---------------------------------------------------------------------------
# 业务常量（从 common.constants 导入，保持单一数据源）
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 支付渠道配置（从环境变量读取，开发环境有默认值）
# ---------------------------------------------------------------------------
WECHAT_PAY: dict[str, str] = {
    "appid": env("WECHAT_APPID", default=""),
    "mchid": env("WECHAT_MCHID", default=""),
    "api_v3_key": env("WECHAT_API_V3_KEY", default=""),
    "notify_url": env("WECHAT_NOTIFY_URL", default=""),
    "cert_path": env("WECHAT_CERT_PATH", default=""),
}
ALIPAY: dict[str, str] = {
    "app_id": env("ALIPAY_APP_ID", default=""),
    "private_key": env("ALIPAY_PRIVATE_KEY", default=""),
    "public_key": env("ALIPAY_PUBLIC_KEY", default=""),
    "notify_url": env("ALIPAY_NOTIFY_URL", default=""),
}
# 订单签名密钥
ORDER_SIGNATURE_SECRET: str = env("ORDER_SIGNATURE_SECRET", default="career-test-order-secret-key-2026")

# ---------------------------------------------------------------------------
# Admin API 认证令牌（用于 X-Admin-Token 请求头校验）
# 生产环境必须通过环境变量设置真实值，切勿使用默认值。
# ---------------------------------------------------------------------------
ADMIN_TOKEN: str = env("ADMIN_TOKEN", default="admin_dev_token")
