"""WebSocket streaming endpoint for real-time AI chat.

Provides production-ready WebSocket endpoint with:
- Token-by-token streaming via ConversationService
- Bidirectional tool approval workflow
- Session management compatible with HTTP /chat
- Backpressure handling for slow clients
- API key authentication

Example:
    >>> # Client connection with authentication
    >>> ws = await websockets.connect(
    ...     "ws://localhost:8000/ws/chat/session123?api_key=secret-key"
    ... )
    >>>
    >>> # Send message
    >>> await ws.send(json.dumps({"type": "message", "content": "Hello!"}))
    >>>
    >>> # Receive streaming tokens
    >>> async for message in ws:
    ...     data = json.loads(message)
    ...     if data["type"] == "token":
    ...         print(data["data"]["text"], end="", flush=True)
    ...     elif data["type"] == "done":
    ...         break

Protocol:
    Client → Server:
        {"type": "message", "content": "user message"}
        {"type": "tool_approval", "id": "call_123", "approved": true}

    Server → Client:
        {"type": "token", "data": {"text": "..."}}
        {"type": "tool_approval_request", "data": {...}}
        {"type": "done", "data": {"usage": {...}, "timestamp": "..."}}
        {"type": "error", "data": {"message": "..."}}

Security Notes:
    - Requires API key via query parameter when auth is configured
    - Sessions are isolated per session_id
    - Backpressure prevents slow client DoS
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import WebSocket, WebSocketDisconnect

from consoul.server.errors import ERROR_REGISTRY, ErrorCode

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest

logger = logging.getLogger(__name__)

__all__ = [
    "BackpressureHandler",
    "WebSocketApprovalProvider",
    "WebSocketConnectionManager",
    "websocket_chat_handler",
]


class WebSocketConnectionManager:
    """Thread-safe WebSocket connection counter for /health endpoint.

    Tracks the number of active WebSocket connections using an async lock
    to ensure accurate counting under concurrent access.

    Attributes:
        active_count: Current number of active connections

    Example:
        >>> manager = WebSocketConnectionManager()
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
            logger.debug(f"WebSocket connected, total: {self._count}")

    async def disconnect(self) -> None:
        """Decrement connection count atomically, never below zero."""
        async with self._lock:
            self._count = max(0, self._count - 1)
            logger.debug(f"WebSocket disconnected, total: {self._count}")


class WebSocketApprovalProvider:
    """WebSocket-based approval provider for tool execution.

    Implements the ToolExecutionCallback protocol to send approval requests
    via WebSocket and wait for client responses using asyncio.Future.

    Attributes:
        send: Async function to send JSON messages to client
        timeout: Seconds to wait for approval response (default: 60)

    Example:
        >>> async def send_json(msg: dict) -> None:
        ...     await websocket.send_json(msg)
        >>>
        >>> provider = WebSocketApprovalProvider(send_json, timeout=30.0)
        >>>
        >>> # Called by ConversationService when tool needs approval
        >>> approved = await provider.on_tool_request(request)

    Security Notes:
        - Timeout prevents indefinite blocking
        - Pending approvals cleaned up on timeout/cancel
        - All pending approvals cancelled on disconnect
    """

    def __init__(
        self,
        send_func: Any,  # Callable[[dict], Awaitable[None]]
        timeout: float = 60.0,
    ) -> None:
        """Initialize approval provider.

        Args:
            send_func: Async function to send JSON messages to client
            timeout: Seconds to wait for approval response
        """
        self.send = send_func
        self.timeout = timeout
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution via WebSocket.

        Sends approval request to client and waits for response with timeout.

        Args:
            request: Tool execution request with name, args, and risk level

        Returns:
            True if client approved, False if denied, timeout, or cancelled
        """
        future: asyncio.Future[bool] = asyncio.Future()
        self._pending[request.id] = future

        try:
            # Send approval request to client
            await self.send(
                {
                    "type": "tool_approval_request",
                    "data": {
                        "id": request.id,
                        "name": request.name,
                        "arguments": request.arguments,
                        "risk_level": request.risk_level,
                    },
                }
            )

            # Wait for client response with timeout
            approved = await asyncio.wait_for(future, timeout=self.timeout)
            logger.info(
                f"Tool approval received: {request.name} ({request.id}) = {approved}"
            )
            return approved

        except asyncio.TimeoutError:
            logger.warning(
                f"Tool approval timeout: {request.name} ({request.id}) - denying"
            )
            return False
        except asyncio.CancelledError:
            logger.debug(f"Tool approval cancelled: {request.name}")
            return False
        finally:
            self._pending.pop(request.id, None)

    def handle_approval(self, tool_id: str, approved: bool) -> bool:
        """Handle approval response from client.

        Args:
            tool_id: ID of the tool call being approved/denied
            approved: True if approved, False if denied

        Returns:
            True if approval was pending and handled, False otherwise
        """
        future = self._pending.get(tool_id)
        if future and not future.done():
            future.set_result(approved)
            return True
        logger.warning(f"Received approval for unknown tool: {tool_id}")
        return False

    def cancel_all(self) -> None:
        """Cancel all pending approvals on disconnect.

        Should be called during connection cleanup to unblock
        any waiting on_tool_request calls.
        """
        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()
        logger.debug("Cancelled all pending tool approvals")


class BackpressureHandler:
    """Application-level backpressure handling for slow WebSocket clients.

    Buffers outgoing messages in an asyncio.Queue and monitors for slow clients.
    When the buffer fills or send times out, the connection is dropped.

    Attributes:
        MAX_BUFFER_SIZE: Maximum tokens to buffer (1000)
        SEND_TIMEOUT: Seconds before send timeout (5.0)

    Example:
        >>> handler = BackpressureHandler(websocket)
        >>> await handler.start()
        >>>
        >>> try:
        ...     await handler.send({"type": "token", "data": {"text": "Hi"}})
        ... except ConnectionError:
        ...     # Client too slow, connection closed
        ...     pass
        >>>
        >>> await handler.close()

    Security Notes:
        - Prevents slow client DoS by limiting buffer size
        - Disconnects clients that can't keep up
        - Uses WebSocket close code 1008 (Policy Violation)
    """

    MAX_BUFFER_SIZE = 1000
    SEND_TIMEOUT = 5.0

    def __init__(self, websocket: WebSocket) -> None:
        """Initialize backpressure handler.

        Args:
            websocket: WebSocket connection to manage
        """
        self.websocket = websocket
        self._buffer: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=self.MAX_BUFFER_SIZE
        )
        self._sender_task: asyncio.Task[None] | None = None
        self._closed = False

    async def start(self) -> None:
        """Start background sender task."""
        self._sender_task = asyncio.create_task(self._sender_loop())

    async def send(self, message: dict[str, Any]) -> None:
        """Queue message for sending.

        Args:
            message: JSON-serializable message to send

        Raises:
            ConnectionError: If connection is closed or buffer is full
        """
        if self._closed:
            raise ConnectionError("WebSocket closed")

        try:
            self._buffer.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("WebSocket buffer full - dropping connection")
            await self.close(code=1008, reason="Client too slow")
            raise ConnectionError("Client cannot keep up with message rate") from None

    async def _sender_loop(self) -> None:
        """Background task: drain buffer to WebSocket with timeout."""
        while not self._closed:
            try:
                message = await self._buffer.get()
                await asyncio.wait_for(
                    self.websocket.send_json(message),
                    timeout=self.SEND_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("WebSocket send timeout - client too slow")
                await self.close(code=1008, reason="Send timeout")
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Sender loop error: {e}")
                break

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close connection and cleanup.

        Args:
            code: WebSocket close code (default: 1000 normal closure)
            reason: Close reason string
        """
        self._closed = True

        if self._sender_task:
            self._sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._sender_task

        with contextlib.suppress(Exception):
            await self.websocket.close(code=code, reason=reason)


async def websocket_chat_handler(
    websocket: WebSocket,
    session_id: str,
    api_key: str | None = None,
) -> None:
    """WebSocket endpoint handler for streaming AI chat.

    Handles the full WebSocket lifecycle including authentication,
    message streaming, tool approval, and session persistence.

    Args:
        websocket: WebSocket connection from FastAPI
        session_id: Unique session identifier from URL path
        api_key: Optional API key from query parameter

    Protocol:
        Client → Server:
            {"type": "message", "content": "user message"}
            {"type": "tool_approval", "id": "call_123", "approved": true}

        Server → Client:
            {"type": "token", "data": {"text": "..."}}
            {"type": "tool_approval_request", "data": {...}}
            {"type": "done", "data": {"usage": {...}, "timestamp": "..."}}
            {"type": "error", "data": {"message": "..."}}

    Session Management:
        - Uses same SessionStore as HTTP /chat endpoint
        - Session state loaded at each message, saved after response
        - Conversation history preserved across reconnections

    Authentication:
        - If API keys configured, requires valid key via query param
        - Connection rejected with code 1008 if auth fails
        - No auth required if no API keys configured

    Backpressure:
        - Buffers up to 1000 tokens
        - 5-second send timeout per message
        - Disconnects slow clients with code 1008
    """
    from consoul.ai.history import to_dict_message
    from consoul.server.session_locks import SessionLock

    # Get dependencies from app.state
    store = websocket.app.state.session_store
    lock_manager = websocket.app.state.session_locks
    connection_manager = websocket.app.state.ws_connections
    auth = websocket.app.state.auth

    # Authenticate if API keys are configured
    if auth is not None and (not api_key or api_key not in auth.api_keys):
        logger.warning(f"WebSocket auth failed for session: {session_id}")
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Track connection and accept
    await connection_manager.connect()
    await websocket.accept()
    logger.info(f"WebSocket connected: session_id={session_id}")

    # Initialize backpressure handler
    backpressure = BackpressureHandler(websocket)
    await backpressure.start()

    # Initialize approval provider
    approval_provider = WebSocketApprovalProvider(
        send_func=backpressure.send,
        timeout=60.0,
    )

    # Message queue for incoming user messages
    message_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def receive_messages() -> None:
        """Receive and route incoming WebSocket messages.

        Runs concurrently with process_messages to allow tool approval
        responses while streaming is in progress.
        """
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "message":
                    content = data.get("content", "")
                    if content and len(content) <= 32768:
                        await message_queue.put(data)
                    else:
                        error_meta = ERROR_REGISTRY[ErrorCode.FIELD_VALIDATION_FAILED]
                        await backpressure.send(
                            {
                                "type": "error",
                                "data": {
                                    "code": ErrorCode.FIELD_VALIDATION_FAILED.value,
                                    "error": error_meta["error"],
                                    "message": "Invalid message content",
                                    "recoverable": error_meta["recoverable"],
                                },
                            }
                        )

                elif msg_type == "tool_approval":
                    tool_id = data.get("id", "")
                    approved = data.get("approved", False)
                    approval_provider.handle_approval(tool_id, approved)

                else:
                    error_meta = ERROR_REGISTRY[ErrorCode.INVALID_REQUEST_BODY]
                    await backpressure.send(
                        {
                            "type": "error",
                            "data": {
                                "code": ErrorCode.INVALID_REQUEST_BODY.value,
                                "error": error_meta["error"],
                                "message": f"Unknown message type: {msg_type}",
                                "recoverable": error_meta["recoverable"],
                            },
                        }
                    )

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            logger.error(f"Receiver error: {e}", exc_info=True)

    async def process_messages() -> None:
        """Process queued messages and stream responses.

        Uses ConversationService for async streaming and persists
        session state compatible with HTTP /chat endpoint.
        """
        from consoul.sdk.services.conversation import ConversationService

        try:
            while True:
                data = await message_queue.get()
                user_message = data.get("content", "")
                logger.info(f"Processing message: {user_message[:100]}")

                try:
                    # Per-session lock for atomic load→chat→save
                    async with SessionLock(lock_manager, session_id):
                        # Load session state
                        state = await asyncio.to_thread(store.load, session_id)

                        # Create ConversationService with approval provider for tools
                        # Use async context manager to ensure executor cleanup
                        # Get circuit breaker from app state (SOUL-342)
                        circuit_breaker_manager = getattr(
                            websocket.app.state, "circuit_breaker_manager", None
                        )
                        async with ConversationService.from_config(
                            approval_provider=approval_provider,
                            circuit_breaker_manager=circuit_breaker_manager,
                        ) as service:
                            # Restore messages if session exists
                            if state and state.get("messages"):
                                service.conversation.restore_from_dicts(
                                    state["messages"]
                                )

                            # Stream response
                            start_time = time.monotonic()
                            async for token in service.send_message(
                                user_message,
                                on_tool_request=approval_provider,
                            ):
                                await backpressure.send(
                                    {"type": "token", "data": {"text": token.content}}
                                )

                            # Save session state (compatible with HTTP /chat)
                            messages = [
                                to_dict_message(m)
                                for m in service.conversation.messages
                            ]
                            new_state = {
                                "session_id": session_id,
                                "model": (
                                    service.config.current_model
                                    if service.config
                                    else "unknown"
                                ),
                                "temperature": 0.7,
                                "messages": messages,
                                "created_at": (
                                    state.get("created_at", time.time())
                                    if state
                                    else time.time()
                                ),
                                "updated_at": time.time(),
                                "config": {
                                    "tools_enabled": bool(service.tool_registry)
                                },
                            }
                            await asyncio.to_thread(store.save, session_id, new_state)

                    # Send done message
                    duration_ms = int((time.monotonic() - start_time) * 1000)
                    await backpressure.send(
                        {
                            "type": "done",
                            "data": {
                                "usage": {"duration_ms": duration_ms},
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        }
                    )

                except ConnectionError:
                    # Backpressure triggered disconnect
                    break
                except Exception as e:
                    logger.error(f"Processing error: {e}", exc_info=True)
                    try:
                        error_meta = ERROR_REGISTRY[ErrorCode.INTERNAL_ERROR]
                        await backpressure.send(
                            {
                                "type": "error",
                                "data": {
                                    "code": ErrorCode.INTERNAL_ERROR.value,
                                    "error": error_meta["error"],
                                    "message": str(e),
                                    "recoverable": error_meta["recoverable"],
                                },
                            }
                        )
                    except ConnectionError:
                        break

        except Exception as e:
            logger.error(f"Processor error: {e}", exc_info=True)

    # Run receiver and processor concurrently
    receiver_task = asyncio.create_task(receive_messages())
    processor_task = asyncio.create_task(process_messages())

    try:
        _done, pending = await asyncio.wait(
            [receiver_task, processor_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        # Cleanup
        approval_provider.cancel_all()
        await backpressure.close()
        await connection_manager.disconnect()
        logger.info(f"WebSocket closed: {session_id}")
