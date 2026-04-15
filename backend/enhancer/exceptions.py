"""Custom exceptions for PromptX."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('enhancer')


class PromptXBaseException(Exception):
    """Base exception for PromptX system."""
    def __init__(self, message: str, code: str = 'PROMPTX_ERROR', details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class PromptTooShortError(PromptXBaseException):
    def __init__(self, length: int, minimum: int):
        super().__init__(
            message=f"Prompt is too short ({length} chars). Minimum is {minimum}.",
            code='PROMPT_TOO_SHORT',
            details={'length': length, 'minimum': minimum}
        )


class PromptTooLongError(PromptXBaseException):
    def __init__(self, length: int, maximum: int):
        super().__init__(
            message=f"Prompt is too long ({length} chars). Maximum is {maximum}.",
            code='PROMPT_TOO_LONG',
            details={'length': length, 'maximum': maximum}
        )


class ValidationError(PromptXBaseException):
    def __init__(self, message: str, issues: list = None):
        super().__init__(
            message=message,
            code='VALIDATION_FAILED',
            details={'issues': issues or []}
        )


class EnhancementError(PromptXBaseException):
    def __init__(self, message: str, stage: str = 'unknown'):
        super().__init__(
            message=message,
            code='ENHANCEMENT_FAILED',
            details={'stage': stage}
        )


class QualityThresholdError(PromptXBaseException):
    def __init__(self, score: float, threshold: float):
        super().__init__(
            message=f"Enhanced prompt quality ({score:.2f}) below threshold ({threshold:.2f})",
            code='QUALITY_BELOW_THRESHOLD',
            details={'score': score, 'threshold': threshold}
        )


def custom_exception_handler(exc, context):
    """Custom DRF exception handler for PromptX."""
    response = exception_handler(exc, context)

    if response is not None:
        return response

    if isinstance(exc, PromptXBaseException):
        logger.warning(f"PromptX Exception: {exc.code} - {exc.message}")
        return Response(
            {
                'error': True,
                'code': exc.code,
                'message': exc.message,
                'details': exc.details,
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return Response(
        {
            'error': True,
            'code': 'INTERNAL_ERROR',
            'message': 'An unexpected error occurred.',
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
