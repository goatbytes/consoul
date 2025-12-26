#!/usr/bin/env python3
"""Minimal Consoul Server Example using Factory Pattern.

Demonstrates the simplest way to create a Consoul API server using the
create_server() factory function. The factory automatically configures:

- CORS middleware for cross-origin requests
- API key authentication (if CONSOUL_API_KEYS is set)
- Rate limiting with configurable limits
- Health and readiness endpoints
- Graceful shutdown handling

This factory pattern is the recommended starting point for backend APIs.

Usage:
    # Install dependencies
    pip install consoul[server]

    # Set API keys (optional, disables auth if not set)
    export CONSOUL_API_KEYS="dev-key-1,dev-key-2"

    # Set rate limits (optional, defaults to "10 per minute")
    export CONSOUL_DEFAULT_LIMITS="10/minute;100/hour"

    # Run server
    python examples/server/basic_server.py

    # Or with uvicorn directly
    uvicorn examples.server.basic_server:app --host 0.0.0.0 --port 8000

Testing:
    # Test health endpoint (no auth required)
    curl http://localhost:8000/health

    # Test authenticated endpoint
    curl -H "X-API-Key: dev-key-1" http://localhost:8000/status

    # Test rate limiting (>10 requests/minute)
    for i in {1..15}; do
        curl -H "X-API-Key: dev-key-1" http://localhost:8000/status
    done

    # Test WebSocket chat (requires wscat: npm install -g wscat)
    # Note: WebSocket auth uses query param, not header
    wscat -c "ws://localhost:8000/ws/chat?api_key=dev-key-1"

Environment Variables:
    CONSOUL_API_KEYS: Comma-separated API keys for authentication
    CONSOUL_DEFAULT_LIMITS: Rate limits (e.g., "10/minute;100/hour")
    CONSOUL_REDIS_URL: Redis URL for distributed rate limiting (optional)
    CONSOUL_HOST: Server host (default: 0.0.0.0)
    CONSOUL_PORT: Server port (default: 8000)

Security Notes:
    ⚠️  DEVELOPMENT CONFIGURATION - Not production-ready without changes

    This example uses the factory pattern which provides good defaults, but
    you MUST configure these settings before deploying to production:

    REQUIRED for Production:
    - Set CONSOUL_API_KEYS environment variable (NEVER hardcode keys)
    - Configure specific CORS origins via CONSOUL_CORS_ORIGINS (no wildcards)
    - Enable HTTPS/TLS (configure via reverse proxy like nginx/Caddy)
    - Enable Redis for distributed rate limiting (CONSOUL_RATE_LIMIT_REDIS_URL)
    - Set appropriate rate limits for your use case
    - Monitor and log API usage

    See examples/README.md#security-considerations for complete production checklist.
"""

from __future__ import annotations

import logging

from fastapi import Depends, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# Import Consoul server factory
from consoul.server import create_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class StatusRequest(BaseModel):
    """Status request model."""

    message: str = Field(default="ping", max_length=100)


class StatusResponse(BaseModel):
    """Status response model."""

    status: str
    message: str
    authenticated: bool
    api_key_prefix: str | None = None


# ==============================================================================
# Create Server using Factory Pattern
# ==============================================================================

# Create server - loads configuration from environment variables
# The factory provides good defaults, but review Security Notes before production
app = create_server()

# The factory configures everything:
# - app.state.limiter: RateLimiter for @limiter.limit() decorators
# - app.state.auth: APIKeyAuth for Depends(auth.verify) (if CONSOUL_API_KEYS set)
# - Health/readiness endpoints at /health and /ready
# - CORS middleware configured
# - Graceful shutdown handling


# ==============================================================================
# Custom Endpoints (Add your own routes here)
# ==============================================================================


# ==============================================================================
# Authentication Dependency Pattern
# ==============================================================================
# This helper function creates a FastAPI dependency that conditionally enforces
# authentication based on whether API keys are configured via environment variables.
#
# Pattern: Depends(get_auth_dependency())
#   - get_auth_dependency() is CALLED to return the dependency function
#   - Depends() receives the dependency function (not the result of calling it)
#   - This is the CORRECT pattern for FastAPI dependency injection
#
# Behavior:
#   - If CONSOUL_API_KEYS is set → Requires valid API key (401 if missing/invalid)
#   - If CONSOUL_API_KEYS not set → Allows unauthenticated access (None returned)
#
# This pattern allows the same example to work both with and without API keys
# configured, making it suitable for development and testing.
# ==============================================================================


def get_auth_dependency():
    """Get auth dependency - raises 401 if auth is configured but key invalid.

    This function returns a dependency that:
    - Enforces authentication if app.state.auth is configured
    - Allows unauthenticated access if app.state.auth is None

    Returns:
        FastAPI dependency function that validates API keys when configured

    Usage:
        @app.get("/endpoint")
        async def endpoint(api_key: str | None = Depends(get_auth_dependency())):
            # api_key will be validated string if auth enabled, None if disabled
            ...
    """

    async def auth_dependency(request: Request):
        if app.state.auth is not None:
            # Auth is configured - enforce it
            return await app.state.auth.verify(request)
        # Auth not configured - allow unauthenticated access
        return None

    return auth_dependency


@app.get("/status", response_model=StatusResponse, tags=["api"])
@app.state.limiter.limit("10/minute")  # Rate limit: 10 requests per minute
async def get_status(
    request: Request,
    api_key: str | None = Depends(get_auth_dependency()),
) -> StatusResponse:
    """Get server status (authenticated endpoint with rate limiting).

    This endpoint demonstrates:
    - API key authentication via Depends(get_auth_dependency())
    - Rate limiting via @app.state.limiter.limit() decorator
    - Pydantic request/response models

    Authentication behavior:
    - If CONSOUL_API_KEYS is set: Requires valid API key (401 without it)
    - If CONSOUL_API_KEYS not set: Allows unauthenticated access

    Args:
        api_key: API key from auth dependency (None if auth disabled)

    Returns:
        Status response with authentication info
    """
    return StatusResponse(
        status="ok",
        message="Server is running",
        authenticated=api_key is not None,
        api_key_prefix=api_key[:8] + "..." if api_key else None,
    )


@app.post("/status", response_model=StatusResponse, tags=["api"])
@app.state.limiter.limit("5/minute")  # Stricter rate limit for POST
async def post_status(
    http_request: Request,
    request: StatusRequest,
    api_key: str | None = Depends(get_auth_dependency()),
) -> StatusResponse:
    """Post status message (authenticated endpoint with stricter rate limiting).

    Authentication behavior:
    - If CONSOUL_API_KEYS is set: Requires valid API key (401 without it)
    - If CONSOUL_API_KEYS not set: Allows unauthenticated access

    Args:
        request: Status request with message
        api_key: API key from auth dependency (None if auth disabled)

    Returns:
        Status response echoing the message
    """
    return StatusResponse(
        status="ok",
        message=f"Received: {request.message}",
        authenticated=api_key is not None,
        api_key_prefix=api_key[:8] + "..." if api_key else None,
    )


@app.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    # Note: WebSocket auth requires manual check (Depends() doesn't work)
) -> None:
    """WebSocket chat endpoint (requires API key in query params).

    Connect with: ws://localhost:8000/ws/chat?api_key=YOUR_KEY

    Protocol:
        Client → {"message": "Hello!"}
        Server → {"response": "Echo: Hello!"}

    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()

    # Manual auth check for WebSocket (Depends() doesn't work)
    if app.state.auth:
        api_key = websocket.query_params.get("api_key")
        if not api_key or api_key not in app.state.auth.api_keys:
            await websocket.send_json({"error": "Invalid or missing API key"})
            await websocket.close()
            return

    logger.info("WebSocket connection established")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Echo response
            await websocket.send_json(
                {
                    "response": f"Echo: {message}",
                    "authenticated": app.state.auth is not None,
                }
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close()


# ==============================================================================
# Server Startup
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    # Read config from app.state or environment
    from consoul.server.models import ServerConfig

    config = ServerConfig()

    auth_status = (
        "✓ Enabled"
        if config.security.api_keys
        else "✗ Disabled (allows unauthenticated access)"
    )

    print("=" * 70)
    print("Consoul Server - Factory Pattern Example")
    print("=" * 70)
    print()
    print("⚠️  DEVELOPMENT MODE - See Security Notes in module docstring")
    print()
    print("Server Configuration:")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  API Keys: {auth_status}")
    print(f"  Rate Limiting: {config.rate_limit.default_limits}")
    print(
        f"  Redis: {config.rate_limit.storage_url or '✗ Not configured (in-memory only)'}"
    )
    print()
    print("Endpoints:")
    print("  GET  /health             (public, no auth, no rate limit)")
    print("  GET  /ready              (public, no auth, no rate limit)")
    print("  GET  /status             (auth if enabled, rate limit: 10/min)")
    print("  POST /status             (auth if enabled, rate limit: 5/min)")
    print("  WS   /ws/chat            (auth via api_key param if enabled)")
    print()
    print("Documentation:")
    print("  ✗ API docs disabled (production best practice)")
    print("  Note: To enable docs, set docs_url='/docs' when creating FastAPI app")
    print()
    print("Test Commands:")
    print("  # Health check (always works)")
    print("  curl http://localhost:8000/health")
    print()
    if config.security.api_keys:
        print("  # Authenticated requests (API key required)")
        print('  curl -H "X-API-Key: dev-key-1" http://localhost:8000/status')
    else:
        print("  # Status endpoint (no auth configured)")
        print("  curl http://localhost:8000/status")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    # Run server with uvicorn
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level="info",
    )
