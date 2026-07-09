"""URL configuration for the careers app.

All paths are defined relative to the project root because the root
URLconf includes this module at ``path('')``.
"""

from django.urls import path

from . import views

app_name = 'careers'

urlpatterns = [
    path('api/careers/match/', views.CareerMatchView.as_view(), name='match'),
]
