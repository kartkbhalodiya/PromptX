"""
Health check URL — separate file so it can be included at /health directly.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.health_view, name='health'),
]
