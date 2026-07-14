# 画己职测 — assessment Admin 路由
#
# 后台题库管理 Admin API 路由（挂载于 /api/admin/questions/）：
#   GET    /api/admin/questions/         — 题目列表（筛选/分页/统计）
#   POST   /api/admin/questions/         — 新增题目
#   PUT    /api/admin/questions/<id>/    — 更新题目
#   DELETE /api/admin/questions/<id>/    — 删除题目
#   GET    /api/admin/questions/export/  — 导出题目 CSV

from django.urls import path

from assessment.admin_views import (
    AdminQuestionExportView,
    AdminQuestionItemView,
    AdminQuestionListCreateView,
)

urlpatterns: list[path] = [
    path("export/", AdminQuestionExportView.as_view(), name="admin-question-export"),
    path("<int:question_id>/", AdminQuestionItemView.as_view(), name="admin-question-item"),
    path("", AdminQuestionListCreateView.as_view(), name="admin-question-list"),
]
