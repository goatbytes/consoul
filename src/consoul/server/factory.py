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

Health & Readiness Endpoints:
    Health Endpoint (GET /health):
        Returns basic service status with ISO 8601 timestamp.
        Always returns HTTP 200 when service is running.

        Response Schema:
        {
            "status": "ok",
            "service": "Consoul API",
            "version": "0.4.2",
            "timestamp": "2025-12-25T10:30:45.123456Z"
        }

    Readiness Endpoint (GET /ready):
        Returns dependency health status with ISO 8601 timestamp.
        Returns HTTP 200 when all dependencies healthy, 503 when unhealthy.

        Success Response (HTTP 200):
        {
            "status": "ready",
            "checks": {"redis": true},
            "timestamp": "2025-12-25T10:30:45.123456Z"
        }

        Error Response (HTTP 503):
        {
            "status": "not_ready",
            "checks": {"redis": false},
            "message": "Redis connection failed",
            "timestamp": "2025-12-25T10:30:45.123456Z"
        }

Security Notes:
    - Health/readiness endpoints bypass auth and rate limiting
    - Store API keys in environment variables, never in code
    - Use HTTPS in production
    - Configure specific CORS origins (no wildcards in production)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib.metadata import version as get_version
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Coroutine

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
    from consoul.server.models import (
        ChatErrorResponse,
        ChatRequest,
        ChatResponse,
        ChatUsage,
        HealthResponse,
        ReadinessErrorResponse,
        ReadinessResponse,
        ServerConfig,
    )

    # Ensure Pydantic models are fully resolved for FastAPI
    ChatRequest.model_rebuild()
    ChatResponse.model_rebuild()
    ChatErrorResponse.model_rebuild()
    ChatUsage.model_rebuild()

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

        # Initialize observability (metrics, tracing)
        from consoul.server.observability import (
            MetricsCollector,
            create_metrics_middleware,
            setup_langsmith,
            setup_opentelemetry,
            start_metrics_server,
        )

        # Start Prometheus metrics server on separate port
        if config.observability.prometheus_enabled:
            if start_metrics_server(config.observability.metrics_port):
                app.state.metrics = MetricsCollector()
                logger.info(
                    f"Prometheus metrics enabled on port {config.observability.metrics_port}"
                )
            else:
                app.state.metrics = None
                logger.warning("Prometheus metrics disabled (server failed to start)")
        else:
            app.state.metrics = None

        # Add metrics middleware AFTER app.state.metrics is set
        # This middleware records request latency, status codes, and errors
        from starlette.middleware.base import BaseHTTPMiddleware

        app.add_middleware(
            BaseHTTPMiddleware,
            dispatch=create_metrics_middleware(app.state.metrics),
        )

        # Setup OpenTelemetry tracing
        if config.observability.otel_enabled:
            setup_opentelemetry(
                service_name=config.observability.otel_service_name,
                endpoint=config.observability.otel_endpoint,
            )

        # Setup LangSmith tracing
        if config.observability.langsmith_enabled:
            app.state.langsmith_tracer = setup_langsmith()
        else:
            app.state.langsmith_tracer = None

        # Session garbage collection background task
        gc_task: asyncio.Task[None] | None = None
        session_store = getattr(app.state, "session_store", None)
        if (
            session_store is not None
            and config.session.gc_interval > 0
            and hasattr(session_store, "cleanup")
        ):
            # Check if cleanup() accepts batch_size (only RedisSessionStore does)
            import inspect

            cleanup_sig = inspect.signature(session_store.cleanup)
            accepts_batch_size = "batch_size" in cleanup_sig.parameters

            async def session_gc_loop() -> None:
                """Periodic session garbage collection.

                Runs cleanup in a thread pool to avoid blocking the event loop
                during synchronous Redis SCAN operations.
                """
                while True:
                    await asyncio.sleep(config.session.gc_interval)
                    try:
                        # Run synchronous cleanup in thread pool
                        # to avoid blocking the event loop
                        if accepts_batch_size:
                            cleaned = await asyncio.to_thread(
                                session_store.cleanup,
                                batch_size=config.session.gc_batch_size,
                            )
                        else:
                            cleaned = await asyncio.to_thread(session_store.cleanup)
                        if cleaned > 0:
                            logger.info(
                                f"Session GC: cleaned {cleaned} orphaned sessions"
                            )
                    except Exception as e:
                        logger.error(f"Session GC failed: {e}")

            gc_task = asyncio.create_task(session_gc_loop())
            app.state.gc_task = gc_task
            logger.info(
                f"Session GC enabled: interval={config.session.gc_interval}s, "
                f"batch_size={config.session.gc_batch_size}"
            )

        yield

        # Cancel GC task
        if gc_task is not None:
            gc_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await gc_task
            logger.info("Session GC task cancelled")

        logger.info("Shutting down gracefully...")

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

    # Configure body size limit middleware (after CORS, before rate limiter)
    # This protects against DoS attacks via oversized payloads
    if config.validation.enabled:
        from starlette.middleware.base import BaseHTTPMiddleware

        # Capture value to avoid closure issues with mypy
        max_body_size = config.validation.max_body_size

        async def body_size_limit_dispatch(request: Request, call_next: Any) -> Any:
            """Check request body size and reject if too large."""
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > max_body_size:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "error": "Request too large",
                                "message": f"Request body must be less than {max_body_size} bytes",
                                "limit": max_body_size,
                            },
                        )
                except ValueError:
                    pass  # Invalid Content-Length, let request proceed
            return await call_next(request)

        app.add_middleware(BaseHTTPMiddleware, dispatch=body_size_limit_dispatch)
        logger.info(f"Body size limit: {max_body_size} bytes")

    # Initialize rate limiter and store in app.state
    # Ensure default_limits is a list (pydantic validator guarantees this)
    default_limits: list[str] = (
        config.rate_limit.default_limits
        if isinstance(config.rate_limit.default_limits, list)
        else [config.rate_limit.default_limits]
    )

    # Initialize tiered rate limiting if configured (SOUL-331)
    # Must be done BEFORE creating limiter to set up per-API-key bucketing
    tiered_limit_func: Callable[[Request], str] | None = None
    rate_limit_key_func: Callable[[Request], str] | None = None

    if config.rate_limit.tier_limits and config.rate_limit.api_key_tiers:
        from slowapi.util import get_remote_address

        from consoul.server.middleware.rate_limit import create_tiered_limit_func

        # Create tiered limit function for dynamic rate limits
        tiered_limit_func = create_tiered_limit_func(
            tier_limits=config.rate_limit.tier_limits,
            api_key_tiers=config.rate_limit.api_key_tiers,
            default_limit=default_limits[0],
            header_name=config.security.header_name,
        )

        # Create per-API-key bucket function so each key has its own rate limit bucket
        # This ensures premium and basic keys don't share buckets even behind the same NAT
        header_name = config.security.header_name

        def get_api_key_or_ip(request: Request) -> str:
            """Extract API key for rate limit bucketing, fallback to IP."""
            api_key = request.headers.get(header_name)
            if api_key:
                return str(api_key)
            return str(get_remote_address(request))

        rate_limit_key_func = get_api_key_or_ip

        logger.info(
            f"Tiered rate limiting enabled: {len(config.rate_limit.tier_limits)} tiers, "
            f"{len(config.rate_limit.api_key_tiers)} patterns (per-API-key buckets)"
        )

    # Create limiter with appropriate key function
    # - With tiers: bucket by API key (each key has its own bucket)
    # - Without tiers: bucket by IP address (default behavior)
    limiter = RateLimiter(
        default_limits=default_limits,
        key_func=rate_limit_key_func,  # None = default IP-based bucketing
        storage_url=config.rate_limit.storage_url,
        key_prefix=config.rate_limit.key_prefix,
        enabled=config.rate_limit.enabled,
    )
    limiter.init_app(app)
    app.state.limiter = limiter
    app.state.tiered_limit_func = tiered_limit_func

    # Create chat rate limit function (uses tiered limits if configured)
    def get_chat_rate_limit(request: Request) -> str:
        """Get rate limit for chat endpoint based on API key tier.

        Returns tiered limit if configured, otherwise static "30/minute".
        """
        if tiered_limit_func is not None:
            return tiered_limit_func(request)
        return "30/minute"

    app.state.get_chat_rate_limit = get_chat_rate_limit

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

    # Initialize session store based on configuration
    from consoul.sdk.session_store import MemorySessionStore, RedisSessionStore
    from consoul.server.session_locks import SessionLockManager

    session_store: (
        MemorySessionStore | RedisSessionStore | Any
    )  # Any for ResilientSessionStore
    if config.session.redis_url:
        if config.session.fallback_enabled:
            # Use resilient wrapper with fallback support (SOUL-328)
            from consoul.server.resilient_store import ResilientSessionStore

            def metrics_callback(event: str, value: bool) -> None:
                """Update metrics when Redis state changes."""
                if hasattr(app.state, "metrics") and app.state.metrics:
                    if event == "degraded":
                        app.state.metrics.set_redis_degraded(1)
                    elif event == "recovered":
                        app.state.metrics.set_redis_degraded(0)
                        app.state.metrics.increment_redis_recovered()

            session_store = ResilientSessionStore(
                redis_url=config.session.redis_url,
                ttl=config.session.ttl,
                prefix=config.session.key_prefix,
                fallback_enabled=True,
                reconnect_interval=config.session.reconnect_interval,
                metrics_callback=metrics_callback,
            )
        else:
            # Original fail-fast behavior (default)
            try:
                import redis

                redis_client = redis.from_url(config.session.redis_url)
                session_store = RedisSessionStore(
                    redis_client=redis_client,
                    ttl=config.session.ttl,
                    prefix=config.session.key_prefix,
                )
                logger.info(f"Session store: Redis ({config.session.redis_url})")
            except Exception as e:
                # FAIL-FAST: No silent fallback to memory in production
                raise RuntimeError(
                    f"Redis session store configured but unavailable: {e}. "
                    "Set CONSOUL_SESSION_REDIS_URL='' to use in-memory storage."
                ) from e
    else:
        session_store = MemorySessionStore(ttl=config.session.ttl)
        logger.warning(
            "Session store: In-memory (not distributed). "
            "Set CONSOUL_SESSION_REDIS_URL for production."
        )

    app.state.session_store = session_store
    app.state.session_locks = SessionLockManager()

    # Initialize WebSocket connection manager
    from consoul.server.endpoints.websocket import WebSocketConnectionManager

    app.state.ws_connections = WebSocketConnectionManager()

    # Register health endpoint (exempt from auth and rate limiting)
    @app.get("/health", tags=["monitoring"], response_model=HealthResponse)  # type: ignore[misc]
    @limiter.exempt
    async def health() -> HealthResponse:
        """Health check endpoint for monitoring systems.

        Returns basic service status and version. This endpoint bypasses
        authentication and rate limiting for reliable monitoring.

        Returns:
            HealthResponse: Standardized health check response with ISO 8601 timestamp

        Response Schema:
            {
                "status": "ok",
                "service": "Consoul API",
                "version": "0.4.2",
                "timestamp": "2025-12-25T10:30:45.123456Z"
            }
        """
        return HealthResponse(
            status="ok",
            service=config.app_name,
            version=app_version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            connections=app.state.ws_connections.active_count,
        )

    # Register readiness endpoint (exempt from auth and rate limiting)
    @app.get(
        "/ready",
        tags=["monitoring"],
        response_model=None,
        responses={
            200: {"model": ReadinessResponse},
            503: {"model": ReadinessErrorResponse},
        },
    )  # type: ignore[misc]
    @limiter.exempt
    async def readiness() -> ReadinessResponse | JSONResponse:
        """Readiness check endpoint with dependency health checks.

        Checks the health of external dependencies (e.g., Redis) and returns
        503 if any are unhealthy. This endpoint bypasses authentication and
        rate limiting for reliable monitoring.

        Returns:
            ReadinessResponse: Success response when all dependencies healthy (200)
            JSONResponse: Error response when dependencies unhealthy (503)

        Response Schemas:
            Success (200):
            {
                "status": "ready",
                "checks": {"redis": true},
                "timestamp": "2025-12-25T10:30:45.123456Z"
            }

            Error (503):
            {
                "status": "not_ready",
                "checks": {"redis": false},
                "message": "Redis connection failed",
                "timestamp": "2025-12-25T10:30:45.123456Z"
            }
        """
        checks: dict[str, bool | str] = {}
        timestamp = datetime.now(timezone.utc).isoformat()
        is_degraded = False

        # Check Redis if configured for rate limiting
        if config.rate_limit.storage_url:
            redis_healthy = await check_redis_connection(config.rate_limit.storage_url)
            checks["redis"] = redis_healthy

            if not redis_healthy:
                return JSONResponse(
                    status_code=503,
                    content=ReadinessErrorResponse(
                        status="not_ready",
                        checks=checks,
                        message="Redis connection failed",
                        timestamp=timestamp,
                    ).model_dump(),
                )

        # Check session store mode (SOUL-328: Redis fallback support)
        store = app.state.session_store
        if hasattr(store, "mode"):
            checks["session_store"] = store.mode
            if store.mode == "degraded":
                is_degraded = True

        # Return success response (200 even if degraded - service is operational)
        response = ReadinessResponse(
            status="ready",
            checks=checks or {"status": "no_dependencies"},
            timestamp=timestamp,
        )

        # Add message for degraded mode
        if is_degraded:
            return JSONResponse(
                status_code=200,
                content={
                    **response.model_dump(),
                    "message": "Running in fallback mode",
                },
            )

        return response

    # Helper for optional auth (works with or without API keys configured)
    def get_optional_auth() -> Callable[[Request], Coroutine[Any, Any, str | None]]:
        """Get auth dependency that works with or without API keys configured."""

        async def verify(request: Request) -> str | None:
            if request.app.state.auth is not None:
                result: str | None = await request.app.state.auth.verify(request)
                return result
            return None

        return verify

    # Chat request body dependency
    async def get_chat_request(request: Request) -> ChatRequest:
        """Parse and validate chat request from body."""
        from fastapi import HTTPException
        from pydantic import ValidationError

        try:
            body = await request.json()
            return ChatRequest(**body)
        except ValidationError as e:
            raise HTTPException(
                status_code=422,
                detail=e.errors(),
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request body: {e}",
            ) from e

    # Register chat endpoint
    @app.post(
        "/chat",
        tags=["chat"],
        response_model=ChatResponse,
        responses={
            503: {
                "model": ChatErrorResponse,
                "description": "Session storage unavailable",
            },
            500: {"model": ChatErrorResponse, "description": "Internal server error"},
        },
    )  # type: ignore[misc]
    @limiter.limit(get_chat_rate_limit)  # type: ignore[misc]
    async def chat(
        request: Request,
        chat_request: ChatRequest = Depends(get_chat_request),  # noqa: B008
        api_key: str | None = Depends(get_optional_auth()),
    ) -> ChatResponse | JSONResponse:
        """HTTP chat endpoint with session management.

        Processes chat messages with automatic session creation and persistence.
        Sessions are identified by session_id and maintain conversation history
        across requests.

        Args:
            request: FastAPI request object
            chat_request: Chat request with session_id and message
            api_key: Optional API key (if authentication configured)

        Returns:
            ChatResponse on success, JSONResponse with ChatErrorResponse on failure

        Raises:
            HTTPException: 401 if authentication fails (when configured)
            HTTPException: 429 if rate limit exceeded
        """
        import asyncio

        from consoul.sdk import create_session, restore_session, save_session_state
        from consoul.server.session_locks import SessionLock

        session_id = chat_request.session_id
        timestamp = datetime.now(timezone.utc).isoformat()
        store = request.app.state.session_store
        lock_manager = request.app.state.session_locks

        try:
            # Per-session lock ensures atomic load→chat→save (prevents race conditions)
            async with SessionLock(lock_manager, session_id):
                # Load session state (blocking Redis call → run in thread)
                state = await asyncio.to_thread(store.load, session_id)

                if state:
                    console = restore_session(state)
                    # Warn if model parameter differs from existing session
                    if chat_request.model and chat_request.model != console.model_name:
                        logger.warning(
                            f"Ignoring model={chat_request.model!r} for existing session "
                            f"{session_id} (locked to {console.model_name})"
                        )
                else:
                    console = create_session(
                        session_id=session_id,
                        model=chat_request.model,
                        tools=False,
                    )

                # Run blocking chat in thread pool
                response_text = await asyncio.to_thread(
                    console.chat, chat_request.message
                )

                # Save session state (blocking Redis call → run in thread)
                new_state = save_session_state(console)
                await asyncio.to_thread(store.save, session_id, new_state)

            cost = console.last_cost

            # Record token usage metrics (if metrics enabled)
            metrics = request.app.state.metrics
            if metrics is not None:
                metrics.record_tokens(
                    input_tokens=cost.get("input_tokens", 0),
                    output_tokens=cost.get("output_tokens", 0),
                    model=console.model_name,
                    session_id=session_id,
                )

            return ChatResponse(
                session_id=session_id,
                response=response_text,
                model=console.model_name,
                usage=ChatUsage(
                    input_tokens=cost.get("input_tokens", 0),
                    output_tokens=cost.get("output_tokens", 0),
                    total_tokens=cost.get("total_tokens", 0),
                    estimated_cost=cost.get("estimated_cost", 0.0),
                ),
                timestamp=timestamp,
            )
        except OSError as e:
            logger.error(f"Session storage error for {session_id}: {e}")
            return JSONResponse(
                status_code=503,
                content=ChatErrorResponse(
                    error="storage_unavailable",
                    message="Session storage temporarily unavailable",
                    timestamp=timestamp,
                ).model_dump(),
            )
        except Exception as e:
            logger.exception(f"Chat error for session {session_id}: {e}")
            return JSONResponse(
                status_code=500,
                content=ChatErrorResponse(
                    error="internal_error",
                    message=str(e),
                    timestamp=timestamp,
                ).model_dump(),
            )

    # Register WebSocket endpoint
    from consoul.server.endpoints.websocket import websocket_chat_handler

    @app.websocket("/ws/chat/{session_id}")  # type: ignore[misc]
    async def websocket_chat(
        websocket: WebSocket,
        session_id: str,
        api_key: str | None = None,  # Query param: ?api_key=xxx
    ) -> None:
        """WebSocket endpoint for streaming AI chat with tool approval.

        Provides token-by-token streaming, bidirectional tool approval,
        and session management compatible with HTTP /chat endpoint.

        Args:
            websocket: WebSocket connection
            session_id: Unique session identifier from URL path
            api_key: Optional API key from query parameter

        Protocol:
            Client → Server:
                {"type": "message", "content": "user message"}
                {"type": "tool_approval", "id": "call_123", "approved": true}

            Server → Client:
                {"type": "token", "data": {"text": "..."}}
                {"type": "tool_approval_request", "data": {...}}
                {"type": "done", "data": {"usage": {...}, "timestamp": "..."}}
                {"type": "error", "data": {"message": "..."}}
        """
        await websocket_chat_handler(websocket, session_id, api_key)

    logger.info(f"Server factory created: {config.app_name} v{app_version}")
    logger.info("Health endpoint: GET /health (auth: bypass, rate_limit: exempt)")
    logger.info("Readiness endpoint: GET /ready (auth: bypass, rate_limit: exempt)")
    logger.info("Chat endpoint: POST /chat (auth: optional, rate_limit: 30/minute)")
    logger.info(
        "WebSocket endpoint: WS /ws/chat/{session_id} (auth: optional, streaming)"
    )

    return app
