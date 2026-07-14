"""画己职测 — 生产环境配置。

品牌：画己职测
项目：career_test
说明：继承 base.py，关闭 DEBUG，启用 HTTPS、安全 Cookie、HSTS 等
     生产级安全策略。包含数据库连接池、日志、Sentry 集成、
     静态文件 Manifest 存储等生产级增强配置。
"""

from .base import *  # noqa: F401,F403

# 关闭调试模式
DEBUG: bool = False

# HTTPS / SSL
SECURE_SSL_REDIRECT: bool = True

# 安全 Cookie
SESSION_COOKIE_SECURE: bool = True
CSRF_COOKIE_SECURE: bool = True

# 浏览器安全响应头
SECURE_BROWSER_XSS_FILTER: bool = True
SECURE_CONTENT_TYPE_NOSNIFF: bool = True
X_FRAME_OPTIONS: str = "DENY"

# HSTS（HTTP 严格传输安全）
SECURE_HSTS_SECONDS: int = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
SECURE_HSTS_PRELOAD: bool = True

# 反向代理 SSL 识别
SECURE_PROXY_SSL_HEADER: tuple[str, str] = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# CSRF 信任来源（生产域名）
# ---------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS: list[str] = ["https://huajizhice.com"]

# Referrer 策略
SECURE_REFERRER_POLICY: str = "strict-origin-when-cross-origin"

# ---------------------------------------------------------------------------
# Session 配置（30 天）
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE: int = 30 * 24 * 3600  # 30 天
SESSION_COOKIE_HTTPONLY: bool = True
SESSION_COOKIE_SAMESITE: str = "Lax"

# ---------------------------------------------------------------------------
# 数据库（MySQL 连接池）
# ---------------------------------------------------------------------------
DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="caretest"),  # noqa: F405
        "USER": env("DB_USER", default="caretest"),  # noqa: F405
        "PASSWORD": env("DB_PASSWORD", default=""),  # noqa: F405
        "HOST": env("DB_HOST", default="127.0.0.1"),  # noqa: F405
        "PORT": env("DB_PORT", default="3306"),  # noqa: F405
        # 连接池：持久连接复用，减少 TCP 握手开销
        "CONN_MAX_AGE": 60,  # 连接复用 60 秒
        "CONN_HEALTH_CHECKS": True,  # 连接健康检查
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------------
# 邮件配置
# ---------------------------------------------------------------------------
DEFAULT_FROM_EMAIL: str = env(  # noqa: F405
    "DEFAULT_FROM_EMAIL", default="noreply@huajizhice.com"
)
EMAIL_BACKEND: str = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST: str = env("EMAIL_HOST", default="smtp.qq.com")  # noqa: F405
EMAIL_PORT: int = env.int("EMAIL_PORT", default=465)  # noqa: F405
EMAIL_HOST_USER: str = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD: str = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_SSL: bool = env.bool("EMAIL_USE_SSL", default=True)  # noqa: F405

# ---------------------------------------------------------------------------
# 静态文件 Manifest 存储（文件名加 hash，配合 CDN 缓存）
# ---------------------------------------------------------------------------
STORAGES: dict[str, dict[str, str]] = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# 日志目录（确保存在，供 RotatingFileHandler 写入）
# ---------------------------------------------------------------------------
_logs_dir = BASE_DIR / "logs"  # noqa: F405
_logs_dir.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 日志配置（文件日志 + 控制台日志，按级别分文件）
# ---------------------------------------------------------------------------
LOGGING: dict[str, object] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}:{lineno} {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        # 控制台输出（容器环境采集 stdout/stderr）
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        # DEBUG 级别文件
        "debug_file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "debug.log",  # noqa: F405
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        # INFO 级别文件
        "info_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "info.log",  # noqa: F405
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        # ERROR 级别文件
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "error.log",  # noqa: F405
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        # Sentry 错误上报（通过 Sentry SDK 自动集成，此处仅作记录）
        "sentry": {
            "level": "ERROR",
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "common": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "assessment": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "payment": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "stats": {
            "handlers": ["console", "info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "error_file"],
        "level": "INFO",
    },
}

# ---------------------------------------------------------------------------
# Sentry SDK 初始化（从环境变量读取 SENTRY_DSN，非空时初始化）
# ---------------------------------------------------------------------------
import sentry_sdk  # noqa: E402
from sentry_sdk.integrations.celery import CeleryIntegration  # noqa: E402
from sentry_sdk.integrations.django import DjangoIntegration  # noqa: E402

SENTRY_DSN: str = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )
