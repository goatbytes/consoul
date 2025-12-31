"""Security middleware components for FastAPI servers.

Provides production-ready middleware for authentication, rate limiting,
CORS configuration, and request validation.
"""

from consoul.server.middleware.auth import APIKeyAuth
from consoul.server.middleware.cors import configure_cors
from consoul.server.middleware.rate_limit import (
    RateLimiter,
    create_api_key_limiter,
    create_tiered_limit_func,
)
from consoul.server.middleware.request_context import (
    clear_current_request,
    get_current_request,
    set_current_request,
)
from consoul.server.middleware.validation import RequestValidator

__all__ = [
    "APIKeyAuth",
    "RateLimiter",
    "RequestValidator",
    "clear_current_request",
    "configure_cors",
    "create_api_key_limiter",
    "create_tiered_limit_func",
    "get_current_request",
    "set_current_request",
]
