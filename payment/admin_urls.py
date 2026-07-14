# 画己职测 — payment Admin 路由
#
# 后台订单管理 Admin API 路由（挂载于 /api/admin/orders/）：
#   GET /api/admin/orders/             — 订单列表（筛选/分页/统计）
#   GET /api/admin/orders/export/      — 导出订单 CSV
#   GET /api/admin/orders/<order_id>/  — 订单详情 + 操作日志

from django.urls import path

from payment.admin_views import (
    AdminOrderDetailView,
    AdminOrderExportView,
    AdminOrderListView,
)

urlpatterns: list[path] = [
    path("export/", AdminOrderExportView.as_view(), name="admin-order-export"),
    path("<str:order_id>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("", AdminOrderListView.as_view(), name="admin-order-list"),
]
