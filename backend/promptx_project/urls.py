"""
PromptX URL Configuration
"""

from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
import os


from django.shortcuts import render

def serve_frontend(request, path='index.html'):
    """Serve frontend static files, defaulting to index.html"""
    # Frontend is at ../frontend (one level up from backend/)
    frontend_dir = os.path.join(settings.BASE_DIR.parent, 'frontend')
    
    # Strip leading/trailing slashes
    clean_path = path.strip('/')
    
    # Try to serve the exact file requested (if it has an extension)
    file_path = os.path.join(frontend_dir, clean_path)
    if clean_path and os.path.isfile(file_path):
        return serve(request, clean_path, document_root=frontend_dir)
    
    # For HTML pages, use render() to process template tags like {{ user.username }}
    if not clean_path:
        return render(request, 'index.html')
    elif clean_path in ['choose', 'choose.html']:
        return render(request, 'choose.html')
    elif clean_path in ['login', 'login.html']:
        return render(request, 'login.html')
    elif clean_path in ['chat', 'chat.html']:
        return render(request, 'chat.html')
    
    # Fall back to index.html
    return render(request, 'index.html')


urlpatterns = [
    # API endpoints
    path('api/v1/', include('enhancer.urls')),
    path('api/', include('api.urls')),
    path('health', include('api.urls_health')),
    
    # Auth routes
    path('', include('social_django.urls')),
    
    # Frontend files — static assets and HTML pages
    re_path(r'^(?P<path>.+\..+)$', serve_frontend),  # Files with extensions
    re_path(r'^(?P<path>.*)$', serve_frontend),        # Everything else → index.html
]
