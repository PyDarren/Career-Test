"""Celery application configuration for the caretest project.

This module creates and configures the Celery app. It is imported by
``caretest/__init__.py`` so that the app is available whenever Django
starts.

Usage:
    # Run a worker
    celery -A caretest worker -l info

    # Run the beat scheduler
    celery -A caretest beat -l info
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caretest.settings.development')

app = Celery('caretest')

# Read configuration from Django settings, prefixed with CELERY_.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Example task that prints the request information."""
    print(f'Request: {self.request!r}')
