"""URL configuration for the payment app.

All paths are defined relative to the project root because the root
URLconf includes this module at ``path('')``.
"""

from django.urls import path

from . import views

app_name = 'payment'

urlpatterns = [
    path('api/payment/create/', views.CreatePaymentView.as_view(), name='create'),
    path('payment/wechat/notify/', views.WechatNotifyView.as_view(), name='wechat-notify'),
    path('payment/alipay/notify/', views.AlipayNotifyView.as_view(), name='alipay-notify'),
    path('api/order/status/<str:order_no>/', views.OrderStatusView.as_view(), name='order-status'),
    path('api/report/recover/', views.ReportRecoverView.as_view(), name='report-recover'),
    path('report/<str:order_no>/', views.ReportView.as_view(), name='report'),
]
