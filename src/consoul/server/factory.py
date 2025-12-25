"""Server factory for creating production-ready FastAPI applications.

Provides a simple factory pattern for creating configured FastAPI servers with
all middleware components (CORS, auth, rate limiting) pre-configured.

Example - Minimal usage:
    >>> from consoul.server import create_server
    >>> app = create_server()  # Load config from environment
    >>> # Add your routes
    >>> @app.post("/chat")
    >>> async def chat(api_key: str = Depends(app.state.auth.verify)):
    ...     return {"message": "Hello!"}

Example - Custom configuration:
    >>> from consoul.server import create_server
    >>> from consoul.server.models import ServerConfig, SecurityConfig
    >>> config = ServerConfig(
    ...     security=SecurityConfig(api_keys=["key1", "key2"]),
    ...     app_name="My Custom API"
    ... )
    >>> app = create_server(config)

Example - Using rate limiter:
    >>> app = create_server()
    >>> @app.get("/status")
    >>> @app.state.limiter.limit("10/minute")
    >>> async def status():
    ...     return {"status": "ok"}

Environment Variables:
    Security:
        CONSOUL_API_KEYS: Comma-separated API keys (or JSON array)
        CONSOUL_BYPASS_PATHS: Paths that bypass auth (or JSON array)

    Rate Limiting:
        CONSOUL_DEFAULT_LIMITS: Rate limits (e.g., "10/minute;100/hour")
        CONSOUL_RATE_LIMIT_REDIS_URL: Redis URL for rate limiting
        REDIS_URL: Universal fallback

    Session Storage:
        CONSOUL_SESSION_REDIS_URL: Redis URL for session storage
        REDIS_URL: Universal fallback

    CORS:
        CONSOUL_CORS_ORIGINS: Allowed origins (comma or JSON array)
        CONSOUL_CORS_ALLOW_METHODS: Allowed HTTP methods (comma or JSON array)
        CONSOUL_CORS_ALLOW_HEADERS: Allowed HTTP headers (comma or JSON array)
        CONSOUL_CORS_ALLOW_CREDENTIALS: Allow credentials (true/false)
        CONSOUL_CORS_MAX_AGE: Preflight cache duration (seconds)

    Server:
        CONSOUL_HOST: Server host (default: 0.0.0.0)
        CONSOUL_PORT: Server port (default: 8000)

Security Notes:
    - Health/readiness endpoints bypass auth and rate limiting
    - Store API keys in environment variables, never in code
    - Use HTTPS in production
    - Configure specific CORS origins (no wildcards in production)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from importlib.metadata import version as get_version
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from consoul.server.models import ServerConfig

logger = logging.getLogger(__name__)

__all__ = ["create_server"]


async def check_redis_connection(redis_url: str) -> bool:
    """Check if Redis connection is healthy.

    Args:
        redis_url: Redis connection URL

    Returns:
        True if Redis is reachable, False otherwise
    """
    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        await client.ping()
        await client.aclose()
        return True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return False


def create_server(config: ServerConfig | None = None) -> FastAPI:
    """Create production-ready FastAPI server with Consoul middleware.

    Configures a FastAPI application with:
    - CORS middleware (configurable origins)
    - API key authentication (optional, via environment)
    - Rate limiting (per-route decorators available)
    - Health and readiness endpoints (exempt from auth/rate limits)
    - Graceful shutdown handling

    The factory stores middleware instances in app.state for route access:
    - app.state.limiter: RateLimiter for @limiter.limit() decorators
    - app.state.auth: APIKeyAuth for Depends(auth.verify) (if configured)

    Args:
        config: Server configuration (loads from environment if None)

    Returns:
        Configured FastAPI application ready for uvicorn

    Raises:
        ImportError: If required dependencies not installed (pip install consoul[server])

    Example - Basic usage:
        >>> app = create_server()
        >>> # Server configured from environment variables
        >>> # Add your routes with auth/rate limiting as needed

    Example - With custom config:
        >>> from consoul.server.models import ServerConfig, SecurityConfig
        >>> config = ServerConfig(
        ...     security=SecurityConfig(api_keys=["secret"]),
        ...     app_name="My API"
        ... )
        >>> app = create_server(config)

    Example - Add authenticated route:
        >>> from fastapi import Depends
        >>> app = create_server()
        >>> @app.post("/chat")
        >>> @app.state.limiter.limit("10/minute")
        >>> async def chat(api_key: str = Depends(app.state.auth.verify)):
        ...     return {"authenticated": True}
    """
    # Import here to avoid circular dependencies and optional dependency issues
    from consoul.server.middleware import (
        APIKeyAuth,
        RateLimiter,
        configure_cors,
    )
    from consoul.server.models import ServerConfig

    # Load configuration (default to environment if None)
    if config is None:
        config = ServerConfig()

    # Get package version dynamically
    try:
        app_version = get_version("consoul")
    except Exception:
        app_version = "unknown"
        logger.warning("Could not determine package version")

    # Create lifespan context for startup/shutdown
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan context for startup and shutdown events."""
        logger.info(f"Starting {config.app_name} v{app_version}")
        logger.info(f"Listening on {config.host}:{config.port}")

        yield

        logger.info("Shutting down gracefully...")
        # Cleanup is handled by uvicorn's shutdown timeout

    # Create FastAPI application
    app = FastAPI(
        title=config.app_name,
        version=app_version,
        description="AI-powered API built with Consoul SDK",
        lifespan=lifespan,
        docs_url=None,  # Disable docs (production best practice)
        redoc_url=None,  # Disable redoc (production best practice)
    )

    # Configure CORS middleware (must be first)
    # Note: validators ensure these are always list[str] at runtime
    configure_cors(
        app,
        allowed_origins=config.cors.allowed_origins,  # type: ignore[arg-type]
        allow_credentials=config.cors.allow_credentials,
        allow_methods=config.cors.allow_methods,  # type: ignore[arg-type]
        allow_headers=config.cors.allow_headers,  # type: ignore[arg-type]
        max_age=config.cors.max_age,
    )

    # Initialize rate limiter and store in app.state
    # Ensure default_limits is a list (pydantic validator guarantees this)
    default_limits: list[str] = (
        config.rate_limit.default_limits
        if isinstance(config.rate_limit.default_limits, list)
        else [config.rate_limit.default_limits]
    )
    limiter = RateLimiter(
        default_limits=default_limits,
        storage_url=config.rate_limit.storage_url,
        key_prefix=config.rate_limit.key_prefix,
        enabled=config.rate_limit.enabled,
    )
    limiter.init_app(app)
    app.state.limiter = limiter

    logger.info(f"Rate limiter initialized: {config.rate_limit.default_limits}")

    # Initialize API key authentication (if configured)
    auth = None
    if config.security.api_keys:
        try:
            # Ensure all lists are properly typed (pydantic validators guarantee this)
            api_keys: list[str] = (
                config.security.api_keys
                if isinstance(config.security.api_keys, list)
                else [config.security.api_keys]
            )
            bypass_paths: list[str] = (
                config.security.bypass_paths
                if isinstance(config.security.bypass_paths, list)
                else [config.security.bypass_paths]
            )
            auth = APIKeyAuth(
                api_keys=api_keys,
                header_name=config.security.header_name,
                query_name=config.security.query_name,
                bypass_paths=bypass_paths,
            )
            logger.info(
                f"API key authentication enabled ({len(config.security.api_keys)} keys)"
            )
        except ValueError as e:
            logger.error(f"Failed to initialize authentication: {e}")
            auth = None
    else:
        logger.warning(
            "API key authentication disabled - set CONSOUL_API_KEYS to enable"
        )

    app.state.auth = auth

    # Register health endpoint (exempt from auth and rate limiting)
    @app.get("/health", tags=["monitoring"])  # type: ignore[misc]
    @limiter.exempt
    async def health() -> dict[str, Any]:
        """Health check endpoint for monitoring systems.

        Returns basic service status and version. This endpoint bypasses
        authentication and rate limiting for reliable monitoring.

        Returns:
            Health check response with status and version
        """
        return {
            "status": "ok",
            "service": config.app_name,
            "version": app_version,
        }

    # Register readiness endpoint (exempt from auth and rate limiting)
    @app.get("/ready", tags=["monitoring"], response_model=None)  # type: ignore[misc]
    @limiter.exempt
    async def readiness() -> dict[str, Any] | JSONResponse:
        """Readiness check endpoint with dependency health checks.

        Checks the health of external dependencies (e.g., Redis) and returns
        503 if any are unhealthy. This endpoint bypasses authentication and
        rate limiting for reliable monitoring.

        Returns:
            Readiness response with dependency check status
        """
        checks: dict[str, bool] = {}

        # Check Redis if configured
        if config.rate_limit.storage_url:
            redis_healthy = await check_redis_connection(config.rate_limit.storage_url)
            checks["redis"] = redis_healthy

            if not redis_healthy:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "checks": checks,
                        "message": "Redis connection failed",
                    },
                )

        # Return dict - checks can contain bool or string values
        return {
            "status": "ready",
            "checks": checks or {"status": "no_dependencies"},
        }

    logger.info(f"Server factory created: {config.app_name} v{app_version}")
    logger.info("Health endpoint: GET /health (auth: bypass, rate_limit: exempt)")
    logger.info("Readiness endpoint: GET /ready (auth: bypass, rate_limit: exempt)")

    return app
