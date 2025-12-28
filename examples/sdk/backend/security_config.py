#!/usr/bin/env python3
"""Security Configuration Example - Production middleware setup.

Demonstrates secure configuration for production deployments:
- API key authentication
- Rate limiting with Redis
- CORS for specific origins
- Request validation
- Error handling without stack traces

Usage:
    # Set required environment variables
    export CONSOUL_API_KEYS="your-secure-api-key"
    export REDIS_URL="redis://localhost:6379"
    export CONSOUL_CORS_ORIGINS="https://app.example.com"

    # Run server
    python examples/sdk/backend/security_config.py

    # Test with API key
    curl -H "X-API-Key: your-secure-api-key" http://localhost:8000/health
"""

from consoul.server import create_server
from consoul.server.models import (
    CORSConfig,
    RateLimitConfig,
    SecurityConfig,
    ServerConfig,
    SessionConfig,
)


def create_production_config() -> ServerConfig:
    """Create production-ready server configuration.

    This demonstrates explicit configuration. In production, you would
    typically use environment variables instead.
    """
    return ServerConfig(
        app_name="Secure Consoul API",
        host="0.0.0.0",
        port=8000,
        # API key authentication
        security=SecurityConfig(
            # In production: use CONSOUL_API_KEYS env var
            api_keys=["demo-key-1", "demo-key-2"],
            header_name="X-API-Key",
            # Paths that bypass authentication
            bypass_paths=["/health", "/ready", "/docs", "/openapi.json"],
        ),
        # Rate limiting with Redis backend
        rate_limit=RateLimitConfig(
            # Multiple rate limits
            default_limits=["30 per minute", "500 per hour"],
            # Redis for distributed rate limiting
            # In production: use REDIS_URL env var
            storage_url=None,  # Uses env var REDIS_URL
            strategy="moving-window",
        ),
        # CORS for specific origins
        cors=CORSConfig(
            # In production: use CONSOUL_CORS_ORIGINS env var
            allowed_origins=["https://app.example.com", "https://admin.example.com"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "Authorization"],
            max_age=600,
        ),
        # Session storage
        session=SessionConfig(
            # Redis for distributed sessions
            # In production: use REDIS_URL env var
            redis_url=None,  # Uses env var REDIS_URL
            ttl=3600,  # 1 hour session TTL
        ),
    )


# Create app with production config
# Note: Environment variables override these defaults
app = create_server(create_production_config())


if __name__ == "__main__":
    import os

    import uvicorn

    print("=" * 60)
    print("Security Configuration Example")
    print("=" * 60)
    print()
    print("Configuration:")
    print(
        f"  API Keys: {len(os.environ.get('CONSOUL_API_KEYS', 'demo-key-1,demo-key-2').split(','))} configured"
    )
    print(f"  Redis: {os.environ.get('REDIS_URL', 'Not configured (in-memory)')}")
    print(
        f"  CORS Origins: {os.environ.get('CONSOUL_CORS_ORIGINS', 'Default (restricted)')}"
    )
    print()
    print("Test with API key:")
    print('  curl -H "X-API-Key: demo-key-1" http://localhost:8000/health')
    print()
    print("Test without API key (should fail):")
    print("  curl http://localhost:8000/chat")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
