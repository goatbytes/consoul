"""Webhook storage with Redis backend and optional memory fallback.

Provides persistent storage for webhook registrations and delivery records.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from consoul.server.webhooks.models import (
    DeliveryRecord,
    WebhookCreateRequest,
    WebhookEventType,
    WebhookRecord,
    WebhookResponse,
    WebhookUpdateRequest,
)

# Re-export for convenience
__all__ = [
    "MemoryWebhookStore",
    "RedisWebhookStore",
    "ResilientWebhookStore",
    "WebhookRecord",
    "WebhookStoreProtocol",
    "generate_delivery_id",
    "generate_event_id",
    "generate_webhook_id",
    "hash_owner_id",
    "now_iso",
]

if TYPE_CHECKING:
    import redis

logger = logging.getLogger(__name__)


def generate_webhook_id() -> str:
    """Generate a unique webhook ID."""
    return f"wh_{secrets.token_hex(12)}"


def generate_delivery_id() -> str:
    """Generate a unique delivery ID."""
    return f"del_{secrets.token_hex(12)}"


def generate_event_id() -> str:
    """Generate a unique event ID."""
    return f"evt_{secrets.token_hex(12)}"


def hash_owner_id(owner_id: str) -> str:
    """Hash owner ID for storage (one-way, for lookup only)."""
    return hashlib.sha256(owner_id.encode()).hexdigest()[:16]


def now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class WebhookStoreProtocol(ABC):
    """Protocol for webhook storage backends."""

    @abstractmethod
    def create_webhook(
        self, owner_id: str, request: WebhookCreateRequest
    ) -> WebhookResponse:
        """Create a new webhook registration."""
        ...

    @abstractmethod
    def get_webhook(self, webhook_id: str, owner_id: str) -> WebhookResponse | None:
        """Get webhook by ID (enforces ownership)."""
        ...

    @abstractmethod
    def list_webhooks(self, owner_id: str) -> list[WebhookResponse]:
        """List all webhooks for an owner."""
        ...

    @abstractmethod
    def update_webhook(
        self, webhook_id: str, owner_id: str, request: WebhookUpdateRequest
    ) -> WebhookResponse | None:
        """Update webhook (enforces ownership)."""
        ...

    @abstractmethod
    def delete_webhook(self, webhook_id: str, owner_id: str) -> bool:
        """Delete webhook (enforces ownership)."""
        ...

    @abstractmethod
    def get_webhooks_for_event(
        self, owner_id: str, event_type: WebhookEventType
    ) -> list[WebhookRecord]:
        """Get all enabled webhooks subscribed to an event type."""
        ...

    @abstractmethod
    def record_delivery_attempt(
        self,
        webhook_id: str,
        success: bool,
        response_status: int | None = None,
    ) -> None:
        """Record a delivery attempt (updates consecutive_failures)."""
        ...

    @abstractmethod
    def disable_webhook(self, webhook_id: str) -> bool:
        """Disable a webhook (e.g., after consecutive failures).

        Returns True if the webhook was found and disabled.
        """
        ...

    @abstractmethod
    def get_delivery_history(
        self, webhook_id: str, limit: int = 50
    ) -> list[DeliveryRecord]:
        """Get recent delivery records for a webhook."""
        ...

    @abstractmethod
    def save_delivery(self, record: DeliveryRecord) -> None:
        """Save or update a delivery record."""
        ...

    @abstractmethod
    def get_delivery(self, delivery_id: str) -> DeliveryRecord | None:
        """Get a delivery record by ID."""
        ...


class MemoryWebhookStore(WebhookStoreProtocol):
    """In-memory webhook storage (non-persistent, for development/testing)."""

    def __init__(self) -> None:
        self._webhooks: dict[str, WebhookRecord] = {}
        self._webhooks_by_owner: dict[str, set[str]] = {}
        self._deliveries: dict[str, DeliveryRecord] = {}
        self._deliveries_by_webhook: dict[str, list[str]] = {}

    def create_webhook(
        self, owner_id: str, request: WebhookCreateRequest
    ) -> WebhookResponse:
        webhook_id = generate_webhook_id()
        owner_hash = hash_owner_id(owner_id)
        now = now_iso()

        record = WebhookRecord(
            id=webhook_id,
            owner_id=owner_hash,
            url=request.url,
            events=request.events,
            secret=WebhookRecord.encode_secret(request.secret),
            enabled=True,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
            consecutive_failures=0,
            last_delivery_at=None,
        )

        self._webhooks[webhook_id] = record
        if owner_hash not in self._webhooks_by_owner:
            self._webhooks_by_owner[owner_hash] = set()
        self._webhooks_by_owner[owner_hash].add(webhook_id)

        return record.to_response()

    def get_webhook(self, webhook_id: str, owner_id: str) -> WebhookResponse | None:
        record = self._webhooks.get(webhook_id)
        if not record:
            return None
        if record.owner_id != hash_owner_id(owner_id):
            return None
        return record.to_response()

    def list_webhooks(self, owner_id: str) -> list[WebhookResponse]:
        owner_hash = hash_owner_id(owner_id)
        webhook_ids = self._webhooks_by_owner.get(owner_hash, set())
        return [
            self._webhooks[wh_id].to_response()
            for wh_id in webhook_ids
            if wh_id in self._webhooks
        ]

    def update_webhook(
        self, webhook_id: str, owner_id: str, request: WebhookUpdateRequest
    ) -> WebhookResponse | None:
        record = self._webhooks.get(webhook_id)
        if not record:
            return None
        if record.owner_id != hash_owner_id(owner_id):
            return None

        if request.url is not None:
            record.url = request.url
        if request.events is not None:
            record.events = request.events
        if request.secret is not None:
            record.secret = WebhookRecord.encode_secret(request.secret)
        if request.enabled is not None:
            record.enabled = request.enabled
        if request.metadata is not None:
            record.metadata = request.metadata
        record.updated_at = now_iso()

        self._webhooks[webhook_id] = record
        return record.to_response()

    def delete_webhook(self, webhook_id: str, owner_id: str) -> bool:
        record = self._webhooks.get(webhook_id)
        if not record:
            return False
        if record.owner_id != hash_owner_id(owner_id):
            return False

        del self._webhooks[webhook_id]
        owner_hash = hash_owner_id(owner_id)
        if owner_hash in self._webhooks_by_owner:
            self._webhooks_by_owner[owner_hash].discard(webhook_id)
        return True

    def get_webhooks_for_event(
        self, owner_id: str, event_type: WebhookEventType
    ) -> list[WebhookRecord]:
        owner_hash = hash_owner_id(owner_id)
        webhook_ids = self._webhooks_by_owner.get(owner_hash, set())
        return [
            self._webhooks[wh_id]
            for wh_id in webhook_ids
            if wh_id in self._webhooks
            and self._webhooks[wh_id].enabled
            and event_type in self._webhooks[wh_id].events
        ]

    def record_delivery_attempt(
        self,
        webhook_id: str,
        success: bool,
        response_status: int | None = None,
    ) -> None:
        record = self._webhooks.get(webhook_id)
        if not record:
            return

        record.last_delivery_at = now_iso()
        if success:
            record.consecutive_failures = 0
        else:
            record.consecutive_failures += 1

        self._webhooks[webhook_id] = record

    def disable_webhook(self, webhook_id: str) -> bool:
        record = self._webhooks.get(webhook_id)
        if not record:
            return False

        record.enabled = False
        record.updated_at = now_iso()
        self._webhooks[webhook_id] = record
        return True

    def get_delivery_history(
        self, webhook_id: str, limit: int = 50
    ) -> list[DeliveryRecord]:
        delivery_ids = self._deliveries_by_webhook.get(webhook_id, [])
        # Return most recent first
        return [
            self._deliveries[d_id]
            for d_id in reversed(delivery_ids[-limit:])
            if d_id in self._deliveries
        ]

    def save_delivery(self, record: DeliveryRecord) -> None:
        self._deliveries[record.id] = record
        if record.webhook_id not in self._deliveries_by_webhook:
            self._deliveries_by_webhook[record.webhook_id] = []
        if record.id not in self._deliveries_by_webhook[record.webhook_id]:
            self._deliveries_by_webhook[record.webhook_id].append(record.id)
            # Cap at 100 entries per webhook
            if len(self._deliveries_by_webhook[record.webhook_id]) > 100:
                old_id = self._deliveries_by_webhook[record.webhook_id].pop(0)
                self._deliveries.pop(old_id, None)

    def get_delivery(self, delivery_id: str) -> DeliveryRecord | None:
        return self._deliveries.get(delivery_id)


class RedisWebhookStore(WebhookStoreProtocol):
    """Redis-backed webhook storage.

    Key schema:
        consoul:webhook:{id}                 -> JSON: WebhookRecord
        consoul:webhook:by_owner:{hash}      -> Set: webhook IDs
        consoul:delivery:{id}                -> JSON: DeliveryRecord
        consoul:delivery:by_webhook:{wh_id}  -> List: delivery IDs (capped 100)
    """

    def __init__(
        self,
        redis_client: redis.Redis[bytes],
        prefix: str = "consoul:",
        delivery_ttl: int = 604800,  # 7 days
    ) -> None:
        self._redis = redis_client
        self._prefix = prefix
        self._delivery_ttl = delivery_ttl

    def _webhook_key(self, webhook_id: str) -> str:
        return f"{self._prefix}webhook:{webhook_id}"

    def _owner_key(self, owner_hash: str) -> str:
        return f"{self._prefix}webhook:by_owner:{owner_hash}"

    def _delivery_key(self, delivery_id: str) -> str:
        return f"{self._prefix}delivery:{delivery_id}"

    def _delivery_list_key(self, webhook_id: str) -> str:
        return f"{self._prefix}delivery:by_webhook:{webhook_id}"

    def create_webhook(
        self, owner_id: str, request: WebhookCreateRequest
    ) -> WebhookResponse:
        webhook_id = generate_webhook_id()
        owner_hash = hash_owner_id(owner_id)
        now = now_iso()

        record = WebhookRecord(
            id=webhook_id,
            owner_id=owner_hash,
            url=request.url,
            events=request.events,
            secret=WebhookRecord.encode_secret(request.secret),
            enabled=True,
            metadata=request.metadata,
            created_at=now,
            updated_at=now,
            consecutive_failures=0,
            last_delivery_at=None,
        )

        # Store webhook
        self._redis.set(
            self._webhook_key(webhook_id),
            record.model_dump_json(),
        )

        # Add to owner's set
        self._redis.sadd(self._owner_key(owner_hash), webhook_id)

        logger.info(f"Created webhook {webhook_id} for owner {owner_hash[:8]}...")
        return record.to_response()

    def get_webhook(self, webhook_id: str, owner_id: str) -> WebhookResponse | None:
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return None

        record = WebhookRecord.model_validate_json(data)
        if record.owner_id != hash_owner_id(owner_id):
            return None

        return record.to_response()

    def list_webhooks(self, owner_id: str) -> list[WebhookResponse]:
        owner_hash = hash_owner_id(owner_id)
        webhook_ids = self._redis.smembers(self._owner_key(owner_hash))

        results: list[WebhookResponse] = []
        for wh_id in webhook_ids:
            wh_id_str = wh_id.decode() if isinstance(wh_id, bytes) else wh_id
            data = self._redis.get(self._webhook_key(wh_id_str))
            if data:
                record = WebhookRecord.model_validate_json(data)
                results.append(record.to_response())

        return results

    def update_webhook(
        self, webhook_id: str, owner_id: str, request: WebhookUpdateRequest
    ) -> WebhookResponse | None:
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return None

        record = WebhookRecord.model_validate_json(data)
        if record.owner_id != hash_owner_id(owner_id):
            return None

        if request.url is not None:
            record.url = request.url
        if request.events is not None:
            record.events = request.events
        if request.secret is not None:
            record.secret = WebhookRecord.encode_secret(request.secret)
        if request.enabled is not None:
            record.enabled = request.enabled
        if request.metadata is not None:
            record.metadata = request.metadata
        record.updated_at = now_iso()

        self._redis.set(self._webhook_key(webhook_id), record.model_dump_json())
        return record.to_response()

    def delete_webhook(self, webhook_id: str, owner_id: str) -> bool:
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return False

        record = WebhookRecord.model_validate_json(data)
        if record.owner_id != hash_owner_id(owner_id):
            return False

        # Delete webhook and remove from owner's set
        self._redis.delete(self._webhook_key(webhook_id))
        self._redis.srem(self._owner_key(record.owner_id), webhook_id)

        logger.info(f"Deleted webhook {webhook_id}")
        return True

    def get_webhooks_for_event(
        self, owner_id: str, event_type: WebhookEventType
    ) -> list[WebhookRecord]:
        owner_hash = hash_owner_id(owner_id)
        webhook_ids = self._redis.smembers(self._owner_key(owner_hash))

        results: list[WebhookRecord] = []
        for wh_id in webhook_ids:
            wh_id_str = wh_id.decode() if isinstance(wh_id, bytes) else wh_id
            data = self._redis.get(self._webhook_key(wh_id_str))
            if data:
                record = WebhookRecord.model_validate_json(data)
                if record.enabled and event_type in record.events:
                    results.append(record)

        return results

    def record_delivery_attempt(
        self,
        webhook_id: str,
        success: bool,
        response_status: int | None = None,
    ) -> None:
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return

        record = WebhookRecord.model_validate_json(data)
        record.last_delivery_at = now_iso()

        if success:
            record.consecutive_failures = 0
        else:
            record.consecutive_failures += 1

        self._redis.set(self._webhook_key(webhook_id), record.model_dump_json())

    def get_delivery_history(
        self, webhook_id: str, limit: int = 50
    ) -> list[DeliveryRecord]:
        # Get most recent delivery IDs (stored newest first with LPUSH)
        delivery_ids = self._redis.lrange(
            self._delivery_list_key(webhook_id), 0, limit - 1
        )

        results: list[DeliveryRecord] = []
        for d_id in delivery_ids:
            d_id_str = d_id.decode() if isinstance(d_id, bytes) else d_id
            data = self._redis.get(self._delivery_key(d_id_str))
            if data:
                results.append(DeliveryRecord.model_validate_json(data))

        return results

    def save_delivery(self, record: DeliveryRecord) -> None:
        # Save delivery with TTL
        self._redis.setex(
            self._delivery_key(record.id),
            self._delivery_ttl,
            record.model_dump_json(),
        )

        # Add to webhook's delivery list (newest first)
        list_key = self._delivery_list_key(record.webhook_id)
        self._redis.lpush(list_key, record.id)
        # Trim to keep only last 100
        self._redis.ltrim(list_key, 0, 99)

    def get_delivery(self, delivery_id: str) -> DeliveryRecord | None:
        data = self._redis.get(self._delivery_key(delivery_id))
        if not data:
            return None
        return DeliveryRecord.model_validate_json(data)

    def get_webhook_record(self, webhook_id: str) -> WebhookRecord | None:
        """Get raw webhook record (internal use for delivery)."""
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return None
        return WebhookRecord.model_validate_json(data)

    def disable_webhook(self, webhook_id: str) -> bool:
        data = self._redis.get(self._webhook_key(webhook_id))
        if not data:
            return False

        record = WebhookRecord.model_validate_json(data)
        record.enabled = False
        record.updated_at = now_iso()
        self._redis.set(self._webhook_key(webhook_id), record.model_dump_json())

        logger.info(f"Webhook {webhook_id} disabled")
        return True


class ResilientWebhookStore(WebhookStoreProtocol):
    """Webhook store with automatic Redis fallback.

    Similar to ResilientSessionStore, provides automatic fallback to
    in-memory storage if Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: str | None,
        prefix: str = "consoul:",
        fallback_enabled: bool = False,
        reconnect_interval: int = 60,
    ) -> None:
        self._redis_url = redis_url
        self._prefix = prefix
        self._fallback_enabled = fallback_enabled
        self._reconnect_interval = reconnect_interval

        self._primary: RedisWebhookStore | None = None
        self._fallback: MemoryWebhookStore | None = None
        self._mode: str = "memory"
        self._last_check: float = 0.0

        self._initialize()

    def _initialize(self) -> None:
        """Initialize storage backend."""
        if not self._redis_url:
            logger.info("Webhook store: Using in-memory storage (no Redis URL)")
            self._fallback = MemoryWebhookStore()
            self._mode = "memory"
            return

        try:
            import redis as redis_lib

            client = redis_lib.from_url(self._redis_url)
            client.ping()

            self._primary = RedisWebhookStore(client, self._prefix)
            self._mode = "redis"
            logger.info(f"Webhook store: Redis ({self._redis_url})")

        except Exception as e:
            if not self._fallback_enabled:
                raise RuntimeError(
                    f"Webhook Redis store unavailable: {e}. "
                    "Set CONSOUL_WEBHOOK_FALLBACK_ENABLED=true for degraded mode."
                ) from e

            self._fallback = MemoryWebhookStore()
            self._mode = "degraded"
            self._last_check = time.monotonic()
            logger.warning(
                "Webhook Redis unavailable - using in-memory fallback. "
                "Webhooks will not persist across restarts."
            )

    @property
    def mode(self) -> str:
        """Current storage mode: 'redis', 'memory', or 'degraded'."""
        return self._mode

    @property
    def active_store(self) -> WebhookStoreProtocol:
        """Get the currently active store."""
        if self._mode == "redis" and self._primary:
            return self._primary
        if self._fallback:
            return self._fallback
        raise RuntimeError("No webhook store available")

    def _try_recover(self) -> bool:
        """Attempt Redis reconnection."""
        if self._mode != "degraded" or not self._redis_url:
            return False

        now = time.monotonic()
        if now - self._last_check < self._reconnect_interval:
            return False

        self._last_check = now

        try:
            import redis as redis_lib

            client = redis_lib.from_url(self._redis_url)
            client.ping()

            self._primary = RedisWebhookStore(client, self._prefix)
            self._mode = "redis"
            logger.info("Webhook Redis connection recovered")
            return True
        except Exception:
            return False

    # Delegate all protocol methods to active store

    def create_webhook(
        self, owner_id: str, request: WebhookCreateRequest
    ) -> WebhookResponse:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.create_webhook(owner_id, request)

    def get_webhook(self, webhook_id: str, owner_id: str) -> WebhookResponse | None:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.get_webhook(webhook_id, owner_id)

    def list_webhooks(self, owner_id: str) -> list[WebhookResponse]:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.list_webhooks(owner_id)

    def update_webhook(
        self, webhook_id: str, owner_id: str, request: WebhookUpdateRequest
    ) -> WebhookResponse | None:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.update_webhook(webhook_id, owner_id, request)

    def delete_webhook(self, webhook_id: str, owner_id: str) -> bool:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.delete_webhook(webhook_id, owner_id)

    def get_webhooks_for_event(
        self, owner_id: str, event_type: WebhookEventType
    ) -> list[WebhookRecord]:
        if self._mode == "degraded":
            self._try_recover()
        return self.active_store.get_webhooks_for_event(owner_id, event_type)

    def record_delivery_attempt(
        self,
        webhook_id: str,
        success: bool,
        response_status: int | None = None,
    ) -> None:
        self.active_store.record_delivery_attempt(webhook_id, success, response_status)

    def get_delivery_history(
        self, webhook_id: str, limit: int = 50
    ) -> list[DeliveryRecord]:
        return self.active_store.get_delivery_history(webhook_id, limit)

    def save_delivery(self, record: DeliveryRecord) -> None:
        self.active_store.save_delivery(record)

    def get_delivery(self, delivery_id: str) -> DeliveryRecord | None:
        return self.active_store.get_delivery(delivery_id)

    def disable_webhook(self, webhook_id: str) -> bool:
        return self.active_store.disable_webhook(webhook_id)
