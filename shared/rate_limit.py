"""
Rate limiting for API endpoints.
"""

import time
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status


def rate_limit(key_prefix: str, limit: int, period: int):
    """
    Rate limit decorator for API views.

    Args:
        key_prefix: Cache key prefix (e.g., 'scan')
        limit: Maximum requests allowed
        period: Time period in seconds

    Usage:
        @rate_limit('scan', limit=10, period=60)
        def post(self, request):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Get client identifier (IP address)
            ip_address = get_client_ip(request)
            cache_key = f"rate_limit:{key_prefix}:{ip_address}"

            # Get current request count
            requests = cache.get(cache_key, [])
            now = time.time()

            # Filter out old requests
            requests = [req_time for req_time in requests if now - req_time < period]

            # Check limit
            if len(requests) >= limit:
                retry_after = int(period - (now - requests[0]))
                return Response(
                    {
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            # Add current request
            requests.append(now)
            cache.set(cache_key, requests, period)

            # Call original function
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
