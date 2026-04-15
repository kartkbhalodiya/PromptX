"""
PromptX API Key Authentication Middleware
"""

import os
import logging

logger = logging.getLogger(__name__)


class APIKeyMiddleware:
    """
    Middleware to enforce API key authentication on /api/ endpoints.
    Only active if CLIENT_API_KEY is set to a non-empty value in .env.
    If CLIENT_API_KEY is empty or not set, all requests pass through freely.
    """

    EXEMPT_PATHS = [
        '/api/login',
        '/api/register',
        '/api/verify-otp',
        '/api/resend-otp',
        '/api/quick-login',
        '/api/health',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Always allow auth routes and exempt API paths
        if request.path.startswith('/auth/'):
            return self.get_response(request)
        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)

        # Read key fresh each request so .env changes take effect without restart
        api_key = os.getenv('CLIENT_API_KEY', '').strip()

        # If no key is configured, skip auth entirely
        if not api_key:
            return self.get_response(request)

        # Enforce key only on /api/ routes
        if request.path.startswith('/api/'):
            client_key = request.headers.get('X-Api-Key', '').strip()
            if client_key != api_key:
                logger.warning(f"Unauthorized access from {self._get_ip(request)} on {request.path}")
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': 'Unauthorized: Invalid or missing API Key', 'success': False},
                    status=401
                )

        return self.get_response(request)

    def _get_ip(self, request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
