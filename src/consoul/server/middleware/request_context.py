"""Request context management for rate limiting.

Provides thread-safe request storage using contextvars, enabling
dynamic rate limit functions to access the current request without
requiring it as a function parameter.

This module solves a compatibility issue with slowapi, which calls
callable limit providers with no arguments. By storing the request
in a ContextVar, the rate limit function can access it indirectly.

Example - In middleware:
    >>> from consoul.server.middleware.request_context import set_current_request
    >>> set_current_request(request)  # Store before rate limiting

Example - In rate limit function:
    >>> from consoul.server.middleware.request_context import get_current_request
    >>> request = get_current_request()
    >>> api_key = request.headers.get("X-API-Key") if request else None
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request

__all__ = ["clear_current_request", "get_current_request", "set_current_request"]

# Thread-safe storage for current request (automatically propagated in async contexts)
_current_request: ContextVar[Request | None] = ContextVar(
    "current_request", default=None
)


def set_current_request(request: Request) -> None:
    """Set current request for context.

    Should be called by middleware before rate limiting runs.

    Args:
        request: The current Starlette/FastAPI request object
    """
    _current_request.set(request)


def get_current_request() -> Request | None:
    """Get current request from context.

    Returns:
        Current request object, or None if not set
    """
    return _current_request.get()


def clear_current_request() -> None:
    """Clear current request from context.

    Should be called after request processing completes to prevent
    memory leaks in long-running processes.
    """
    _current_request.set(None)
