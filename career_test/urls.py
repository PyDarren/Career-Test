"""
URL routes for preview.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('assessment/guide/', views.guide, name='guide'),
    path('assessment/question/', views.question, name='question'),
    path('result/free/', views.free_result, name='free_result'),
    path('result/card/', views.card, name='card'),
    path('payment/preview/', views.preview_report, name='preview'),
    path('payment/pay/', views.pay, name='pay'),
    path('result/deep-report/', views.deep_report, name='deep_report'),
    path('account/profile/', views.profile, name='profile'),
]
