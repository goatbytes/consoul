#!/usr/bin/env python3
"""FastAPI Session Management Example - Multi-user Consoul Backend.

Demonstrates best practices for using Consoul SDK in FastAPI backends with
proper session isolation, concurrent user support, and session lifecycle management.

This example shows:
- Session-scoped Consoul instances (no data leakage)
- HTTP endpoint pattern (new instance per request)
- WebSocket endpoint pattern (one instance per connection)
- Session cleanup and TTL management
- Custom approval provider integration
- Concurrent request handling

Architecture:
    - FastAPI for HTTP and WebSocket endpoints
    - create_session() factory for isolated instances
    - In-memory session storage with TTL
    - WebSocket approval provider for tool execution

Usage:
    # Install dependencies
    pip install consoul fastapi uvicorn

    # Run server
    python examples/backend/fastapi_sessions.py

    # Test HTTP endpoint
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"session_id": "user123", "message": "Hello!"}'

    # Test WebSocket (with wscat)
    wscat -c ws://localhost:8000/ws/chat/user123

Security Notes:
    - Use secure session_id (UUID, JWT subject)
    - Implement rate limiting per session
    - Use approval_provider for tool execution
    - Never expose API keys in responses
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

if TYPE_CHECKING:
    from consoul.sdk import Consoul
    from consoul.sdk.models import ToolRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Session storage with TTL tracking
# In production, use Redis or similar for distributed storage
sessions: dict[str, tuple[Consoul, float]] = {}
SESSION_TTL = 3600  # 1 hour


# Pydantic models for HTTP API
class ChatRequest(BaseModel):
    """HTTP chat request."""

    session_id: str
    message: str
    model: str | None = None
    temperature: float | None = None


class ChatResponse(BaseModel):
    """HTTP chat response."""

    session_id: str
    response: str
    tokens: int
    model: str
    cost: float


# Session management utilities
def get_or_create_session(
    session_id: str,
    model: str | None = None,
    temperature: float | None = None,
    approval_provider: Any = None,
    enable_tools: bool = False,
) -> Consoul:
    """Get existing session or create new one with TTL tracking.

    Args:
        session_id: Unique session identifier
        model: Optional model override
        temperature: Optional temperature override
        approval_provider: Optional approval provider for tools (REQUIRED if enable_tools=True)
        enable_tools: Enable tool execution (default: False, chat-only mode)

    Returns:
        Isolated Consoul instance for this session

    Note:
        If enable_tools=True, you MUST provide approval_provider to avoid blocking
        on CLI prompts. Use WebSocketApprovalProvider or similar non-interactive provider.
    """
    from consoul.sdk import create_session

    now = time.time()

    # Check if session exists and not expired
    if session_id in sessions:
        console, created_at = sessions[session_id]
        if now - created_at < SESSION_TTL:
            logger.info(f"Reusing session: {session_id}")
            return console
        # Expired - cleanup
        logger.info(f"Session expired, cleaning up: {session_id}")
        del sessions[session_id]

    # Create new session
    logger.info(f"Creating new session: {session_id}")

    # Configure tools - only enable if explicitly requested AND approval provider given
    tools_config = False  # Default: chat-only (safe for backends)
    if enable_tools:
        if approval_provider is None:
            raise ValueError(
                "approval_provider is REQUIRED when enable_tools=True. "
                "Without it, tool calls will block on CLI prompts and hang the request. "
                "Use WebSocketApprovalProvider or similar non-interactive provider."
            )
        tools_config = ["search", "web"]  # Safe read-only tools

    console = create_session(
        session_id=session_id,
        model=model or "gpt-4o-mini",  # Default to cheaper model
        tools=tools_config,  # Explicit: False (chat-only) or specific tools
        temperature=temperature or 0.7,
        approval_provider=approval_provider,
    )
    sessions[session_id] = (console, now)
    return console


def cleanup_expired_sessions() -> int:
    """Remove expired sessions from storage.

    Returns:
        Number of sessions cleaned up
    """
    now = time.time()
    expired = [
        sid
        for sid, (_, created_at) in sessions.items()
        if now - created_at >= SESSION_TTL
    ]
    for sid in expired:
        logger.info(f"Cleaning up expired session: {sid}")
        del sessions[sid]
    return len(expired)


async def periodic_cleanup():
    """Background task to periodically clean up expired sessions."""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        count = cleanup_expired_sessions()
        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")


# FastAPI lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup/shutdown tasks."""
    # Startup: Start cleanup task
    logger.info("Starting session cleanup task")
    cleanup_task = asyncio.create_task(periodic_cleanup())

    yield

    # Shutdown: Cancel cleanup task and clear sessions
    logger.info("Shutting down - canceling cleanup task")
    cleanup_task.cancel()
    from contextlib import suppress

    with suppress(asyncio.CancelledError):
        await cleanup_task
    sessions.clear()
    logger.info("All sessions cleared")


# Create FastAPI app
app = FastAPI(
    title="Consoul Multi-User Chat API",
    description="FastAPI backend with session-isolated Consoul instances",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket approval provider
class WebSocketApprovalProvider:
    """WebSocket-based approval provider for tool execution.

    Sends approval requests to client and waits for response.
    """

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        """Initialize WebSocket approval provider.

        Args:
            websocket: Active WebSocket connection
            timeout: Maximum seconds to wait for approval
        """
        self.websocket = websocket
        self.timeout = timeout
        self._pending_approvals: dict[str, asyncio.Future[bool]] = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution via WebSocket.

        Args:
            request: Tool execution request

        Returns:
            True if approved, False if denied or timeout
        """
        approval_future: asyncio.Future[bool] = asyncio.Future()
        self._pending_approvals[request.id] = approval_future

        try:
            # Send approval request to client
            await self.websocket.send_json(
                {
                    "type": "tool_request",
                    "id": request.id,
                    "name": request.name,
                    "arguments": request.arguments,
                    "risk_level": request.risk_level,
                }
            )

            # Wait for client response with timeout
            approved = await asyncio.wait_for(approval_future, timeout=self.timeout)
            return approved

        except asyncio.TimeoutError:
            logger.warning(f"Tool approval timeout for {request.name}")
            return False
        except Exception as e:
            logger.error(f"Error requesting tool approval: {e}")
            return False
        finally:
            self._pending_approvals.pop(request.id, None)

    def handle_approval_response(self, tool_call_id: str, approved: bool) -> None:
        """Handle approval response from client.

        Args:
            tool_call_id: ID of the tool call
            approved: True if approved, False if denied
        """
        future = self._pending_approvals.get(tool_call_id)
        if future and not future.done():
            future.set_result(approved)


# HTTP Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "consoul-multi-user-chat",
        "active_sessions": len(sessions),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """HTTP chat endpoint - creates new session per request.

    This pattern is suitable for stateless HTTP requests where each
    request is independent. For stateful conversations, use WebSocket.

    Args:
        request: Chat request with session_id and message

    Returns:
        Chat response with AI message and metadata
    """
    try:
        # Get or create session-scoped Consoul instance
        console = get_or_create_session(
            session_id=request.session_id,
            model=request.model,
            temperature=request.temperature,
        )

        # Send message and get response
        response = console.chat(request.message)

        # Get cost information
        cost_info = console.last_cost

        return ChatResponse(
            session_id=request.session_id,
            response=response,
            tokens=cost_info["total_tokens"],
            model=console.model_name,
            cost=cost_info["estimated_cost"],
        )

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """Clear conversation history for a session.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    if session_id in sessions:
        console, _ = sessions[session_id]
        console.clear()
        # Update timestamp to prevent expiration
        sessions[session_id] = (console, time.time())
        return {"status": "cleared", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session from storage.

    Args:
        session_id: Session identifier

    Returns:
        Success message
    """
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    else:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


# WebSocket Endpoint
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket chat endpoint - one session per connection.

    This pattern maintains a persistent connection with stateful conversation.
    The session is created when the WebSocket connects and lives for the
    connection duration.

    Protocol:
        Client sends: {"type": "message", "content": "user message"}
        Client sends: {"type": "tool_approval", "id": "call_123", "approved": true}

        Server sends: {"type": "token", "content": "AI chunk"}
        Server sends: {"type": "tool_request", "id": "...", "name": "...", ...}
        Server sends: {"type": "done"}
        Server sends: {"type": "error", "message": "error details"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established: {session_id}")

    # Create approval provider for this connection
    approval_provider = WebSocketApprovalProvider(websocket)

    # Create session-scoped Consoul instance for this connection with tools enabled
    # IMPORTANT: We pass enable_tools=True WITH approval_provider to avoid blocking
    console = get_or_create_session(
        session_id=session_id,
        approval_provider=approval_provider,
        enable_tools=True,  # Enable tools for WebSocket (approval via WebSocket)
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "message":
                # Process user message
                user_message = data.get("content", "")
                logger.info(f"[{session_id}] Processing: {user_message[:50]}")

                try:
                    # Send response (sync for now, could be async streaming)
                    response = console.chat(user_message)

                    # Send response token
                    await websocket.send_json(
                        {
                            "type": "token",
                            "content": response,
                        }
                    )

                    # Send done event with metadata
                    cost_info = console.last_cost
                    await websocket.send_json(
                        {
                            "type": "done",
                            "tokens": cost_info["total_tokens"],
                            "cost": cost_info["estimated_cost"],
                        }
                    )

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif message_type == "tool_approval":
                # Handle tool approval response
                tool_call_id = data.get("id")
                approved = data.get("approved", False)
                logger.info(
                    f"[{session_id}] Tool approval: {tool_call_id} = {approved}"
                )
                approval_provider.handle_approval_response(tool_call_id, approved)

            else:
                logger.warning(f"Unknown message type: {message_type}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        logger.info(f"WebSocket connection closed: {session_id}")


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("Consoul Multi-User FastAPI Backend")
    print("=" * 70)
    print()
    print("HTTP Endpoints:")
    print("  POST   http://localhost:8000/chat")
    print("  POST   http://localhost:8000/sessions/{session_id}/clear")
    print("  DELETE http://localhost:8000/sessions/{session_id}")
    print("  GET    http://localhost:8000/health")
    print()
    print("WebSocket Endpoint:")
    print("  ws://localhost:8000/ws/chat/{session_id}")
    print()
    print("Features:")
    print("  ✓ Session isolation (no data leakage)")
    print("  ✓ Automatic session cleanup (1 hour TTL)")
    print("  ✓ HTTP and WebSocket support")
    print("  ✓ Tool execution with approval")
    print()
    print("Test with:")
    print("  curl -X POST http://localhost:8000/chat \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"session_id": "user123", "message": "Hello!"}\'')
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
