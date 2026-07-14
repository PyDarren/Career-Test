# 画己职测 — payment 路由
#
# 支付订单 API 路由：
#   POST   /api/orders/                              — 创建订单
#   GET    /api/orders/                              — 订单列表
#   GET    /api/orders/<order_id>/                   — 订单详情
#   GET    /api/orders/<order_id>/status/            — 查询订单状态（前端轮询）
#   POST   /api/orders/coupon/                       — 优惠券验证
#   POST   /api/payment/wechat/callback/             — 微信支付回调
#   POST   /api/payment/alipay/callback/             — 支付宝回调
#   GET    /api/reports/<assessment_id>/             — 深度报告（已付费返回完整，未付费返回预览）

from django.urls import path

from payment.views import (
    AlipayCallbackView,
    CouponValidateView,
    CreateOrderView,
    DeepReportView,
    OrderDetailView,
    OrderListView,
    OrderStatusView,
    WeChatCallbackView,
)

urlpatterns: list[path] = [
    # 订单相关
    path("orders/", CreateOrderView.as_view(), name="create-order"),
    path("orders/list/", OrderListView.as_view(), name="order-list"),
    path("orders/coupon/", CouponValidateView.as_view(), name="coupon-validate"),
    path("orders/<str:order_id>/status/", OrderStatusView.as_view(), name="order-status"),
    path("orders/<str:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    # 支付回调
    path(
        "payment/wechat/callback/",
        WeChatCallbackView.as_view(),
        name="wechat-callback",
    ),
    path(
        "payment/alipay/callback/",
        AlipayCallbackView.as_view(),
        name="alipay-callback",
    ),
    # 深度报告
    path(
        "reports/<int:assessment_id>/",
        DeepReportView.as_view(),
        name="deep-report",
    ),
]
