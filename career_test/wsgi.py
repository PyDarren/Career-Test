"""画己职测 — WSGI 入口配置。

品牌：画己职测
项目：career_test
说明：用于 Gunicorn/uWSGI 等同步部署入口，默认指向生产配置。
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "career_test.settings.prod")

application = get_wsgi_application()
