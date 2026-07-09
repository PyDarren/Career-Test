"""
Development settings for the caretest project.

Inherits all defaults from ``base.py`` and enables development-friendly
overrides such as ``DEBUG`` mode, an in-memory cache and a local SQLite
database.

Note: Redis (cache) and MySQL (database) are used in production. See
``production.py`` for the production configuration.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# A local SQLite database is used for development.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}


# Caching
# https://docs.djangoproject.com/en/5.0/topics/cache/
# In-memory cache for development. Redis is used in production.

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "caretest-dev",
    }
}
