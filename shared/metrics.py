"""
Application metrics and monitoring utilities.
"""

import time
import logging
from functools import wraps
from typing import Callable
from django.core.cache import cache

logger = logging.getLogger(__name__)


class Metrics:
    """Simple metrics collection."""

    CACHE_PREFIX = "metrics"

    @classmethod
    def increment(cls, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        key = f"{cls.CACHE_PREFIX}:{metric_name}"
        current = cache.get(key, 0)
        cache.set(key, current + value, timeout=86400)  # 24 hours

    @classmethod
    def get(cls, metric_name: str) -> int:
        """Get metric value."""
        key = f"{cls.CACHE_PREFIX}:{metric_name}"
        return cache.get(key, 0)

    @classmethod
    def timing(cls, metric_name: str, duration: float):
        """Record timing metric."""
        key = f"{cls.CACHE_PREFIX}:timing:{metric_name}"
        timings = cache.get(key, [])
        timings.append(duration)
        # Keep last 100 timings
        if len(timings) > 100:
            timings = timings[-100:]
        cache.set(key, timings, timeout=86400)

    @classmethod
    def get_avg_timing(cls, metric_name: str) -> float:
        """Get average timing for a metric."""
        key = f"{cls.CACHE_PREFIX}:timing:{metric_name}"
        timings = cache.get(key, [])
        if not timings:
            return 0.0
        return sum(timings) / len(timings)


def track_time(metric_name: str):
    """
    Decorator to track function execution time.

    Usage:
        @track_time('scan.execution')
        def scan_wallet(address):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                Metrics.timing(metric_name, duration)
                logger.debug(f"{metric_name}: {duration:.2f}s")

        return wrapper

    return decorator


def track_count(metric_name: str):
    """
    Decorator to count function calls.

    Usage:
        @track_count('api.scan_requests')
        def post(self, request):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            Metrics.increment(metric_name)
            return func(*args, **kwargs)

        return wrapper

    return decorator
