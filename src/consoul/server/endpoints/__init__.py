"""Server endpoint modules."""

from consoul.server.endpoints.sse import (
    SSEAutoApprovalProvider,
    SSEConnectionManager,
    sse_format_event,
    sse_stream_generator,
)
from consoul.server.endpoints.websocket import (
    BackpressureHandler,
    WebSocketApprovalProvider,
    WebSocketConnectionManager,
    websocket_chat_handler,
)

__all__ = [
    "BackpressureHandler",
    "SSEAutoApprovalProvider",
    "SSEConnectionManager",
    "WebSocketApprovalProvider",
    "WebSocketConnectionManager",
    "sse_format_event",
    "sse_stream_generator",
    "websocket_chat_handler",
]
