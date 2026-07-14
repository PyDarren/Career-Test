# 画己职测 — careers 路由
#
# 职业 API 路由：
#   GET /api/careers/?archetype=<id>&riasec=<code> — 职业推荐

from django.urls import path

from careers.views import CareerListView

urlpatterns: list[path] = [
    path("careers/", CareerListView.as_view(), name="career-list"),
]
