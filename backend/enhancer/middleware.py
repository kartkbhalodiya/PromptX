"""Custom middleware for PromptX."""

import time
import logging

logger = logging.getLogger('enhancer')


class RequestLoggingMiddleware:
    """Log all API requests with timing information."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.perf_counter()

        response = self.get_response(request)

        elapsed = time.perf_counter() - start_time

        if request.path.startswith('/api/'):
            logger.info(
                f"{request.method} {request.path} "
                f"[{response.status_code}] "
                f"{elapsed:.4f}s"
            )

        return response
