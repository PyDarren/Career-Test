"""画己职测 — 开发环境配置。

品牌：画己职测
项目：career_test
说明：继承 base.py，开启 DEBUG，使用 SQLite 便于本地开发，
     Celery 任务同步执行，CORS 允许全部来源。
     缓存使用 LocMemCache，无需安装 Redis。
"""

from .base import *  # noqa: F401,F403

# 调试模式
DEBUG: bool = True

# 开发环境允许所有主机
ALLOWED_HOSTS: list[str] = ["*"]

# 开发环境使用 SQLite，无需安装 MySQL
DATABASES: dict[str, dict[str, object]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# 开发环境使用本地内存缓存，无需安装 Redis
CACHES: dict[str, dict[str, object]] = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "career-test-dev-cache",
    }
}

# 开发环境 Celery 使用同步执行
CELERY_TASK_EAGER_PROPAGATES: bool = True
CELERY_BROKER_URL: str = "memory://"
CELERY_RESULT_BACKEND: str = "cache+memory://"

# 开发环境允许所有跨域来源
CORS_ALLOW_ALL_ORIGINS: bool = True
