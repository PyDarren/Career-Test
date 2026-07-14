# 画己职测 — stats 路由
#
# 埋点 API 路由：
#   POST /api/tracking-events/ — 埋点上报

from django.urls import path

from stats.views import TrackingEventView

urlpatterns: list[path] = [
    path("tracking-events/", TrackingEventView.as_view(), name="tracking-event"),
]
