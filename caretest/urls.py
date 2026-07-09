"""Root URL configuration for the caretest project.

Each application's URLconf is included at the project root (``path('')``)
so that every app owns the full path of its own routes (e.g.
``api/score/``, ``api/mbti-type/<code>/``, ``report/<order_no>/``).

The Django admin is mounted only when ``django.contrib.admin`` is
present in INSTALLED_APPS. The project's split settings
(``caretest/settings/base.py``) currently ship a minimal INSTALLED_APPS
that intentionally omits the contrib admin/auth stack, so the admin is a
no-op until those apps are re-added. This keeps the routing compatible
with both the minimal configuration and a future admin-enabled setup.
"""

from django.apps import apps
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = []

if apps.is_installed("django.contrib.admin"):
    from django.contrib import admin

    urlpatterns.append(path("admin/", admin.site.urls))

urlpatterns += [
    path("", include("apps.stats.urls")),
    path("", include("apps.assessment.urls")),
    path("", include("apps.mbti_types.urls")),
    path("", include("apps.careers.urls")),
    path("", include("apps.payment.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
