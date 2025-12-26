"""Configuration models for Consoul server components.

Provides Pydantic models for configuring security middleware, rate limiting,
and server settings. All models support environment variable configuration.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def parse_comma_separated_list(v: str | list[str]) -> list[str]:
    """Parse comma-separated string or JSON array into list.

    Supports:
    - Comma-separated: "item1,item2,item3" → ["item1", "item2", "item3"]
    - JSON array: '["item1","item2"]' → ["item1", "item2"]
    - List passthrough: ["item1"] → ["item1"]

    Raises:
        ValueError: If string looks like JSON (starts with '[') but is malformed

    Note:
        This validator is used by SecurityConfig (api_keys, bypass_paths) and
        CORSConfig (allowed_origins). Malformed JSON will raise ValidationError
        at config initialization, not fall back to comma-separated parsing.
    """
    if isinstance(v, list):
        return [str(item).strip() for item in v]
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return []
        # Strict JSON parsing - if starts with '[' or '{', MUST be valid JSON array
        if v.startswith("[") or v.startswith("{"):
            try:
                parsed = json.loads(v)
                if not isinstance(parsed, list):
                    raise ValueError(
                        f"Expected JSON array, got {type(parsed).__name__}"
                    )
                return [str(item).strip() for item in parsed]
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON array: {e}") from e
        # Comma-separated
        return [item.strip() for item in v.split(",") if item.strip()]
    return []


def parse_semicolon_or_single(v: str | list[str] | list[str]) -> list[str]:
    """Parse rate limit string(s) into list.

    Supports:
    - "10/minute" -> ["10/minute"]
    - "10/minute;100/hour" -> ["10/minute", "100/hour"]
    - ["10/minute"] -> ["10/minute"]
    """
    if v is None:
        return ["10 per minute"]
    if isinstance(v, str):
        if ";" in v:
            return [item.strip() for item in v.split(";") if item.strip()]
        return [v.strip()] if v.strip() else ["10 per minute"]
    if isinstance(v, list):
        return [str(item).strip() for item in v]
    return ["10 per minute"]


class HealthResponse(BaseModel):
    """Health check endpoint response schema.

    Standardized response for GET /health endpoint, used by monitoring systems
    and orchestrators (Kubernetes, Docker Swarm, etc.) to verify service availability.

    Attributes:
        status: Health status indicator (always "ok" when service is running)
        service: Service name from ServerConfig.app_name
        version: Package version from importlib.metadata
        timestamp: ISO 8601 timestamp when health check was performed

    Example:
        >>> response = HealthResponse(
        ...     status="ok",
        ...     service="Consoul API",
        ...     version="0.4.2",
        ...     timestamp="2025-12-25T10:30:45.123456Z"
        ... )
    """

    status: Literal["ok"] = Field(
        default="ok",
        description="Health status indicator (always 'ok' when service is running)",
    )
    service: str = Field(
        description="Service name from configuration",
    )
    version: str = Field(
        description="Package version",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when health check was performed",
    )


class ReadinessResponse(BaseModel):
    """Readiness check endpoint success response schema.

    Returned with HTTP 200 when all dependencies are healthy. Used by orchestrators
    to determine if service is ready to receive traffic.

    Attributes:
        status: Readiness status (always "ready" on success)
        checks: Dictionary of dependency health checks (e.g., {"redis": true})
        timestamp: ISO 8601 timestamp when readiness check was performed

    Example:
        >>> response = ReadinessResponse(
        ...     status="ready",
        ...     checks={"redis": True},
        ...     timestamp="2025-12-25T10:30:45.123456Z"
        ... )
    """

    status: Literal["ready"] = Field(
        default="ready",
        description="Readiness status (always 'ready' on success)",
    )
    checks: dict[str, bool | str] = Field(
        description="Dictionary of dependency health checks",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when readiness check was performed",
    )


class ReadinessErrorResponse(BaseModel):
    """Readiness check endpoint error response schema.

    Returned with HTTP 503 when one or more dependencies are unhealthy. Indicates
    service should not receive traffic until dependencies recover.

    Attributes:
        status: Error status (always "not_ready" on failure)
        checks: Dictionary of dependency health checks showing which failed
        message: Human-readable error description
        timestamp: ISO 8601 timestamp when readiness check was performed

    Example:
        >>> response = ReadinessErrorResponse(
        ...     status="not_ready",
        ...     checks={"redis": False},
        ...     message="Redis connection failed",
        ...     timestamp="2025-12-25T10:30:45.123456Z"
        ... )
    """

    status: Literal["not_ready"] = Field(
        default="not_ready",
        description="Error status (always 'not_ready' on failure)",
    )
    checks: dict[str, bool | str] = Field(
        description="Dictionary of dependency health checks showing failures",
    )
    message: str = Field(
        description="Human-readable error description",
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp when readiness check was performed",
    )


class ChatRequest(BaseModel):
    """Request body for POST /chat endpoint.

    Attributes:
        session_id: Unique session identifier. Auto-creates session if not exists.
        message: User message to send to the AI.
        model: Optional model override (only applies on session creation).

    Example:
        >>> request = ChatRequest(
        ...     session_id="user-abc123",
        ...     message="What is the weather like?",
        ...     model="gpt-4o"
        ... )
    """

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique session identifier. Auto-creates session if not exists.",
        examples=["user-abc123", "session-uuid-v4"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=32768,
        description="User message to send to the AI (32KB max).",
        examples=["Hello, how are you?"],
    )
    model: str | None = Field(
        default=None,
        description="Model to use (only applies when creating new session). "
        "Ignored for existing sessions.",
        examples=["gpt-4o", "claude-3-5-sonnet-20241022"],
    )


class ChatUsage(BaseModel):
    """Token usage and cost information for a chat request.

    Attributes:
        input_tokens: Number of input tokens consumed.
        output_tokens: Number of output tokens generated.
        total_tokens: Total tokens (input + output).
        estimated_cost: Estimated cost in USD.

    Example:
        >>> usage = ChatUsage(
        ...     input_tokens=15,
        ...     output_tokens=8,
        ...     total_tokens=23,
        ...     estimated_cost=0.000115
        ... )
    """

    input_tokens: int = Field(
        ...,
        ge=0,
        description="Number of input tokens consumed",
    )
    output_tokens: int = Field(
        ...,
        ge=0,
        description="Number of output tokens generated",
    )
    total_tokens: int = Field(
        ...,
        ge=0,
        description="Total tokens (input + output)",
    )
    estimated_cost: float = Field(
        ...,
        ge=0.0,
        description="Estimated cost in USD",
    )


class ChatResponse(BaseModel):
    """Response body for POST /chat endpoint.

    Attributes:
        session_id: Session identifier (echoed from request).
        response: AI's response text.
        model: Model that generated the response.
        usage: Token usage and cost information.
        timestamp: ISO 8601 timestamp of response.

    Example:
        >>> response = ChatResponse(
        ...     session_id="user-abc123",
        ...     response="I'm doing well, thank you!",
        ...     model="gpt-4o",
        ...     usage=ChatUsage(
        ...         input_tokens=15,
        ...         output_tokens=8,
        ...         total_tokens=23,
        ...         estimated_cost=0.000115
        ...     ),
        ...     timestamp="2025-12-25T10:30:45.123456Z"
        ... )
    """

    session_id: str = Field(
        ...,
        description="Session identifier",
    )
    response: str = Field(
        ...,
        description="AI's response text",
    )
    model: str = Field(
        ...,
        description="Model that generated the response",
    )
    usage: ChatUsage = Field(
        ...,
        description="Token usage and cost information",
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp of response",
    )


class ChatErrorResponse(BaseModel):
    """Error response for chat endpoint failures.

    Used for 500 and 503 responses.

    Attributes:
        error: Error type identifier.
        message: Human-readable error description.
        timestamp: ISO 8601 timestamp when error occurred.

    Example:
        >>> error = ChatErrorResponse(
        ...     error="storage_unavailable",
        ...     message="Session storage temporarily unavailable",
        ...     timestamp="2025-12-25T10:30:45.123456Z"
        ... )
    """

    error: str = Field(
        ...,
        description="Error type identifier",
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when error occurred",
    )


class SecurityConfig(BaseSettings):
    """API key authentication configuration.

    Attributes:
        api_keys: List of valid API keys for authentication
        header_name: HTTP header name for API key (default: X-API-Key)
        query_name: Query parameter name for API key (default: api_key)
        bypass_paths: Paths that bypass authentication (e.g., /health)

    Environment Variables:
        CONSOUL_API_KEYS: Comma-separated list or JSON array
            - Comma: CONSOUL_API_KEYS="key1,key2"
            - JSON: CONSOUL_API_KEYS='["key1","key2"]'
            - Malformed JSON: CONSOUL_API_KEYS='["key1"' → ValidationError
        CONSOUL_API_KEY_HEADER: Header name
        CONSOUL_API_KEY_QUERY: Query parameter name
        CONSOUL_BYPASS_PATHS: Comma-separated or JSON array
            - Comma: CONSOUL_BYPASS_PATHS="/health,/metrics"
            - JSON: CONSOUL_BYPASS_PATHS='["/health","/metrics"]'
            - Malformed JSON raises ValidationError

    Example:
        >>> config = SecurityConfig(
        ...     api_keys=["secret-key-1", "secret-key-2"],
        ...     bypass_paths=["/health", "/metrics"]
        ... )
        >>> # Or from environment:
        >>> # CONSOUL_API_KEYS=key1,key2 python app.py
        >>> config = SecurityConfig()
    """

    model_config = SettingsConfigDict(
        env_prefix="CONSOUL_",
        # Allow strings to be converted by validators before JSON parsing
        arbitrary_types_allowed=True,
    )

    # Use str | list[str] to allow env var parsing before validation
    api_keys: Annotated[
        str | list[str], BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default_factory=list,
        description="Valid API keys for authentication",
    )
    header_name: str = Field(
        default="X-API-Key",
        description="HTTP header name for API key",
    )
    query_name: str = Field(
        default="api_key",
        description="Query parameter name for API key",
    )
    bypass_paths: Annotated[
        str | list[str], BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default_factory=lambda: ["/health", "/ready", "/docs", "/openapi.json"],
        description="Paths that bypass authentication",
    )


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration.

    Attributes:
        default_limits: Default rate limits (e.g., ["10 per minute", "100 per hour"])
        storage_url: Redis URL for distributed rate limiting (optional)
        strategy: Rate limiting strategy (fixed-window, moving-window)
        key_prefix: Redis key prefix
        enabled: Whether rate limiting is enabled

    Environment Variables:
        CONSOUL_ENABLED: Enable/disable rate limiting (default: true)
        CONSOUL_DEFAULT_LIMITS: Default rate limit (supports multiple formats):
            - Single: "10/minute"
            - Multiple (semicolon): "10/minute;100/hour"
            - JSON: '["10/minute","100/hour"]'
        CONSOUL_RATE_LIMIT_REDIS_URL: Redis URL for distributed rate limiting
        REDIS_URL: Universal fallback for Redis URL

    Example:
        >>> config = RateLimitConfig(
        ...     default_limits=["10 per minute"],
        ...     storage_url="redis://localhost:6379"
        ... )
        >>> # Or from environment (single limit):
        >>> # CONSOUL_DEFAULT_LIMITS="10/minute"
        >>> # Or multiple limits:
        >>> # CONSOUL_DEFAULT_LIMITS="10/minute;100/hour;1000/day"
        >>> config = RateLimitConfig()
    """

    # NO env_prefix - use explicit full names for deterministic resolution
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    enabled: bool = Field(
        default=True,
        description="Whether rate limiting is enabled",
        validation_alias="CONSOUL_ENABLED",
    )
    # Use str | list[str] to allow env var parsing before validation
    default_limits: Annotated[
        str | list[str], BeforeValidator(parse_semicolon_or_single)
    ] = Field(
        default_factory=lambda: ["10 per minute"],
        description="Default rate limits",
        validation_alias="CONSOUL_DEFAULT_LIMITS",
    )
    storage_url: str | None = Field(
        default=None,
        description="Redis URL for distributed rate limiting",
        validation_alias=AliasChoices(
            "CONSOUL_RATE_LIMIT_REDIS_URL",
            "REDIS_URL",  # Universal fallback
        ),
    )
    strategy: Literal["fixed-window", "moving-window"] = Field(
        default="moving-window",
        description="Rate limiting strategy",
        validation_alias="CONSOUL_STRATEGY",
    )
    key_prefix: str = Field(
        default="consoul:ratelimit",
        description="Redis key prefix",
        validation_alias="CONSOUL_KEY_PREFIX",
    )


class CORSConfig(BaseSettings):
    """CORS configuration with environment variable support.

    Attributes:
        allowed_origins: List of allowed origins (use specific domains in production)
        allow_credentials: Whether to allow credentials
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed HTTP headers
        max_age: Preflight cache duration in seconds

    Environment Variables:
        CONSOUL_CORS_ORIGINS: Allowed origins (comma-separated or JSON array)
            - Single: CONSOUL_CORS_ORIGINS="https://app.com"
            - Comma: CONSOUL_CORS_ORIGINS="https://app.com,https://admin.com"
            - JSON: CONSOUL_CORS_ORIGINS='["https://app.com","https://admin.com"]'
            - Malformed JSON: CONSOUL_CORS_ORIGINS='["https://app.com"' → ValidationError
        CONSOUL_CORS_ALLOW_CREDENTIALS: Allow credentials (true/false)
        CONSOUL_CORS_ALLOW_METHODS: Allowed methods (comma or JSON)
        CONSOUL_CORS_ALLOW_HEADERS: Allowed headers (comma or JSON)
        CONSOUL_CORS_MAX_AGE: Preflight cache duration (seconds)

    Example:
        >>> config = CORSConfig(
        ...     allowed_origins=["https://app.example.com"],
        ...     allow_credentials=True
        ... )
    """

    # NO env_prefix - use explicit full names for deterministic resolution
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    allowed_origins: Annotated[
        str | list[str], BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default_factory=lambda: ["*"],
        description="Allowed origins (use specific domains in production)",
        validation_alias=AliasChoices(
            "CONSOUL_CORS_ORIGINS", "CONSOUL_CORS_ALLOWED_ORIGINS"
        ),
    )
    allow_credentials: bool = Field(
        default=False,
        description="Whether to allow credentials (set to False when using wildcard origins)",
        validation_alias="CONSOUL_CORS_ALLOW_CREDENTIALS",
    )
    allow_methods: Annotated[
        str | list[str], BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP methods",
        validation_alias="CONSOUL_CORS_ALLOW_METHODS",
    )
    allow_headers: Annotated[
        str | list[str], BeforeValidator(parse_comma_separated_list)
    ] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP headers",
        validation_alias="CONSOUL_CORS_ALLOW_HEADERS",
    )
    max_age: int = Field(
        default=600,
        description="Preflight cache duration in seconds",
        validation_alias="CONSOUL_CORS_MAX_AGE",
    )


class SessionConfig(BaseSettings):
    """Session storage configuration.

    Environment Variables:
        CONSOUL_SESSION_REDIS_URL: Redis URL for session storage
        REDIS_URL: Universal fallback for Redis URL

    Example:
        # Dedicated session Redis
        CONSOUL_SESSION_REDIS_URL=redis://localhost:6379/1

        # Universal fallback
        REDIS_URL=redis://localhost:6379/0
    """

    # NO env_prefix - use explicit full names for deterministic resolution
    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")

    redis_url: str | None = Field(
        default=None,
        description="Redis URL for session storage",
        validation_alias=AliasChoices(
            "CONSOUL_SESSION_REDIS_URL",
            "REDIS_URL",  # Universal fallback
        ),
    )
    ttl: int = Field(
        default=3600,
        description="Session TTL in seconds",
        validation_alias="CONSOUL_SESSION_TTL",
    )
    key_prefix: str = Field(
        default="consoul:session:",
        description="Redis key prefix",
        validation_alias="CONSOUL_SESSION_KEY_PREFIX",
    )


class ServerConfig(BaseSettings):
    """Complete server configuration.

    Combines all middleware configuration into a single model for convenience.

    Attributes:
        security: API key authentication configuration
        rate_limit: Rate limiting configuration
        cors: CORS configuration
        session: Session storage configuration
        host: Server host
        port: Server port
        reload: Enable auto-reload (development only)

    Environment Variables:
        CONSOUL_HOST: Server host
        CONSOUL_PORT: Server port
        CONSOUL_RELOAD: Enable auto-reload

        See nested config classes for their environment variables:
        - SecurityConfig: CONSOUL_API_KEYS, etc.
        - RateLimitConfig: CONSOUL_RATE_LIMIT_REDIS_URL, etc.
        - CORSConfig: CONSOUL_CORS_ORIGINS, etc.
        - SessionConfig: CONSOUL_SESSION_REDIS_URL, etc.

    Example:
        >>> config = ServerConfig()
        >>> # Configure from environment variables
        >>> config = ServerConfig(
        ...     security=SecurityConfig(api_keys=["key1"]),
        ...     rate_limit=RateLimitConfig(default_limits=["100/hour"])
        ... )
    """

    model_config = SettingsConfigDict(env_prefix="CONSOUL_")

    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="API key authentication configuration",
    )
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig,
        description="Rate limiting configuration",
    )
    cors: CORSConfig = Field(
        default_factory=CORSConfig,
        description="CORS configuration",
    )
    session: SessionConfig = Field(
        default_factory=SessionConfig,
        description="Session storage configuration",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Server host",
    )
    port: int = Field(
        default=8000,
        description="Server port",
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload (development only)",
    )
    app_name: str = Field(
        default="Consoul API",
        description="Application name for health checks and metadata",
    )
