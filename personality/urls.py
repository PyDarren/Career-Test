# 画己职测 — personality 路由
#
# 人格原型 API 路由：
#   GET /api/archetypes/<int:archetype_id>/ — 获取原型配置

from django.urls import path

from personality.views import ArchetypeDetailView

urlpatterns: list[path] = [
    path(
        "archetypes/<int:archetype_id>/",
        ArchetypeDetailView.as_view(),
        name="archetype-detail",
    ),
]
