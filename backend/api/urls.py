"""
API URL Configuration
"""

from django.urls import path
from . import views

urlpatterns = [
    path('enhance', views.enhance_view, name='enhance'),
    path('detect-intent', views.detect_intent_view, name='detect-intent'),
    path('quality-heatmap', views.quality_heatmap_view, name='quality-heatmap'),
    path('ab-test', views.ab_test_view, name='ab-test'),
]
