"""
PromptX URL Configuration
"""

from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
import os


def serve_frontend(request, path='index.html'):
    """Serve frontend static files, defaulting to index.html"""
    # Frontend is at ../frontend (one level up from backend/)
    frontend_dir = os.path.join(settings.BASE_DIR.parent, 'frontend')
    
    # Try to serve the exact file requested
    file_path = os.path.join(frontend_dir, path)
    if os.path.isfile(file_path):
        return serve(request, path, document_root=frontend_dir)
    
    # Fall back to index.html for SPA-style routing
    return serve(request, 'index.html', document_root=frontend_dir)


urlpatterns = [
    # API endpoints
    path('api/', include('api.urls')),
    path('health', include('api.urls_health')),
    
    # Frontend files — static assets and HTML pages
    re_path(r'^(?P<path>.+\..+)$', serve_frontend),  # Files with extensions
    re_path(r'^(?P<path>.*)$', serve_frontend),        # Everything else → index.html
]
