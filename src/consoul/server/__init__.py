"""Production server components for Consoul SDK.

This module provides production-ready middleware and utilities for building
secure FastAPI backends with Consoul SDK integration.

Middleware Components:
    - APIKeyAuth: API key authentication (header/query param)
    - RateLimiter: Token bucket rate limiting (per-key, per-IP, global)
    - configure_cors: CORS configuration helper
    - RequestValidator: Enhanced request validation with detailed errors

Configuration Models:
    - SecurityConfig: API key and authentication settings
    - RateLimitConfig: Rate limiting configuration
    - ServerConfig: Complete server configuration

Example:
    >>> from consoul.server import APIKeyAuth, RateLimiter, configure_cors
    >>> from fastapi import FastAPI, Depends
    >>>
    >>> app = FastAPI()
    >>>
    >>> # Configure CORS
    >>> configure_cors(app, allowed_origins=["https://app.example.com"])
    >>>
    >>> # Add API key authentication
    >>> auth = APIKeyAuth(api_keys=["secret-key-1", "secret-key-2"])
    >>>
    >>> # Add rate limiting
    >>> limiter = RateLimiter(
    ...     default_limits=["10 per minute"],
    ...     key_func=lambda request: request.headers.get("X-API-Key", "")
    ... )
    >>>
    >>> @app.post("/chat")
    >>> @limiter.limit("10/minute")
    >>> async def chat(api_key: str = Depends(auth.verify)):
    ...     # Your endpoint logic
    ...     pass

Security Best Practices:
    1. Store API keys in environment variables
    2. Use rate limiting per-key AND per-IP
    3. Whitelist CORS origins (no wildcards in production)
    4. Implement health endpoints that bypass authentication
    5. Use Redis for distributed rate limiting
    6. Middleware ordering: CORS → Auth → RateLimit → Validation

Installation:
    pip install consoul[server]

    This installs:
    - fastapi>=0.115.0
    - uvicorn[standard]>=0.34.0
    - slowapi>=0.1.9
    - redis>=5.2.0
"""

from consoul.server.endpoints.websocket import (
    BackpressureHandler,
    WebSocketApprovalProvider,
    WebSocketConnectionManager,
)
from consoul.server.factory import create_server
from consoul.server.middleware import (
    APIKeyAuth,
    RateLimiter,
    RequestValidator,
    configure_cors,
)
from consoul.server.models import (
    ChatErrorResponse,
    ChatRequest,
    ChatResponse,
    ChatUsage,
    RateLimitConfig,
    SecurityConfig,
    ServerConfig,
)
from consoul.server.session_locks import SessionLockManager

__all__ = [
    "APIKeyAuth",
    "BackpressureHandler",
    "ChatErrorResponse",
    "ChatRequest",
    "ChatResponse",
    "ChatUsage",
    "RateLimitConfig",
    "RateLimiter",
    "RequestValidator",
    "SecurityConfig",
    "ServerConfig",
    "SessionLockManager",
    "WebSocketApprovalProvider",
    "WebSocketConnectionManager",
    "configure_cors",
    "create_server",
]
