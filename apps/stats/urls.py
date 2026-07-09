"""URL configuration for the stats app.

All paths are defined relative to the project root because the root
URLconf includes this module at ``path('')``.

Note: ``app_name`` is intentionally omitted so that URL names can be
referenced without a namespace prefix in templates (e.g. ``{% url 'home' %}``).
"""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('help/', views.HelpView.as_view(), name='help'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('report/', views.ReportView.as_view(), name='report'),
    path('api/stats/completed-count/', views.CompletedCountView.as_view(), name='completed-count'),
    path('api/feedback/', views.FeedbackView.as_view(), name='feedback'),
    path('api/customer-service/', views.CustomerServiceView.as_view(), name='customer-service'),
    path('api/track/', views.TrackView.as_view(), name='track'),
]
