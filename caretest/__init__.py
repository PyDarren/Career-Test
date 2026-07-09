"""CareTest project package.

Importing this package also attempts to initialise the Celery app so
that ``@shared_task`` decorators and ``celery -A caretest`` commands
work when Celery is installed. The import is guarded so that Django
continues to function in environments where Celery is not available.
"""

try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    celery_app = None
    __all__ = ()
