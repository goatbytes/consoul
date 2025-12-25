"""Correlation ID context management for request tracing.

Provides thread-safe correlation ID storage using contextvars, enabling
distributed tracing across async operations for compliance audit trails.

Correlation IDs are automatically propagated through async/await chains
and can be used to link related log events (request → tool execution → response).

Example - Auto-generate ID:
    >>> from consoul.sdk.context import set_correlation_id, get_correlation_id
    >>> correlation_id = set_correlation_id()  # Generates req-abc123def456
    >>> print(get_correlation_id())
    req-abc123def456

Example - Use existing ID (from HTTP header):
    >>> request_id = request.headers.get("X-Correlation-ID")
    >>> set_correlation_id(request_id)
    >>> # All async operations will inherit this ID

Example - Multiple concurrent requests:
    >>> async def handle_request(request_id):
    ...     set_correlation_id(request_id)
    ...     await process_message()  # Inherits correlation_id
    ...     await execute_tools()     # Inherits correlation_id
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

__all__ = ["clear_correlation_id", "get_correlation_id", "set_correlation_id"]

# Thread-safe storage for correlation ID (automatically propagated in async contexts)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID for current context (auto-generate if None).

    Correlation IDs are stored in contextvars, which automatically propagate
    through async/await chains. Each async task maintains its own ID without
    cross-contamination.

    Args:
        correlation_id: Existing correlation ID (e.g., from HTTP header),
            or None to auto-generate a new ID

    Returns:
        The correlation ID that was set (useful when auto-generating)

    Example - Auto-generate:
        >>> correlation_id = set_correlation_id()
        >>> print(correlation_id)
        req-a1b2c3d4e5f6

    Example - Use existing:
        >>> set_correlation_id("external-trace-12345")
        'external-trace-12345'
    """
    id_ = correlation_id or f"req-{uuid.uuid4().hex[:12]}"
    _correlation_id.set(id_)
    return id_


def get_correlation_id() -> str | None:
    """Get current correlation ID from context.

    Returns None if no correlation ID has been set for the current context.

    Returns:
        Current correlation ID, or None if not set

    Example:
        >>> set_correlation_id("trace-123")
        'trace-123'
        >>> get_correlation_id()
        'trace-123'

    Example - Before setting:
        >>> get_correlation_id()  # Returns None
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context.

    Useful for resetting state in long-running processes or after
    request completion in server applications.

    Example:
        >>> set_correlation_id("trace-123")
        >>> clear_correlation_id()
        >>> get_correlation_id()  # Returns None
    """
    _correlation_id.set(None)
