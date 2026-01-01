"""Configuration for webhook system.

All configuration is loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebhookConfig(BaseSettings):
    """Webhook system configuration.

    Environment Variables:
        CONSOUL_WEBHOOK_ENABLED: Enable webhook system (default: false)
        CONSOUL_WEBHOOK_REDIS_URL: Redis URL for storage (falls back to REDIS_URL)
        CONSOUL_WEBHOOK_DELIVERY_TIMEOUT: HTTP timeout in seconds (default: 30)
        CONSOUL_WEBHOOK_MAX_RETRIES: Max retry attempts (default: 5)
        CONSOUL_WEBHOOK_QUEUE_MAX_DEPTH: Max pending deliveries (default: 10000)
        CONSOUL_WEBHOOK_MAX_INFLIGHT: Max concurrent deliveries per webhook (default: 5)
        CONSOUL_WEBHOOK_ALLOW_LOCALHOST: Allow localhost URLs (default: false)
        CONSOUL_WEBHOOK_MAX_PAYLOAD_SIZE: Max payload bytes (default: 65536)
        CONSOUL_WEBHOOK_FALLBACK_ENABLED: Enable memory fallback (default: false)
        CONSOUL_WEBHOOK_FAILURE_THRESHOLD: Failures before auto-disable (default: 5)
        CONSOUL_WEBHOOK_SIGNATURE_MAX_AGE: Max signature age in seconds (default: 300)

    Example:
        >>> config = WebhookConfig()
        >>> config.enabled
        False
        >>> config = WebhookConfig(enabled=True, redis_url="redis://localhost:6379")
    """

    model_config = SettingsConfigDict(
        env_prefix="CONSOUL_WEBHOOK_",
        env_file=".env",
        extra="ignore",
    )

    # Feature toggle
    enabled: bool = Field(
        default=False,
        description="Enable webhook system",
    )

    # Storage
    redis_url: str | None = Field(
        default=None,
        description="Redis URL for webhook storage (falls back to CONSOUL_REDIS_URL)",
    )
    fallback_enabled: bool = Field(
        default=False,
        description="Enable in-memory fallback if Redis unavailable",
    )

    # Delivery settings
    delivery_timeout: int = Field(
        default=30,
        description="HTTP timeout for webhook delivery in seconds",
        ge=1,
        le=120,
    )
    max_retries: int = Field(
        default=5,
        description="Maximum retry attempts before marking as failed",
        ge=1,
        le=10,
    )

    # Queue settings
    queue_max_depth: int = Field(
        default=10000,
        description="Maximum pending deliveries in queue",
        ge=100,
    )
    max_inflight: int = Field(
        default=5,
        description="Maximum concurrent deliveries per webhook",
        ge=1,
        le=20,
    )

    # Security settings
    allow_localhost: bool = Field(
        default=False,
        description="Allow localhost URLs (development only)",
    )
    max_payload_size: int = Field(
        default=65536,
        description="Maximum webhook payload size in bytes (64KB default)",
        ge=1024,
    )
    signature_max_age: int = Field(
        default=300,
        description="Maximum signature age in seconds for replay protection",
        ge=60,
    )

    # Auto-disable settings
    failure_threshold: int = Field(
        default=5,
        description="Consecutive failures before auto-disabling webhook",
        ge=1,
    )


# Retry schedule: delays in seconds for each retry attempt
# Follows exponential backoff: 1m, 5m, 30m, 2h, 24h
RETRY_DELAYS: list[int] = [
    60,  # 1 minute
    300,  # 5 minutes
    1800,  # 30 minutes
    7200,  # 2 hours
    86400,  # 24 hours
]
