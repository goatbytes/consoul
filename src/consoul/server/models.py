"""Configuration models for Consoul server components.

Provides Pydantic models for configuring security middleware, rate limiting,
and server settings. All models support environment variable configuration.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_comma_separated_list(v: str | list[str] | list[str]) -> list[str]:
    """Parse comma-separated string into list.

    Supports:
    - "key1,key2,key3" -> ["key1", "key2", "key3"]
    - ["key1", "key2"] -> ["key1", "key2"]
    """
    if v is None or (isinstance(v, list) and len(v) == 0):
        return []
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    if isinstance(v, list):
        return [str(item).strip() for item in v]
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


class SecurityConfig(BaseSettings):
    """API key authentication configuration.

    Attributes:
        api_keys: List of valid API keys for authentication
        header_name: HTTP header name for API key (default: X-API-Key)
        query_name: Query parameter name for API key (default: api_key)
        bypass_paths: Paths that bypass authentication (e.g., /health)

    Environment Variables:
        CONSOUL_API_KEYS: Comma-separated list of API keys
        CONSOUL_API_KEY_HEADER: Header name
        CONSOUL_API_KEY_QUERY: Query parameter name

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
        default_factory=lambda: ["/health", "/docs", "/openapi.json"],
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
        CONSOUL_STORAGE_URL or CONSOUL_REDIS_URL: Redis connection URL

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

    model_config = SettingsConfigDict(env_prefix="CONSOUL_")

    enabled: bool = Field(
        default=True,
        description="Whether rate limiting is enabled",
    )
    # Use str | list[str] to allow env var parsing before validation
    default_limits: Annotated[
        str | list[str], BeforeValidator(parse_semicolon_or_single)
    ] = Field(
        default_factory=lambda: ["10 per minute"],
        description="Default rate limits",
    )
    storage_url: str | None = Field(
        default=None,
        description="Redis URL for distributed rate limiting",
        validation_alias="REDIS_URL",
    )
    strategy: Literal["fixed-window", "moving-window"] = Field(
        default="moving-window",
        description="Rate limiting strategy",
    )
    key_prefix: str = Field(
        default="consoul:ratelimit",
        description="Redis key prefix",
    )


class CORSConfig(BaseModel):
    """CORS configuration.

    Attributes:
        allowed_origins: List of allowed origins (use specific domains in production)
        allow_credentials: Whether to allow credentials
        allow_methods: Allowed HTTP methods
        allow_headers: Allowed HTTP headers
        max_age: Preflight cache duration in seconds

    Example:
        >>> config = CORSConfig(
        ...     allowed_origins=["https://app.example.com"],
        ...     allow_credentials=True
        ... )
    """

    allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed origins (use specific domains in production)",
    )
    allow_credentials: bool = Field(
        default=False,
        description="Whether to allow credentials (set to False when using wildcard origins)",
    )
    allow_methods: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP methods",
    )
    allow_headers: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP headers",
    )
    max_age: int = Field(
        default=600,
        description="Preflight cache duration in seconds",
    )


class ServerConfig(BaseSettings):
    """Complete server configuration.

    Combines all middleware configuration into a single model for convenience.

    Attributes:
        security: API key authentication configuration
        rate_limit: Rate limiting configuration
        cors: CORS configuration
        host: Server host
        port: Server port
        reload: Enable auto-reload (development only)

    Environment Variables:
        CONSOUL_HOST: Server host
        CONSOUL_PORT: Server port
        CONSOUL_RELOAD: Enable auto-reload

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
