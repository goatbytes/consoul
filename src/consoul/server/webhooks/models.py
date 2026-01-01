"""Pydantic models for webhook system.

Provides data models for webhook registration, payloads, and delivery records.
All models are designed for API serialization and Redis storage.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WebhookEventType(str, Enum):
    """Supported webhook event types.

    Core events (initial implementation):
        - CHAT_COMPLETED: Chat response fully generated
        - CHAT_ERROR: Chat request failed
        - BATCH_COMPLETED: Batch request finished

    Future events (extensible):
        - TOOL_REQUESTED: Tool approval needed
        - TOOL_EXECUTED: Tool finished execution
        - SESSION_CREATED: New session initialized
        - SESSION_EXPIRED: Session TTL reached
    """

    # Core events (Phase 1)
    CHAT_COMPLETED = "chat.completed"
    CHAT_ERROR = "chat.error"
    BATCH_COMPLETED = "batch.completed"

    # Future events (extensible)
    TOOL_REQUESTED = "tool.requested"
    TOOL_EXECUTED = "tool.executed"
    SESSION_CREATED = "session.created"
    SESSION_EXPIRED = "session.expired"


class DeliveryStatus(str, Enum):
    """Webhook delivery status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"


# =============================================================================
# Request/Response Models (API)
# =============================================================================


class WebhookCreateRequest(BaseModel):
    """Request body for webhook registration.

    Example:
        >>> request = WebhookCreateRequest(
        ...     url="https://example.com/webhook",
        ...     events=[WebhookEventType.CHAT_COMPLETED],
        ...     secret="whsec_abc123",
        ... )
    """

    url: str = Field(
        description="HTTPS URL to receive webhook events",
        examples=["https://example.com/webhooks/consoul"],
    )
    events: list[WebhookEventType] = Field(
        description="List of event types to subscribe to",
        min_length=1,
        examples=[[WebhookEventType.CHAT_COMPLETED, WebhookEventType.CHAT_ERROR]],
    )
    secret: str = Field(
        description="Secret for HMAC-SHA256 signature verification",
        min_length=16,
        examples=["whsec_abc123def456ghi789"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional custom metadata included in webhook payloads",
        examples=[{"customer_id": "cus_123", "environment": "production"}],
    )


class WebhookUpdateRequest(BaseModel):
    """Request body for updating a webhook.

    All fields are optional; only provided fields are updated.
    """

    url: str | None = Field(
        default=None,
        description="New HTTPS URL for webhook events",
    )
    events: list[WebhookEventType] | None = Field(
        default=None,
        description="New list of event types to subscribe to",
        min_length=1,
    )
    secret: str | None = Field(
        default=None,
        description="New secret for signature verification (rotates previous)",
        min_length=16,
    )
    enabled: bool | None = Field(
        default=None,
        description="Enable or disable the webhook",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="New custom metadata (replaces existing)",
    )


class WebhookResponse(BaseModel):
    """Webhook details returned by API.

    Note:
        The secret is never included in responses; it's only accepted on create/update.
    """

    id: str = Field(
        description="Unique webhook identifier",
        examples=["wh_abc123def456"],
    )
    url: str = Field(
        description="HTTPS URL receiving webhook events",
    )
    events: list[WebhookEventType] = Field(
        description="Event types this webhook is subscribed to",
    )
    enabled: bool = Field(
        description="Whether the webhook is currently enabled",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Custom metadata included in payloads",
    )
    created_at: str = Field(
        description="ISO 8601 timestamp when webhook was created",
    )
    updated_at: str = Field(
        description="ISO 8601 timestamp when webhook was last updated",
    )
    consecutive_failures: int = Field(
        default=0,
        description="Number of consecutive delivery failures",
    )
    last_delivery_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of last delivery attempt",
    )


# =============================================================================
# Payload Models (Webhook Delivery)
# =============================================================================


class DeliveryMetadata(BaseModel):
    """Metadata about the current delivery attempt.

    Included in every webhook payload to help with deduplication and debugging.
    """

    id: str = Field(
        description="Unique delivery attempt identifier",
        examples=["del_xyz789abc123"],
    )
    attempt: int = Field(
        description="Delivery attempt number (1 = first attempt)",
        ge=1,
        examples=[1, 2, 3],
    )
    webhook_id: str = Field(
        description="ID of the webhook receiving this delivery",
        examples=["wh_abc123def456"],
    )


class WebhookPayload(BaseModel):
    """Versioned webhook payload sent to registered URLs.

    The payload structure is versioned via `api_version` to support
    backwards-compatible evolution.

    Example:
        >>> payload = WebhookPayload(
        ...     id="evt_abc123",
        ...     type=WebhookEventType.CHAT_COMPLETED,
        ...     created="2025-01-01T00:00:00Z",
        ...     api_version="2025-01-01",
        ...     delivery=DeliveryMetadata(
        ...         id="del_xyz789",
        ...         attempt=1,
        ...         webhook_id="wh_123456",
        ...     ),
        ...     data={
        ...         "session_id": "user-abc123",
        ...         "response": "Hello! How can I help?",
        ...         "usage": {"input_tokens": 15, "output_tokens": 8},
        ...     },
        ... )
    """

    id: str = Field(
        description="Unique event identifier for deduplication",
        examples=["evt_abc123def456"],
    )
    type: WebhookEventType = Field(
        description="Type of event that triggered this webhook",
    )
    created: str = Field(
        description="ISO 8601 timestamp when event occurred",
        examples=["2025-01-01T00:00:00Z"],
    )
    api_version: str = Field(
        default="2025-01-01",
        description="API version for payload schema",
    )
    delivery: DeliveryMetadata = Field(
        description="Metadata about this delivery attempt",
    )
    data: dict[str, Any] = Field(
        description="Event-specific data payload",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Custom metadata from webhook registration",
    )


# =============================================================================
# Internal Models (Storage)
# =============================================================================


class DeliveryRecord(BaseModel):
    """Record of a webhook delivery attempt.

    Stored in Redis for delivery history and retry scheduling.
    """

    id: str = Field(
        description="Unique delivery identifier",
    )
    webhook_id: str = Field(
        description="ID of the target webhook",
    )
    event_id: str = Field(
        description="ID of the event being delivered",
    )
    event_type: WebhookEventType = Field(
        description="Type of event",
    )
    event_data: dict[str, Any] | None = Field(
        default=None,
        description="Original event data payload (preserved for replay)",
    )
    status: DeliveryStatus = Field(
        default=DeliveryStatus.PENDING,
        description="Current delivery status",
    )
    attempt: int = Field(
        default=1,
        description="Current attempt number",
        ge=1,
    )
    max_attempts: int = Field(
        default=5,
        description="Maximum retry attempts",
    )
    created_at: str = Field(
        description="ISO 8601 timestamp when delivery was created",
    )
    scheduled_at: str = Field(
        description="ISO 8601 timestamp when delivery is scheduled",
    )
    completed_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when delivery completed (success or final failure)",
    )
    response_status: int | None = Field(
        default=None,
        description="HTTP status code from delivery attempt",
    )
    response_body: str | None = Field(
        default=None,
        description="Truncated response body (max 1KB)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if delivery failed",
    )
    next_retry_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp for next retry (if applicable)",
    )


class WebhookRecord(BaseModel):
    """Internal webhook record stored in Redis.

    Extends WebhookResponse with internal fields like owner_id and secret.
    The secret is stored base64-encoded for payload signing.
    """

    id: str
    owner_id: str = Field(
        description="API key that owns this webhook (hashed for storage)",
    )
    url: str
    events: list[WebhookEventType]
    secret: str = Field(
        description="Base64-encoded webhook secret for payload signing",
    )
    enabled: bool = True
    metadata: dict[str, Any] | None = None
    created_at: str
    updated_at: str
    consecutive_failures: int = 0
    last_delivery_at: str | None = None

    def get_secret(self) -> str:
        """Decode and return the webhook secret for signing."""
        import base64

        return base64.b64decode(self.secret.encode()).decode()

    @staticmethod
    def encode_secret(secret: str) -> str:
        """Encode a secret for storage."""
        import base64

        return base64.b64encode(secret.encode()).decode()

    def to_response(self) -> WebhookResponse:
        """Convert to API response (excludes internal fields)."""
        return WebhookResponse(
            id=self.id,
            url=self.url,
            events=self.events,
            enabled=self.enabled,
            metadata=self.metadata,
            created_at=self.created_at,
            updated_at=self.updated_at,
            consecutive_failures=self.consecutive_failures,
            last_delivery_at=self.last_delivery_at,
        )


# =============================================================================
# Event Data Schemas (for type hints and documentation)
# =============================================================================


class ChatCompletedData(BaseModel):
    """Data payload for chat.completed events."""

    session_id: str = Field(description="Session ID for the conversation")
    response: str = Field(description="Generated response text (may be truncated)")
    model: str | None = Field(default=None, description="Model used for generation")
    usage: dict[str, int] | None = Field(
        default=None,
        description="Token usage (input_tokens, output_tokens, total_tokens)",
    )


class ChatErrorData(BaseModel):
    """Data payload for chat.error events."""

    session_id: str = Field(description="Session ID for the conversation")
    error_code: str = Field(description="Error code (e.g., E200, E301)")
    message: str = Field(description="Human-readable error message")


class BatchCompletedData(BaseModel):
    """Data payload for batch.completed events."""

    session_id: str = Field(description="Session ID for the batch")
    message_count: int = Field(description="Number of messages processed")
    success_count: int = Field(description="Number of successful messages")
    error_count: int = Field(description="Number of failed messages")
    total_usage: dict[str, int] | None = Field(
        default=None,
        description="Combined token usage for all messages",
    )
