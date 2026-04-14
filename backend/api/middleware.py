"""
PromptX API Key Authentication Middleware
Replaces Flask's @require_api_key decorator.
"""

import os
import json
import logging

logger = logging.getLogger(__name__)


class APIKeyMiddleware:
    """
    Middleware to enforce API key authentication on /api/ endpoints.
    Only active if CLIENT_API_KEY is set in environment.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = os.getenv('CLIENT_API_KEY')
    
    def __call__(self, request):
        # Only check API key for /api/ endpoints
        if request.path.startswith('/api/') and self.api_key:
            client_key = request.headers.get('X-Api-Key', '')
            if client_key != self.api_key:
                logger.warning(f"Unauthorized access attempt from {self._get_client_ip(request)}")
                return self._json_response(
                    {'error': 'Unauthorized: Invalid or missing API Key', 'success': False},
                    status=401
                )
        
        return self.get_response(request)
    
    def _get_client_ip(self, request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _json_response(self, data, status=200):
        from django.http import JsonResponse
        return JsonResponse(data, status=status)
