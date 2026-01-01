"""Webhook system for async event delivery.

Provides webhook registration, delivery, and management for Consoul server events.
Supports HMAC-SHA256 signatures, exponential backoff retries, and SSRF protection.

Example:
    >>> from consoul.server.webhooks import WebhookEventType, WebhookPayload
    >>> payload = WebhookPayload(
    ...     id="evt_abc123",
    ...     type=WebhookEventType.CHAT_COMPLETED,
    ...     created="2025-01-01T00:00:00Z",
    ...     api_version="2025-01-01",
    ...     delivery=DeliveryMetadata(id="del_xyz", attempt=1, webhook_id="wh_123"),
    ...     data={"session_id": "user-abc", "response": "Hello!"},
    ... )
"""

from consoul.server.webhooks.config import RETRY_DELAYS, WebhookConfig
from consoul.server.webhooks.delivery import DeliveryResult, WebhookDeliveryService
from consoul.server.webhooks.emitter import WebhookEventEmitter
from consoul.server.webhooks.errors import (
    WEBHOOK_ERROR_REGISTRY,
    WebhookErrorCode,
    get_webhook_error_message,
    get_webhook_error_status,
)
from consoul.server.webhooks.models import (
    DeliveryMetadata,
    DeliveryRecord,
    DeliveryStatus,
    WebhookCreateRequest,
    WebhookEventType,
    WebhookPayload,
    WebhookRecord,
    WebhookResponse,
    WebhookUpdateRequest,
)
from consoul.server.webhooks.router import (
    DeliveryListResponse,
    TestWebhookResponse,
    WebhookListResponse,
    create_webhook_router,
)
from consoul.server.webhooks.security import (
    URLValidationError,
    ValidatedURL,
    WebhookURLValidator,
    is_safe_url,
)
from consoul.server.webhooks.signature import (
    SIGNATURE_HEADER,
    SignatureError,
    sign_payload,
    verify_signature,
)
from consoul.server.webhooks.store import (
    MemoryWebhookStore,
    RedisWebhookStore,
    ResilientWebhookStore,
    WebhookStoreProtocol,
    generate_delivery_id,
    generate_event_id,
    generate_webhook_id,
)
from consoul.server.webhooks.worker import (
    WorkerSettings as WebhookWorkerSettings,
)
from consoul.server.webhooks.worker import (
    create_worker_settings,
    deliver_webhook_task,
)

__all__ = [
    "RETRY_DELAYS",
    "SIGNATURE_HEADER",
    "WEBHOOK_ERROR_REGISTRY",
    "DeliveryListResponse",
    "DeliveryMetadata",
    "DeliveryRecord",
    "DeliveryResult",
    "DeliveryStatus",
    "MemoryWebhookStore",
    "RedisWebhookStore",
    "ResilientWebhookStore",
    "SignatureError",
    "TestWebhookResponse",
    "URLValidationError",
    "ValidatedURL",
    "WebhookConfig",
    "WebhookCreateRequest",
    "WebhookDeliveryService",
    "WebhookErrorCode",
    "WebhookEventEmitter",
    "WebhookEventType",
    "WebhookListResponse",
    "WebhookPayload",
    "WebhookRecord",
    "WebhookResponse",
    "WebhookStoreProtocol",
    "WebhookURLValidator",
    "WebhookUpdateRequest",
    "WebhookWorkerSettings",
    "create_webhook_router",
    "create_worker_settings",
    "deliver_webhook_task",
    "generate_delivery_id",
    "generate_event_id",
    "generate_webhook_id",
    "get_webhook_error_message",
    "get_webhook_error_status",
    "is_safe_url",
    "sign_payload",
    "verify_signature",
]
