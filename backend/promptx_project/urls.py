"""
PromptX URL Configuration
"""

from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.shortcuts import render
import os


def serve_frontend(request, path='index.html'):
    """Serve frontend static files, defaulting to index.html"""
    frontend_dir = os.path.join(settings.BASE_DIR.parent, 'frontend')
    pages_dir = os.path.join(frontend_dir, 'pages')

    clean_path = path.strip('/')

    # Serve exact static file if it exists (css, js, images, etc.)
    file_path = os.path.join(frontend_dir, clean_path)
    if clean_path and os.path.isfile(file_path):
        return serve(request, clean_path, document_root=frontend_dir)

    # HTML pages — use render() so Django template tags work (e.g. {{ user.username }})
    page_map = {
        '':                  'index.html',
        'choose':            'choose.html',
        'choose.html':       'choose.html',
        'login':             'login.html',
        'login.html':        'login.html',
        'chat':              'chat.html',
        'chat.html':         'chat.html',
        'build':             'build.html',
        'build.html':        'build.html',
        'docs':              'docs.html',
        'docs.html':         'docs.html',
        'pricing':           'pricing.html',
        'pricing.html':      'pricing.html',
        'enterprise':        'enterprise.html',
        'enterprise.html':   'enterprise.html',
        'integrations':      'integrations.html',
        'integrations.html': 'integrations.html',
    }
    template = page_map.get(clean_path, 'index.html')
    return render(request, template)


urlpatterns = [
    # API endpoints
    path('api/', include('api.urls')),
    path('health', include('api.urls_health')),

    # Auth routes (Google OAuth etc.)
    path('', include('social_django.urls')),

    # Frontend — static assets (files with extensions) and HTML pages
    re_path(r'^(?P<path>.+\..+)$', serve_frontend),   # e.g. chat.css, bot-img.png
    re_path(r'^(?P<path>.*)$',     serve_frontend),    # everything else → index.html
]
