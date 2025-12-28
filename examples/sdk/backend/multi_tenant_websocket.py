#!/usr/bin/env python3
"""Multi-Tenant WebSocket Pattern - Per-connection session isolation.

Demonstrates WebSocket patterns for real-time chat:
- One session per WebSocket connection
- Tool execution with WebSocket-based approval
- Approval timeout handling
- Token streaming (via chat response)

Usage:
    python examples/sdk/backend/multi_tenant_websocket.py

    # Test with wscat
    wscat -c ws://localhost:8000/ws/chat/user123

    # Send message
    {"type": "message", "content": "Hello!"}
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from consoul.sdk import create_session

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketApprovalProvider:
    """WebSocket-based tool approval provider.

    Sends approval requests to client and waits for response with timeout.
    """

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        self.websocket = websocket
        self.timeout = timeout
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request tool approval via WebSocket."""
        future: asyncio.Future[bool] = asyncio.Future()
        self._pending[request.id] = future

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

            # Wait for response with timeout
            approved = await asyncio.wait_for(future, timeout=self.timeout)
            return approved

        except asyncio.TimeoutError:
            logger.warning(f"Tool approval timeout: {request.name}")
            return False
        except Exception as e:
            logger.error(f"Approval error: {e}")
            return False
        finally:
            self._pending.pop(request.id, None)

    def handle_response(self, tool_id: str, approved: bool) -> None:
        """Handle approval response from client."""
        future = self._pending.get(tool_id)
        if future and not future.done():
            future.set_result(approved)


app = FastAPI(title="Multi-Tenant WebSocket Example")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket chat with per-connection session.

    Protocol:
        Client -> Server:
            {"type": "message", "content": "user message"}
            {"type": "tool_approval", "id": "call_123", "approved": true}

        Server -> Client:
            {"type": "response", "content": "AI response"}
            {"type": "tool_request", "id": "...", "name": "...", ...}
            {"type": "done", "tokens": 150, "cost": 0.001}
            {"type": "error", "message": "error details"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")

    # Create approval provider for this connection
    approval = WebSocketApprovalProvider(websocket, timeout=60.0)

    # Create session for this connection with tools enabled
    console = create_session(
        session_id=session_id,
        model="gpt-4o-mini",
        tools=["search", "web"],  # Safe read-only tools
        approval_provider=approval,
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                content = data.get("content", "")
                logger.info(f"[{session_id}] Message: {content[:50]}...")

                try:
                    # Process message (sync, run in thread pool)
                    response = await asyncio.to_thread(console.chat, content)

                    # Send response
                    await websocket.send_json(
                        {
                            "type": "response",
                            "content": response,
                        }
                    )

                    # Send completion with metadata
                    cost = console.last_cost
                    await websocket.send_json(
                        {
                            "type": "done",
                            "tokens": cost["total_tokens"],
                            "cost": cost["estimated_cost"],
                        }
                    )

                except Exception as e:
                    logger.error(f"Chat error: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": str(e),
                        }
                    )

            elif msg_type == "tool_approval":
                # Handle tool approval response from client
                tool_id = data.get("id")
                approved = data.get("approved", False)
                logger.info(f"[{session_id}] Tool {tool_id}: {approved}")
                approval.handle_response(tool_id, approved)

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Multi-Tenant WebSocket Example")
    print("=" * 60)
    print()
    print("WebSocket endpoint:")
    print("  ws://localhost:8000/ws/chat/{session_id}")
    print()
    print("Test with wscat:")
    print("  wscat -c ws://localhost:8000/ws/chat/user123")
    print()
    print("Send message:")
    print('  {"type": "message", "content": "Hello!"}')
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
