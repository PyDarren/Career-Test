# 画己职测 — personality Admin 路由
#
# 后台内容配置 Admin API 路由（挂载于 /api/admin/content/）：
#   GET /api/admin/content/archetypes/         — 画像列表
#   PUT /api/admin/content/archetypes/<id>/    — 更新画像配置
#   GET /api/admin/content/careers/            — 职业列表
#   PUT /api/admin/content/careers/<id>/       — 更新职业配置

from django.urls import path

from personality.admin_views import (
    AdminArchetypeListView,
    AdminArchetypeUpdateView,
    AdminCareerListView,
    AdminCareerUpdateView,
)

urlpatterns: list[path] = [
    path("archetypes/", AdminArchetypeListView.as_view(), name="admin-archetype-list"),
    path("archetypes/<int:archetype_id>/", AdminArchetypeUpdateView.as_view(), name="admin-archetype-update"),
    path("careers/", AdminCareerListView.as_view(), name="admin-career-list"),
    path("careers/<int:career_id>/", AdminCareerUpdateView.as_view(), name="admin-career-update"),
]
