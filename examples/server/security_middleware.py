#!/usr/bin/env python3
"""Security Middleware Reference Example for Consoul Server.

⭐ SECURITY BEST PRACTICES REFERENCE ⭐

This example demonstrates PROPER security configuration patterns.
Unlike other examples that use development-friendly wildcards, this shows
how to configure security middleware correctly for staging and production.

Security Features Demonstrated:
- API key authentication (header + query param)
- Rate limiting (per-API-key + per-IP)
- CORS configuration (specific origins, no wildcards)
- Request validation (Pydantic models with size limits)
- Health check endpoints (bypass auth properly)
- Required environment variables (no hardcoded secrets)

Usage:
    # Install dependencies
    pip install consoul[server]

    # Set API keys (REQUIRED - no default fallback)
    export CONSOUL_API_KEYS="your-key-1,your-key-2"

    # Run server
    python examples/server/security_middleware.py

    # Test authenticated endpoint
    curl -X POST http://localhost:8000/chat \\
      -H "X-API-Key: your-key-1" \\
      -H "Content-Type: application/json" \\
      -d '{"session_id": "user123", "message": "Hello!"}'

    # Test rate limiting (>10 requests/minute)
    for i in {1..15}; do
        curl -H "X-API-Key: your-key-1" http://localhost:8000/status
    done

    # Test health endpoint (bypasses auth)
    curl http://localhost:8000/health

Configuration Notes:
    ✅ API keys REQUIRED via environment (no hardcoded fallback)
    ✅ CORS configured with specific origins (update for your domains)
    ✅ Rate limiting with multiple time windows
    ✅ Request validation with size limits
    ✅ Proper health check exemptions

    Before production deployment:
    - Update CORS origins to your production domains
    - Use HTTPS/TLS (configure via reverse proxy)
    - Enable Redis for distributed rate limiting
    - Set up monitoring and logging

    See examples/README.md#security-considerations for complete guidance.
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel, Field

# Import Consoul server middleware
from consoul.server import (
    APIKeyAuth,
    RateLimiter,
    RequestValidator,
    configure_cors,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class ChatRequest(BaseModel):
    """Chat request model."""

    session_id: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=10000)


class ChatResponse(BaseModel):
    """Chat response model."""

    session_id: str
    response: str
    api_key: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    middleware: dict[str, str]


# ==============================================================================
# Middleware Configuration
# ==============================================================================


# Load API keys from environment (REQUIRED - no hardcoded fallback)
api_keys_env = os.getenv("CONSOUL_API_KEYS")
if not api_keys_env:
    raise ValueError(
        "CONSOUL_API_KEYS environment variable is required. "
        "Never hardcode API keys in source code. "
        "Set with: export CONSOUL_API_KEYS='key1,key2'"
    )
api_keys = api_keys_env.split(",")

# Configure authentication
auth = APIKeyAuth(
    api_keys=api_keys,
    header_name="X-API-Key",
    query_name="api_key",
    bypass_paths=["/health", "/docs", "/openapi.json", "/redoc"],
)

# Configure rate limiting
# - Per-API-key: 10 requests/minute
# - Global: 100 requests/minute
limiter = RateLimiter(
    default_limits=["10 per minute", "100 per hour"],
    key_func=lambda request: request.headers.get("X-API-Key", request.client.host),
)

# Configure request validator
validator = RequestValidator(max_body_size=1024 * 100)  # 100KB


# ==============================================================================
# FastAPI Application
# ==============================================================================


app = FastAPI(
    title="Consoul Secure Chat Server",
    description="Production-ready FastAPI server with security middleware",
    version="1.0.0",
)

# Initialize rate limiter with app
limiter.init_app(app)

# ==============================================================================
# CORS Configuration - Update for Your Domains
# ==============================================================================
# This example shows CORRECT CORS patterns (specific origins, no wildcards).
# IMPORTANT: Replace example.com with your actual domains before deployment.
# ==============================================================================
configure_cors(
    app,
    allowed_origins=[
        "https://app.example.com",  # Production frontend - UPDATE THIS
        "https://staging.example.com",  # Staging frontend - UPDATE THIS
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

logger.info("Security middleware configured successfully")


# ==============================================================================
# Endpoints
# ==============================================================================


@app.get("/health", response_model=HealthResponse)
@limiter.exempt  # Health checks bypass rate limiting
async def health():
    """Health check endpoint (bypasses authentication).

    Returns:
        Health status and middleware configuration
    """
    return {
        "status": "healthy",
        "middleware": {
            "auth": "enabled",
            "rate_limit": "enabled",
            "cors": "enabled",
            "validation": "enabled",
        },
    }


@app.get("/status")
@limiter.limit("10/minute")  # Rate limit per API key
async def status(request: Request, api_key: str = Depends(auth.verify)):
    """Server status endpoint (authenticated + rate limited).

    Args:
        request: FastAPI request (required by slowapi limiter)
        api_key: Validated API key from auth middleware

    Returns:
        Server status
    """
    return {"status": "ok", "authenticated": True, "api_key": api_key[:8] + "..."}


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute;100/hour")  # Multiple rate limits
async def chat(
    request: Request,
    api_key: str = Depends(auth.verify),
) -> ChatResponse:
    """Chat endpoint with full security stack.

    Demonstrates:
    - API key authentication
    - Rate limiting (10/min + 100/hr)
    - Request validation
    - CORS

    Args:
        request: FastAPI request
        api_key: Validated API key

    Returns:
        Chat response

    Raises:
        401: Invalid/missing API key
        413: Request too large
        422: Validation error
        429: Rate limit exceeded
    """
    # Validate request body
    data = await validator.validate_json(request, ChatRequest)

    logger.info(
        f"Chat request from session={data.session_id}, key={api_key[:8]}..., "
        f"message_len={len(data.message)}"
    )

    # Mock response (integrate with Consoul SDK here)
    return ChatResponse(
        session_id=data.session_id,
        response=f"Echo: {data.message}",
        api_key=api_key[:8] + "...",
    )


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Consoul Secure Chat Server...")
    logger.info(f"API Keys configured: {len(api_keys)}")
    logger.info("Access docs at: http://localhost:8000/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
