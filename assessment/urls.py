# 画己职测 — assessment 路由
#
# 测评 API 路由：
#   GET  /api/questions/                        — 获取 80 题题库
#   POST /api/assessments/                      — 提交测评答案
#   GET  /api/assessments/<session_token>/      — 查询测评结果

from django.urls import path

from assessment.views import (
    AssessmentResultView,
    AssessmentSubmitView,
    QuestionListView,
)

urlpatterns: list[path] = [
    path("questions/", QuestionListView.as_view(), name="question-list"),
    path("assessments/", AssessmentSubmitView.as_view(), name="assessment-submit"),
    path(
        "assessments/<str:session_token>/",
        AssessmentResultView.as_view(),
        name="assessment-result",
    ),
]
