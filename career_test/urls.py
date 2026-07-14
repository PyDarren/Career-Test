"""画己职测 — 根路由配置。

品牌：画己职测
项目：career_test
说明：挂载 admin 后台、API 路由、静态前端页面路由。
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns: list[object] = [
    # Django admin 后台
    path("admin/", admin.site.urls),
    # API 路由
    path("api/", include("assessment.urls")),
    path("api/", include("personality.urls")),
    path("api/", include("careers.urls")),
    path("api/", include("stats.urls")),
    path("api/", include("payment.urls")),
    # Admin API 路由（M4 阶段，不需要认证）
    path("api/admin/dashboard/", include("stats.admin_urls")),
    path("api/admin/orders/", include("payment.admin_urls")),
    path("api/admin/questions/", include("assessment.admin_urls")),
    path("api/admin/content/", include("personality.admin_urls")),
    # 首页
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    # 静态前端页面
    path("guide/", TemplateView.as_view(template_name="guide.html"), name="guide"),
    path(
        "question/",
        TemplateView.as_view(template_name="question.html"),
        name="question",
    ),
    path(
        "result-free/",
        TemplateView.as_view(template_name="result-free.html"),
        name="result-free",
    ),
    path(
        "deep-report/",
        TemplateView.as_view(template_name="deep-report.html"),
        name="deep-report",
    ),
    path(
        "payment/",
        TemplateView.as_view(template_name="payment.html"),
        name="payment",
    ),
    path(
        "account/",
        TemplateView.as_view(template_name="account.html"),
        name="account",
    ),
    path(
        "orders/",
        TemplateView.as_view(template_name="orders.html"),
        name="orders",
    ),
    path(
        "history/",
        TemplateView.as_view(template_name="history.html"),
        name="history",
    ),
    # 管理后台前端页面
    path(
        "admin-dashboard/",
        TemplateView.as_view(template_name="admin-dashboard.html"),
        name="admin-dashboard",
    ),
    path(
        "admin-questions/",
        TemplateView.as_view(template_name="admin-questions.html"),
        name="admin-questions",
    ),
    path(
        "admin-orders/",
        TemplateView.as_view(template_name="admin-orders.html"),
        name="admin-orders",
    ),
    path(
        "admin-content/",
        TemplateView.as_view(template_name="admin-content.html"),
        name="admin-content",
    ),
]
