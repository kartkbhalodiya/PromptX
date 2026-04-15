"""Helper utilities for PromptX."""

import time
import functools
import logging
from typing import Any, Callable

logger = logging.getLogger('enhancer')


def timer(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.debug(f"{func.__qualname__} executed in {elapsed:.4f}s")
        return result
    return wrapper


def safe_execute(default: Any = None):
    """Decorator to catch exceptions and return default value."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{func.__qualname__} failed: {e}")
                return default
        return wrapper
    return decorator


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))
