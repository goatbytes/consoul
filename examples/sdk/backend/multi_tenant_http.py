#!/usr/bin/env python3
"""Multi-Tenant HTTP Pattern - Per-request session isolation.

Demonstrates production patterns for HTTP session management:
- Session isolation between users (no data leakage)
- Redis-backed distributed sessions
- Session locking for concurrent requests
- Safe JSON serialization (no pickle RCE)

Usage:
    # Start Redis
    docker run -p 6379:6379 redis:7-alpine

    # Set environment
    export REDIS_URL="redis://localhost:6379"

    # Run server
    python examples/sdk/backend/multi_tenant_http.py

    # Test
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"session_id": "user123", "message": "Hello!"}'
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from consoul.sdk import create_session, restore_session, save_session_state
from consoul.sdk.session_store import MemorySessionStore, RedisSessionStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Request/Response models with validation
class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=10000)
    model: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    tokens: int
    cost: float


# Session storage - choose based on environment
def create_session_store() -> MemorySessionStore | RedisSessionStore:
    """Create session store based on environment."""
    import os

    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        import redis

        logger.info(f"Using Redis session store: {redis_url}")
        client = redis.from_url(redis_url)
        return RedisSessionStore(redis_client=client, ttl=3600)
    else:
        logger.warning("No REDIS_URL set, using in-memory storage (not distributed)")
        return MemorySessionStore(ttl=3600)


session_store = create_session_store()

# Simple session locking for concurrent requests
_session_locks: dict[str, asyncio.Lock] = {}


def get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create lock for session."""
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


# FastAPI app
app = FastAPI(title="Multi-Tenant HTTP Example")


@app.get("/health")
async def health():
    return {"status": "ok", "storage": type(session_store).__name__}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint with session isolation and locking.

    Pattern:
    1. Acquire session lock (prevents race conditions)
    2. Load session state from store (or create new)
    3. Process message
    4. Save updated state back to store
    5. Release lock
    """
    lock = get_session_lock(request.session_id)

    async with lock:
        try:
            # Load existing session or create new one
            state = await asyncio.to_thread(session_store.load, request.session_id)

            if state:
                logger.info(f"Restoring session: {request.session_id}")
                console = restore_session(state)
            else:
                logger.info(f"Creating new session: {request.session_id}")
                console = create_session(
                    session_id=request.session_id,
                    model=request.model or "gpt-4o-mini",
                    tools=False,  # Chat-only for HTTP (no approval provider)
                )

            # Process message (blocking, run in thread)
            response = await asyncio.to_thread(console.chat, request.message)

            # Save updated state (JSON serialization - safe, no pickle)
            new_state = save_session_state(console)
            await asyncio.to_thread(session_store.save, request.session_id, new_state)

            # Get cost info
            cost = console.last_cost

            return ChatResponse(
                session_id=request.session_id,
                response=response,
                tokens=cost["total_tokens"],
                cost=cost["estimated_cost"],
            )

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    session_store.delete(session_id)
    _session_locks.pop(session_id, None)
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Multi-Tenant HTTP Example")
    print("=" * 60)
    print()
    print("Storage:", type(session_store).__name__)
    print()
    print("Test with:")
    print("  curl -X POST http://localhost:8000/chat \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"session_id": "user1", "message": "Hi!"}\'')
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
