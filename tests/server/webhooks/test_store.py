"""Tests for webhook storage layer."""

from __future__ import annotations

import pytest

from consoul.server.webhooks.models import (
    DeliveryRecord,
    DeliveryStatus,
    WebhookCreateRequest,
    WebhookEventType,
    WebhookUpdateRequest,
)
from consoul.server.webhooks.store import (
    MemoryWebhookStore,
    generate_delivery_id,
    generate_event_id,
    generate_webhook_id,
    hash_owner_id,
)


class TestGenerators:
    """Tests for ID generation functions."""

    def test_generate_webhook_id(self) -> None:
        """Test webhook ID generation."""
        id1 = generate_webhook_id()
        id2 = generate_webhook_id()

        assert id1.startswith("wh_")
        assert id2.startswith("wh_")
        assert id1 != id2
        assert len(id1) > 10

    def test_generate_delivery_id(self) -> None:
        """Test delivery ID generation."""
        id1 = generate_delivery_id()
        id2 = generate_delivery_id()

        assert id1.startswith("del_")
        assert id2.startswith("del_")
        assert id1 != id2

    def test_generate_event_id(self) -> None:
        """Test event ID generation."""
        id1 = generate_event_id()
        id2 = generate_event_id()

        assert id1.startswith("evt_")
        assert id2.startswith("evt_")
        assert id1 != id2

    def test_hash_owner_id(self) -> None:
        """Test owner ID hashing."""
        hash1 = hash_owner_id("api_key_1")
        hash2 = hash_owner_id("api_key_2")
        hash3 = hash_owner_id("api_key_1")

        # Different keys produce different hashes
        assert hash1 != hash2

        # Same key produces same hash
        assert hash1 == hash3

        # Hash is truncated
        assert len(hash1) == 16


class TestMemoryWebhookStore:
    """Tests for in-memory webhook store."""

    @pytest.fixture
    def store(self) -> MemoryWebhookStore:
        """Create a fresh store for each test."""
        return MemoryWebhookStore()

    @pytest.fixture
    def sample_request(self) -> WebhookCreateRequest:
        """Create a sample webhook creation request."""
        return WebhookCreateRequest(
            url="https://example.com/webhook",
            events=[WebhookEventType.CHAT_COMPLETED],
            secret="whsec_test_secret_key_12345",
            metadata={"customer_id": "cus_123"},
        )

    def test_create_webhook(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test creating a webhook."""
        owner_id = "api_key_123"

        result = store.create_webhook(owner_id, sample_request)

        assert result.id.startswith("wh_")
        assert result.url == sample_request.url
        assert result.events == sample_request.events
        assert result.enabled is True
        assert result.metadata == sample_request.metadata
        assert result.consecutive_failures == 0

    def test_get_webhook(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test retrieving a webhook by ID."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        result = store.get_webhook(created.id, owner_id)

        assert result is not None
        assert result.id == created.id
        assert result.url == sample_request.url

    def test_get_webhook_wrong_owner(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test that wrong owner cannot access webhook."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        result = store.get_webhook(created.id, "different_owner")

        assert result is None

    def test_get_webhook_not_found(self, store: MemoryWebhookStore) -> None:
        """Test handling of non-existent webhook."""
        result = store.get_webhook("wh_nonexistent", "api_key_123")

        assert result is None

    def test_list_webhooks(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test listing webhooks for an owner."""
        owner_id = "api_key_123"

        # Create multiple webhooks
        store.create_webhook(owner_id, sample_request)
        store.create_webhook(owner_id, sample_request)

        # Create webhook for different owner
        store.create_webhook("other_owner", sample_request)

        result = store.list_webhooks(owner_id)

        assert len(result) == 2

    def test_update_webhook(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test updating a webhook."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        update = WebhookUpdateRequest(
            url="https://new-url.com/webhook",
            enabled=False,
        )
        result = store.update_webhook(created.id, owner_id, update)

        assert result is not None
        assert result.url == "https://new-url.com/webhook"
        assert result.enabled is False
        # Events should remain unchanged
        assert result.events == sample_request.events

    def test_delete_webhook(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test deleting a webhook."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        result = store.delete_webhook(created.id, owner_id)

        assert result is True
        assert store.get_webhook(created.id, owner_id) is None

    def test_delete_webhook_wrong_owner(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test that wrong owner cannot delete webhook."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        result = store.delete_webhook(created.id, "different_owner")

        assert result is False
        # Webhook should still exist
        assert store.get_webhook(created.id, owner_id) is not None

    def test_get_webhooks_for_event(self, store: MemoryWebhookStore) -> None:
        """Test finding webhooks subscribed to an event type."""
        owner_id = "api_key_123"

        # Create webhook for chat.completed
        store.create_webhook(
            owner_id,
            WebhookCreateRequest(
                url="https://example.com/webhook1",
                events=[WebhookEventType.CHAT_COMPLETED],
                secret="whsec_secret_12345678",
            ),
        )

        # Create webhook for chat.error
        store.create_webhook(
            owner_id,
            WebhookCreateRequest(
                url="https://example.com/webhook2",
                events=[WebhookEventType.CHAT_ERROR],
                secret="whsec_secret_12345678",
            ),
        )

        result = store.get_webhooks_for_event(owner_id, WebhookEventType.CHAT_COMPLETED)

        assert len(result) == 1
        assert result[0].url == "https://example.com/webhook1"

    def test_record_delivery_attempt_success(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test recording a successful delivery."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        # Record failures first
        store.record_delivery_attempt(created.id, success=False)
        store.record_delivery_attempt(created.id, success=False)

        # Record success
        store.record_delivery_attempt(created.id, success=True)

        # Get updated webhook
        result = store.get_webhook(created.id, owner_id)

        assert result is not None
        assert result.consecutive_failures == 0

    def test_record_delivery_attempt_failure(
        self, store: MemoryWebhookStore, sample_request: WebhookCreateRequest
    ) -> None:
        """Test recording failed deliveries."""
        owner_id = "api_key_123"
        created = store.create_webhook(owner_id, sample_request)

        store.record_delivery_attempt(created.id, success=False)
        store.record_delivery_attempt(created.id, success=False)

        result = store.get_webhook(created.id, owner_id)

        assert result is not None
        assert result.consecutive_failures == 2

    def test_save_and_get_delivery(self, store: MemoryWebhookStore) -> None:
        """Test saving and retrieving delivery records."""
        record = DeliveryRecord(
            id="del_123",
            webhook_id="wh_456",
            event_id="evt_789",
            event_type=WebhookEventType.CHAT_COMPLETED,
            status=DeliveryStatus.SUCCESS,
            attempt=1,
            max_attempts=5,
            created_at="2025-01-01T00:00:00Z",
            scheduled_at="2025-01-01T00:00:00Z",
        )

        store.save_delivery(record)
        result = store.get_delivery("del_123")

        assert result is not None
        assert result.id == "del_123"
        assert result.status == DeliveryStatus.SUCCESS

    def test_delivery_history(self, store: MemoryWebhookStore) -> None:
        """Test retrieving delivery history."""
        webhook_id = "wh_456"

        # Create multiple deliveries
        for i in range(5):
            record = DeliveryRecord(
                id=f"del_{i}",
                webhook_id=webhook_id,
                event_id=f"evt_{i}",
                event_type=WebhookEventType.CHAT_COMPLETED,
                status=DeliveryStatus.SUCCESS,
                attempt=1,
                max_attempts=5,
                created_at="2025-01-01T00:00:00Z",
                scheduled_at="2025-01-01T00:00:00Z",
            )
            store.save_delivery(record)

        result = store.get_delivery_history(webhook_id, limit=3)

        assert len(result) == 3
