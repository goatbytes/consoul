#!/usr/bin/env python3
"""FastAPI WebSocket Server - Proof of Concept for Consoul SDK.

Demonstrates using Consoul SDK in a web backend without TUI/CLI dependencies.
Validates that the service layer works independently and shows real-world
integration patterns for WebSocket-based AI chat.

This server provides:
- WebSocket endpoint for real-time AI chat
- Token-by-token streaming responses
- Tool execution with WebSocket-based approval
- Multi-user concurrent conversation support
- Clean separation from TUI/CLI code

Usage:
    # Install dependencies
    pip install consoul fastapi uvicorn websockets

    # Run server
    python examples/fastapi_websocket_server.py

    # Connect with test client
    python examples/fastapi_websocket_client.py

    # Or use wscat
    wscat -c ws://localhost:8000/ws/chat

Architecture:
    - FastAPI for WebSocket server
    - ConversationService for AI chat (from SDK)
    - WebSocketApprovalProvider for tool approval
    - Per-connection isolated conversation state

Message Protocol:
    Client → Server:
        {"type": "message", "content": "user message"}
        {"type": "tool_approval", "id": "call_123", "approved": true}

    Server → Client:
        {"type": "token", "content": "AI response chunk"}
        {"type": "tool_request", "id": "call_123", "name": "bash_execute", ...}
        {"type": "done"}
        {"type": "error", "message": "error details"}
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Consoul WebSocket Chat Server",
    description="AI chat server using Consoul SDK with WebSocket support",
    version="1.0.0",
)

# Add CORS middleware for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketApprovalProvider:
    """WebSocket-based approval provider for tool execution.

    Implements the ToolExecutionCallback protocol to send approval requests
    via WebSocket and wait for client responses. This allows web clients to
    approve or deny tool execution in real-time.

    Example message flow:
        1. AI wants to execute tool
        2. Server sends: {"type": "tool_request", "id": "...", "name": "...", ...}
        3. Client responds: {"type": "tool_approval", "id": "...", "approved": true}
        4. Server executes tool (if approved)
    """

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        """Initialize WebSocket approval provider.

        Args:
            websocket: Active WebSocket connection to send approval requests
            timeout: Maximum seconds to wait for approval response
        """
        self.websocket = websocket
        self.timeout = timeout
        self._pending_approvals: dict[str, asyncio.Future[bool]] = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution via WebSocket.

        Sends approval request to client and waits for response.

        Args:
            request: Tool execution request with name, args, and risk level

        Returns:
            True if client approved, False if denied or timeout
        """
        # Create future to wait for client response
        approval_future: asyncio.Future[bool] = asyncio.Future()
        self._pending_approvals[request.id] = approval_future

        # Send approval request to client
        try:
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
            logger.warning(
                f"Tool approval timeout for {request.name} (id={request.id})"
            )
            return False
        except Exception as e:
            logger.error(f"Error requesting tool approval: {e}")
            return False
        finally:
            # Clean up pending approval
            self._pending_approvals.pop(request.id, None)

    def handle_approval_response(self, tool_call_id: str, approved: bool) -> None:
        """Handle approval response from client.

        Args:
            tool_call_id: ID of the tool call being approved/denied
            approved: True if approved, False if denied
        """
        future = self._pending_approvals.get(tool_call_id)
        if future and not future.done():
            future.set_result(approved)


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "consoul-websocket-chat"}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for AI chat with tool execution support.

    Protocol:
        Client sends: {"type": "message", "content": "user message"}
        Client sends: {"type": "tool_approval", "id": "call_123", "approved": true}

        Server sends: {"type": "token", "content": "AI chunk", "cost": 0.0001}
        Server sends: {"type": "tool_request", "id": "...", "name": "...", ...}
        Server sends: {"type": "done"}
        Server sends: {"type": "error", "message": "error details"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established: {websocket.client}")

    # Import SDK components (proof that it works without TUI!)
    from consoul.sdk.services.conversation import ConversationService

    # Create conversation service for this connection
    # Each WebSocket gets isolated conversation state
    service = ConversationService.from_config()

    # Create WebSocket approval provider for tool execution
    approval_provider = WebSocketApprovalProvider(websocket)

    logger.info("ConversationService initialized successfully (headless mode)")

    # Queue for incoming user messages (prevents blocking during streaming)
    message_queue: asyncio.Queue[dict] = asyncio.Queue()

    async def receive_messages():
        """Background task: continuously receive and route incoming messages.

        This task runs concurrently with response streaming, ensuring tool
        approval messages can be processed while the AI is generating a response.
        """
        try:
            while True:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "message":
                    # Queue user messages for processing
                    await message_queue.put(data)
                elif message_type == "tool_approval":
                    # Handle tool approval immediately (non-blocking)
                    tool_call_id = data.get("id")
                    approved = data.get("approved", False)
                    logger.info(
                        f"Tool approval response: id={tool_call_id}, approved={approved}"
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
            logger.info("WebSocket disconnected in receiver task")
        except Exception as e:
            logger.error(f"Error in receiver task: {e}", exc_info=True)

    async def process_messages():
        """Main task: process queued user messages and stream responses."""
        try:
            while True:
                # Get next user message from queue
                data = await message_queue.get()
                user_message = data.get("content", "")
                logger.info(f"Processing message: {user_message[:100]}")

                try:
                    # Stream AI response token by token
                    # While streaming, the receiver task continues to handle approvals
                    async for token in service.send_message(
                        user_message, on_tool_request=approval_provider
                    ):
                        await websocket.send_json(
                            {
                                "type": "token",
                                "content": token.content,
                                "cost": token.cost,
                            }
                        )

                    # Signal completion
                    await websocket.send_json({"type": "done"})

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": str(e)})

        except Exception as e:
            logger.error(f"Error in processor task: {e}", exc_info=True)

    # Run receiver and processor concurrently
    receiver_task = asyncio.create_task(receive_messages())
    processor_task = asyncio.create_task(process_messages())

    try:
        # Wait for either task to complete (disconnect or error)
        _done, pending = await asyncio.wait(
            [receiver_task, processor_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {"type": "error", "message": f"Server error: {e}"}
            )
    finally:
        logger.info("WebSocket connection closed")


if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("Consoul FastAPI WebSocket Server")
    print("=" * 70)
    print()
    print("Starting server at: ws://localhost:8000/ws/chat")
    print("Health check at: http://localhost:8000/health")
    print()
    print("Test with:")
    print("  python examples/fastapi_websocket_client.py")
    print("  wscat -c ws://localhost:8000/ws/chat")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
