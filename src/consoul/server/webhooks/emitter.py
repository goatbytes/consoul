"""Webhook event emitter for triggering webhook deliveries.

Provides a centralized interface for emitting webhook events from
various parts of the application (chat endpoints, batch processing, etc.).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from consoul.server.webhooks.models import WebhookEventType
from consoul.server.webhooks.store import generate_delivery_id, generate_event_id

if TYPE_CHECKING:
    from arq import ArqRedis

    from consoul.server.webhooks.config import WebhookConfig
    from consoul.server.webhooks.store import ResilientWebhookStore

logger = logging.getLogger(__name__)

__all__ = [
    "WebhookEventEmitter",
]


class WebhookEventEmitter:
    """Centralized event emission for webhook triggers.

    The emitter queries matching webhooks for an event type and owner,
    then enqueues delivery jobs to arq for async processing.

    Example:
        >>> emitter = WebhookEventEmitter(store, redis, config)
        >>> await emitter.emit(
        ...     event_type=WebhookEventType.CHAT_COMPLETED,
        ...     data={"session_id": "user-123", "response": "Hello!"},
        ...     owner_id="sk-api-key-xxx",
        ... )
    """

    def __init__(
        self,
        store: ResilientWebhookStore,
        redis: ArqRedis,
        config: WebhookConfig,
        metrics_callback: Any | None = None,
    ) -> None:
        """Initialize event emitter.

        Args:
            store: Webhook store for looking up subscriptions
            redis: arq Redis connection for enqueueing jobs
            config: Webhook configuration
            metrics_callback: Optional callback for metrics
        """
        self._store = store
        self._redis = redis
        self._config = config
        self._metrics_callback = metrics_callback

    async def emit(
        self,
        event_type: WebhookEventType,
        data: dict[str, Any],
        owner_id: str,
        event_id: str | None = None,
    ) -> list[str]:
        """Emit a webhook event.

        Finds all webhooks subscribed to this event type for the given owner
        and enqueues delivery jobs.

        Args:
            event_type: Type of event to emit
            data: Event payload data
            owner_id: API key or owner identifier
            event_id: Optional event ID (generated if not provided)

        Returns:
            List of delivery IDs that were enqueued
        """
        if not self._config.enabled:
            return []

        # Generate event ID if not provided
        if not event_id:
            event_id = generate_event_id()

        # Find matching webhooks
        webhooks = self._store.get_webhooks_for_event(owner_id, event_type)

        if not webhooks:
            logger.debug(
                f"No webhooks found for {event_type.value} owner={owner_id[:8]}..."
            )
            return []

        delivery_ids: list[str] = []

        for webhook in webhooks:
            if not webhook.enabled:
                continue

            delivery_id = generate_delivery_id()
            delivery_ids.append(delivery_id)

            # Get the actual secret from the webhook record
            secret = webhook.get_secret()

            try:
                await self._redis.enqueue_job(
                    "deliver_webhook_task",
                    webhook.id,
                    event_type.value,
                    data,
                    event_id,
                    delivery_id,
                    secret,
                    1,  # Initial attempt
                )

                logger.debug(
                    f"Enqueued webhook delivery: {webhook.id} "
                    f"event={event_type.value} delivery={delivery_id}"
                )

            except Exception as e:
                logger.error(f"Failed to enqueue webhook delivery: {e}")
                delivery_ids.remove(delivery_id)

        if delivery_ids:
            logger.info(
                f"Emitted {event_type.value} to {len(delivery_ids)} webhooks "
                f"for owner={owner_id[:8]}..."
            )

            if self._metrics_callback:
                self._metrics_callback("emit", event_type.value, len(delivery_ids))

        return delivery_ids

    async def emit_chat_completed(
        self,
        owner_id: str,
        session_id: str,
        response: str,
        model: str | None = None,
        usage: dict[str, int] | None = None,
    ) -> list[str]:
        """Emit a chat.completed event.

        Convenience method for emitting chat completion events.

        Args:
            owner_id: API key or owner identifier
            session_id: Session ID for the conversation
            response: Generated response text (truncated if needed)
            model: Model used for generation
            usage: Token usage stats

        Returns:
            List of delivery IDs
        """
        # Truncate response if too long
        max_response_len = min(self._config.max_payload_size // 2, 4096)
        truncated_response = response[:max_response_len]
        if len(response) > max_response_len:
            truncated_response += "... [truncated]"

        data: dict[str, Any] = {
            "session_id": session_id,
            "response": truncated_response,
        }
        if model:
            data["model"] = model
        if usage:
            data["usage"] = usage

        return await self.emit(
            event_type=WebhookEventType.CHAT_COMPLETED,
            data=data,
            owner_id=owner_id,
        )

    async def emit_chat_error(
        self,
        owner_id: str,
        session_id: str,
        error_code: str,
        message: str,
    ) -> list[str]:
        """Emit a chat.error event.

        Args:
            owner_id: API key or owner identifier
            session_id: Session ID for the conversation
            error_code: Error code (e.g., E200)
            message: Human-readable error message

        Returns:
            List of delivery IDs
        """
        return await self.emit(
            event_type=WebhookEventType.CHAT_ERROR,
            data={
                "session_id": session_id,
                "error_code": error_code,
                "message": message,
            },
            owner_id=owner_id,
        )

    async def emit_batch_completed(
        self,
        owner_id: str,
        session_id: str,
        message_count: int,
        success_count: int,
        error_count: int,
        total_usage: dict[str, int] | None = None,
    ) -> list[str]:
        """Emit a batch.completed event.

        Args:
            owner_id: API key or owner identifier
            session_id: Session ID for the batch
            message_count: Total messages in batch
            success_count: Successfully processed messages
            error_count: Failed messages
            total_usage: Combined token usage

        Returns:
            List of delivery IDs
        """
        data: dict[str, Any] = {
            "session_id": session_id,
            "message_count": message_count,
            "success_count": success_count,
            "error_count": error_count,
        }
        if total_usage:
            data["total_usage"] = total_usage

        return await self.emit(
            event_type=WebhookEventType.BATCH_COMPLETED,
            data=data,
            owner_id=owner_id,
        )
