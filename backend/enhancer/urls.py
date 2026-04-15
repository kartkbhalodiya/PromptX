"""URL configuration for PromptX enhancer app."""

from django.urls import path
from .views import (
    EnhancePromptView,
    AnalyzePromptView,
    ValidatePromptView,
    ComparePromptsView,
    BatchEnhanceView,
    FeedbackView,
    HealthCheckView,
)

app_name = 'enhancer'

urlpatterns = [
    # Core endpoints
    path('enhance/', EnhancePromptView.as_view(), name='enhance'),
    path('analyze/', AnalyzePromptView.as_view(), name='analyze'),
    path('validate/', ValidatePromptView.as_view(), name='validate'),
    path('compare/', ComparePromptsView.as_view(), name='compare'),

    # Batch & utility
    path('batch-enhance/', BatchEnhanceView.as_view(), name='batch-enhance'),
    path('feedback/', FeedbackView.as_view(), name='feedback'),
    path('health/', HealthCheckView.as_view(), name='health'),
]
