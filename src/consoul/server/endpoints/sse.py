"""SSE (Server-Sent Events) streaming endpoint for HTTP-only AI chat.

Provides HTTP streaming alternative to WebSocket with:
- Token-by-token streaming via ConversationService
- Auto-approved tool execution (SSE is unidirectional)
- Session management compatible with HTTP /chat and WebSocket
- Standard SSE format for browser EventSource API

Example:
    >>> # curl streaming test
    >>> # curl -N -H "Content-Type: application/json" \
    >>> #      -d '{"session_id": "test", "message": "Hello"}' \
    >>> #      http://localhost:8000/chat/stream

    >>> # Browser EventSource (note: EventSource is GET-only, use fetch for POST)
    >>> const response = await fetch('/chat/stream', {
    ...     method: 'POST',
    ...     headers: {'Content-Type': 'application/json'},
    ...     body: JSON.stringify({session_id: 'test', message: 'Hello'})
    ... });
    >>> const reader = response.body.getReader();
    >>> // Read streaming response...

SSE Event Format:
    event: token
    data: {"text": "Hello"}

    event: tool_request
    data: {"id": "call_123", "name": "search", "arguments": {...}, "risk_level": "safe"}

    event: done
    data: {"session_id": "...", "usage": {...}, "timestamp": "..."}

    event: error
    data: {"code": "INTERNAL_ERROR", "message": "..."}

Security Notes:
    - Requires API key via header/query when auth is configured
    - Sessions are isolated per session_id
    - Tools are auto-approved (configurable via tool_approval_mode in future)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator  # noqa: TC003 (used in return type)
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

from starlette.requests import Request  # noqa: TC002 (used in param type)

from consoul.server.errors import ERROR_REGISTRY, ErrorCode
from consoul.server.models import (
    ChatUsage,
    SSEDoneEvent,
    SSEErrorEvent,
    SSETokenEvent,
    SSEToolRequestEvent,
)

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest
    from consoul.sdk.session_store import SessionStore
    from consoul.server.session_locks import SessionLockManager

logger = logging.getLogger(__name__)

__all__ = [
    "SSEAutoApprovalProvider",
    "SSEConnectionManager",
    "sse_format_event",
    "sse_stream_generator",
]


class SSEConnectionManager:
    """Thread-safe SSE connection counter for /health endpoint.

    Tracks the number of active SSE connections using an async lock
    to ensure accurate counting under concurrent access.

    Attributes:
        active_count: Current number of active connections

    Example:
        >>> manager = SSEConnectionManager()
        >>> await manager.connect()
        >>> print(manager.active_count)  # 1
        >>> await manager.disconnect()
        >>> print(manager.active_count)  # 0
    """

    def __init__(self) -> None:
        """Initialize connection manager with zero connections."""
        self._count = 0
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        """Return current active connection count."""
        return self._count

    async def connect(self) -> None:
        """Increment connection count atomically."""
        async with self._lock:
            self._count += 1
            logger.debug(f"SSE connected, total: {self._count}")

    async def disconnect(self) -> None:
        """Decrement connection count atomically, never below zero."""
        async with self._lock:
            self._count = max(0, self._count - 1)
            logger.debug(f"SSE disconnected, total: {self._count}")


class SSEAutoApprovalProvider:
    """Auto-approval provider for SSE streaming (unidirectional).

    Since SSE is server-to-client only, tool approvals cannot be
    requested interactively. This provider auto-approves based on mode.

    Attributes:
        mode: Approval mode ("auto", "safe_only", "none")

    Modes:
        - "auto": Approve all tool requests
        - "safe_only": Only approve tools with risk_level="safe"
        - "none": Deny all tool requests

    Example:
        >>> provider = SSEAutoApprovalProvider(mode="auto")
        >>> approved = await provider.on_tool_request(request)
        >>> print(approved)  # True
    """

    def __init__(
        self,
        mode: Literal["auto", "safe_only", "none"] = "auto",
        send_func: Any | None = None,
    ) -> None:
        """Initialize auto-approval provider.

        Args:
            mode: Approval mode (auto, safe_only, none)
            send_func: Optional callback to notify client of tool requests
        """
        self.mode = mode
        self._send_func = send_func

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Handle tool execution request with auto-approval.

        Args:
            request: Tool execution request with name, args, and risk level

        Returns:
            True if approved, False if denied based on mode
        """
        # Send notification to client about tool request (informational only)
        if self._send_func is not None:
            try:
                event = SSEToolRequestEvent(
                    id=request.id,
                    name=request.name,
                    arguments=request.arguments,
                    risk_level=request.risk_level,
                )
                await self._send_func(
                    sse_format_event("tool_request", event.model_dump())
                )
            except Exception as e:
                logger.warning(f"Failed to send tool request notification: {e}")

        # Determine approval based on mode
        if self.mode == "none":
            logger.info(f"Tool denied (mode=none): {request.name}")
            return False

        if self.mode == "safe_only":
            approved = request.risk_level == "safe"
            logger.info(
                f"Tool {'approved' if approved else 'denied'} "
                f"(mode=safe_only, risk={request.risk_level}): {request.name}"
            )
            return approved

        # mode == "auto": approve all
        logger.info(f"Tool auto-approved: {request.name}")
        return True


def sse_format_event(event_type: str, data: dict[str, Any]) -> str:
    """Format data as SSE event string.

    Args:
        event_type: SSE event type (token, done, error, tool_request)
        data: JSON-serializable event data

    Returns:
        SSE-formatted string: "event: {type}\\ndata: {json}\\n\\n"

    Example:
        >>> sse_format_event("token", {"text": "Hello"})
        'event: token\\ndata: {"text": "Hello"}\\n\\n'
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {json_data}\n\n"


async def sse_stream_generator(
    session_id: str,
    message: str,
    model: str | None,
    store: SessionStore,
    lock_manager: SessionLockManager,
    request: Request,
    metrics: Any | None = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from ConversationService streaming.

    Handles the full streaming lifecycle including:
    - Session lock acquisition
    - Session state loading/creation
    - Token streaming via ConversationService
    - Session state persistence
    - Usage metrics recording

    Args:
        session_id: Unique session identifier
        message: User message to send to AI
        model: Optional model override (only for new sessions)
        store: Session storage backend
        lock_manager: Per-session lock manager
        request: FastAPI request for disconnect detection
        metrics: Optional metrics collector

    Yields:
        SSE-formatted event strings

    Example:
        >>> async for event in sse_stream_generator(...):
        ...     # event is SSE-formatted string like "event: token\\ndata: {...}\\n\\n"
        ...     pass
    """
    from consoul.ai.history import to_dict_message
    from consoul.sdk.services.conversation import ConversationService
    from consoul.server.session_locks import SessionLock

    # Track collected events for notifications
    collected_events: list[str] = []

    async def send_event(event: str) -> None:
        """Helper to track events for tool request notifications."""
        collected_events.append(event)

    # Initialize auto-approval provider
    approval_provider = SSEAutoApprovalProvider(
        mode="auto",
        send_func=send_event,
    )

    start_time = time.monotonic()
    total_tokens = 0
    total_cost = 0.0
    response_text = ""
    current_model = model or "unknown"

    try:
        async with SessionLock(lock_manager, session_id):
            # Load session state
            state = await asyncio.to_thread(store.load, session_id)

            # Create ConversationService with auto-approval
            # Get circuit breaker from app state (SOUL-342)
            circuit_breaker_manager = getattr(
                request.app.state, "circuit_breaker_manager", None
            )
            async with ConversationService.from_config(
                approval_provider=approval_provider,
                circuit_breaker_manager=circuit_breaker_manager,
            ) as service:
                # Override model for new sessions if specified
                if model and not state and service.config:
                    service.config.current_model = model

                # Restore messages if session exists
                if state and state.get("messages"):
                    service.conversation.restore_from_dicts(state["messages"])

                # Track current model
                if service.config:
                    current_model = service.config.current_model

                # Stream response
                async for token in service.send_message(
                    message,
                    on_tool_request=approval_provider,
                ):
                    # Check for client disconnect
                    if await request.is_disconnected():
                        logger.info(f"SSE client disconnected: {session_id}")
                        break

                    # Yield any collected events (tool requests)
                    for event in collected_events:
                        yield event
                    collected_events.clear()

                    # Yield token event
                    event_data = SSETokenEvent(text=token.content)
                    yield sse_format_event("token", event_data.model_dump())

                    response_text += token.content
                    total_tokens += 1
                    if token.cost:
                        total_cost += token.cost

                # Yield any remaining collected events
                for event in collected_events:
                    yield event
                collected_events.clear()

                # Save session state (compatible with HTTP /chat and WebSocket)
                messages = [to_dict_message(m) for m in service.conversation.messages]
                new_state = {
                    "session_id": session_id,
                    "model": current_model,
                    "temperature": 0.7,
                    "messages": messages,
                    "created_at": (
                        state.get("created_at", time.time()) if state else time.time()
                    ),
                    "updated_at": time.time(),
                    "config": {"tools_enabled": bool(service.tool_registry)},
                }
                await asyncio.to_thread(store.save, session_id, new_state)

        # Record metrics if available
        if metrics is not None:
            try:
                metrics.record_tokens(
                    input_tokens=0,  # Token count not tracked per-token
                    output_tokens=total_tokens,
                    model=current_model,
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to record metrics: {e}")

        # Send done event
        duration_ms = int((time.monotonic() - start_time) * 1000)
        usage = ChatUsage(
            input_tokens=0,  # Input tokens not tracked in streaming mode
            output_tokens=total_tokens,
            total_tokens=total_tokens,
            estimated_cost=total_cost,
        )
        done_event = SSEDoneEvent(
            session_id=session_id,
            usage=usage,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        yield sse_format_event("done", done_event.model_dump())
        logger.info(
            f"SSE stream completed: session={session_id}, "
            f"tokens={total_tokens}, duration={duration_ms}ms"
        )

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled: {session_id}")
        raise

    except Exception as e:
        # Check if this is a circuit breaker error (SOUL-342)
        from consoul.ai.exceptions import StreamingError
        from consoul.server.circuit_breaker import CircuitBreakerError, CircuitState

        error_code = ErrorCode.INTERNAL_ERROR
        retry_after: int | None = None

        if isinstance(e, StreamingError) and isinstance(
            e.__cause__, CircuitBreakerError
        ):
            cb_error: CircuitBreakerError = e.__cause__
            if cb_error.state == CircuitState.OPEN:
                error_code = ErrorCode.CIRCUIT_BREAKER_OPEN
            else:
                error_code = ErrorCode.CIRCUIT_BREAKER_HALF_OPEN
            retry_after = cb_error.retry_after
            logger.warning(
                f"SSE circuit breaker {cb_error.state.name} for {cb_error.provider}: "
                f"{session_id}"
            )
        else:
            logger.error(f"SSE streaming error: {e}", exc_info=True)

        error_meta = ERROR_REGISTRY[error_code]
        error_event = SSEErrorEvent(
            code=error_code.value,
            error=error_meta["error"],
            message=str(e),
            recoverable=error_meta["recoverable"],
            retry_after=retry_after,
        )
        yield sse_format_event("error", error_event.model_dump())
