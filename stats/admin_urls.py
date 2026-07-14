# 画己职测 — stats Admin 路由
#
# 后台数据看板 Admin API 路由（挂载于 /api/admin/dashboard/）：
#   GET /api/admin/dashboard/         — 看板数据
#   GET /api/admin/dashboard/export/  — 导出看板 CSV

from django.urls import path

from stats.admin_views import DashboardExportView, DashboardView

urlpatterns: list[path] = [
    path("export/", DashboardExportView.as_view(), name="admin-dashboard-export"),
    path("", DashboardView.as_view(), name="admin-dashboard"),
]
