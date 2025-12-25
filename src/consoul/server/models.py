"""Configuration models for Consoul server components.

Provides Pydantic models for configuring security middleware, rate limiting,
and server settings. All models support environment variable configuration.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Literal

from pydantic import AliasChoices, BeforeValidator, Field
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
