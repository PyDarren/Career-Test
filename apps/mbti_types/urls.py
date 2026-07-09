"""URL configuration for the mbti_types app.

All paths are defined relative to the project root because the root
URLconf includes this module at ``path('')``.
"""

from django.urls import path

from . import views

app_name = 'mbti_types'

urlpatterns = [
    path('api/mbti-type/<str:code>/', views.MBTITypeView.as_view(), name='detail'),
]
