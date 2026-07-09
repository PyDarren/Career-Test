"""URL configuration for the assessment app.

All paths are defined relative to the project root because the root
URLconf includes this module at ``path('')``.

Note: ``app_name`` is intentionally omitted so that URL names can be
referenced without a namespace prefix in templates (e.g. ``{% url 'assessment' %}``).
"""

from django.urls import path

from . import views

urlpatterns = [
    path('assessment/', views.AssessmentView.as_view(), name='assessment'),
    path('result/', views.ResultView.as_view(), name='result'),
    path('result/<str:uuid>/', views.ResultView.as_view(), name='result_detail'),
    path('api/score/', views.ScoreView.as_view(), name='score'),
    path('api/history/<str:uuid>/', views.HistoryView.as_view(), name='history'),
]
