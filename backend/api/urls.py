"""
API URL Configuration
"""

from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib.auth import login
from django.contrib.auth.models import User
from . import views
from . import auth_views

def quick_login(request):
    """Quick login for testing - creates/uses a demo user"""
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={'email': 'demo@promptx.dev'}
    )
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)
    return HttpResponseRedirect('/choose/')

urlpatterns = [
    path('enhance', views.enhance_view, name='enhance'),
    path('detect-intent', views.detect_intent_view, name='detect-intent'),
    path('quality-heatmap', views.quality_heatmap_view, name='quality-heatmap'),
    path('ab-test', views.ab_test_view, name='ab-test'),
    path('analyze-url', views.analyze_url_view, name='analyze-url'),
    path('web-search', views.web_search_view, name='web-search'),
    path('ideas', views.ideas_view, name='ideas'),
    path('quick-login/', quick_login, name='quick-login'),
    
    # Auth endpoints
    path('login/', auth_views.login_view, name='login'),
    path('register/', auth_views.register_view, name='register'),
    path('verify-otp/', auth_views.verify_otp_view, name='verify-otp'),
    path('resend-otp/', auth_views.resend_otp_view, name='resend-otp'),
]
