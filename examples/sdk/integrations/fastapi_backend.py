#!/usr/bin/env python3
"""FastAPI Backend Integration Example.

Demonstrates Consoul SDK integration with FastAPI for multi-user backends.

Features:
    - HTTP chat endpoint with session persistence
    - WebSocket streaming with tool approval
    - In-memory session store (dict-based)
    - Health and readiness endpoints
    - Session cleanup pattern

Usage:
    pip install consoul[server] fastapi uvicorn
    python examples/sdk/integrations/fastapi_backend.py

    # Test HTTP endpoint:
    curl -X POST http://localhost:8000/chat \
        -H "Content-Type: application/json" \
        -d '{"session_id": "user1", "message": "Hello"}'

    # Test session deletion:
    curl -X DELETE http://localhost:8000/sessions/user1

    # WebSocket: ws://localhost:8000/ws/chat/user1

Security Notes:
    ⚠️  DEVELOPMENT CONFIGURATION - Not production-ready

    - Wildcard CORS (allows any origin)
    - No authentication
    - In-memory sessions (not distributed)

    REQUIRED for Production:
    - Specific CORS origins
    - API authentication (JWT, API keys)
    - Redis session storage (see consoul.sdk.session_store.RedisSessionStore)
    - HTTPS/TLS
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from consoul.sdk import create_session, restore_session, save_session_state

if TYPE_CHECKING:
    from consoul.sdk import Consoul
    from consoul.sdk.models import ToolRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory session store (use Redis in production)
sessions: dict[str, dict[str, Any]] = {}


class ChatRequest(BaseModel):
    """HTTP chat request."""

    session_id: str
    message: str


class ChatResponse(BaseModel):
    """HTTP chat response."""

    session_id: str
    response: str
    tokens: int
    model: str


app = FastAPI(title="Consoul Chat API", version="1.0.0")

# ⚠️ DEVELOPMENT ONLY - Replace with specific origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_or_create_session(session_id: str) -> Consoul:
    """Get existing session or create new one."""
    if session_id in sessions:
        logger.info(f"Restoring session: {session_id}")
        return restore_session(sessions[session_id])

    logger.info(f"Creating new session: {session_id}")
    return create_session(
        session_id=session_id,
        model="gpt-4o-mini",  # Cost-effective for demos
        tools=False,  # Chat-only mode (safe for backends)
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat message with session persistence."""
    console = get_or_create_session(request.session_id)

    # Run blocking LLM call in thread pool to avoid blocking event loop
    response = await asyncio.to_thread(console.chat, request.message)

    # Persist session state
    sessions[request.session_id] = save_session_state(console)

    return ChatResponse(
        session_id=request.session_id,
        response=str(response),
        tokens=console.last_cost.get("input_tokens", 0)
        + console.last_cost.get("output_tokens", 0),
        model=console.settings.get("model", "unknown"),
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


class WebSocketApprovalProvider:
    """WebSocket-based approval provider for tool execution."""

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        self.websocket = websocket
        self.timeout = timeout

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution via WebSocket."""
        await self.websocket.send_json(
            {
                "type": "tool_request",
                "id": request.id,
                "name": request.name,
                "arguments": request.arguments,
            }
        )

        try:
            data = await asyncio.wait_for(
                self.websocket.receive_json(), timeout=self.timeout
            )
            return data.get("approved", False)
        except asyncio.TimeoutError:
            return False


@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint with tool approval support."""
    await websocket.accept()
    approval_provider = WebSocketApprovalProvider(websocket)

    # Create session with tools enabled
    console = create_session(
        session_id=session_id,
        model="gpt-4o-mini",
        tools=["search", "web"],  # Read-only tools
        approval_provider=approval_provider,
    )

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Run blocking LLM call in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(console.chat, message)
            await websocket.send_json(
                {
                    "type": "response",
                    "content": str(response),
                    "tokens": console.last_cost.get("input_tokens", 0)
                    + console.last_cost.get("output_tokens", 0),
                }
            )
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
