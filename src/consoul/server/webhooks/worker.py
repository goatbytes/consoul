"""arq worker for durable webhook delivery.

Provides background task processing with:
- Durable job queue (survives restarts)
- Exponential backoff retries
- Auto-disable after consecutive failures
- Metrics integration
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from consoul.server.webhooks.config import RETRY_DELAYS, WebhookConfig
from consoul.server.webhooks.delivery import WebhookDeliveryService
from consoul.server.webhooks.models import (
    DeliveryRecord,
    DeliveryStatus,
    WebhookEventType,
)
from consoul.server.webhooks.store import (
    ResilientWebhookStore,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from arq import ArqRedis

logger = logging.getLogger(__name__)

__all__ = [
    "WebhookWorkerSettings",
    "create_worker_settings",
    "deliver_webhook_task",
]


def now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


async def deliver_webhook_task(
    ctx: dict[str, Any],
    webhook_id: str,
    event_type: str,
    event_data: dict[str, Any],
    event_id: str,
    delivery_id: str,
    secret: str,
    attempt: int = 1,
) -> dict[str, Any]:
    """arq task for delivering a webhook.

    This task is enqueued by the WebhookEventEmitter and executed
    by arq workers. It handles delivery, result recording, and
    retry scheduling.

    Args:
        ctx: arq context containing dependencies
        webhook_id: ID of the webhook to deliver to
        event_type: Type of event being delivered
        event_data: Event payload data
        event_id: Unique event identifier
        delivery_id: Unique delivery identifier
        secret: Webhook secret for signing
        attempt: Current attempt number

    Returns:
        Dict with delivery result summary
    """
    store: ResilientWebhookStore = ctx["store"]
    delivery_service: WebhookDeliveryService = ctx["delivery_service"]
    config: WebhookConfig = ctx["config"]
    metrics_callback = ctx.get("metrics_callback")

    # Get webhook record (need the full record for URL and metadata)
    # Note: We need to access the underlying store for the full record
    webhook = None
    active = store.active_store
    if hasattr(active, "get_webhook_record"):
        webhook = active.get_webhook_record(webhook_id)
    elif hasattr(active, "_webhooks"):
        # Memory store - access internal dict
        webhooks = active._webhooks
        webhook = webhooks.get(webhook_id)

    if not webhook:
        logger.warning(f"Webhook {webhook_id} not found, skipping delivery")
        return {"status": "skipped", "reason": "webhook_not_found"}

    if not webhook.enabled:
        logger.info(f"Webhook {webhook_id} is disabled, skipping delivery")
        return {"status": "skipped", "reason": "webhook_disabled"}

    # Create/update delivery record
    event_type_enum = WebhookEventType(event_type)
    record = DeliveryRecord(
        id=delivery_id,
        webhook_id=webhook_id,
        event_id=event_id,
        event_type=event_type_enum,
        event_data=event_data,  # Store for replay
        status=DeliveryStatus.PENDING,
        attempt=attempt,
        max_attempts=config.max_retries,
        created_at=now_iso(),
        scheduled_at=now_iso(),
    )

    # Perform delivery
    result = await delivery_service.deliver(
        webhook=webhook,
        event_type=event_type_enum,
        event_data=event_data,
        secret=secret,
        delivery_id=delivery_id,
        event_id=event_id,
        attempt=attempt,
    )

    # Update record with result
    record.response_status = result.status_code
    record.response_body = result.response_body
    record.error_message = result.error

    # Record metrics
    if metrics_callback:
        status = "success" if result.success else "fail"
        metrics_callback("delivery", status, result.duration_ms)

    if result.success:
        # Success - update record and webhook
        record.status = DeliveryStatus.SUCCESS
        record.completed_at = now_iso()
        store.save_delivery(record)
        store.record_delivery_attempt(webhook_id, success=True)

        logger.info(
            f"Webhook delivered: {webhook_id} event={event_type} "
            f"status={result.status_code} duration={result.duration_ms:.0f}ms"
        )

        return {
            "status": "success",
            "status_code": result.status_code,
            "duration_ms": result.duration_ms,
        }

    # Failure - check for retry
    store.record_delivery_attempt(
        webhook_id, success=False, response_status=result.status_code
    )

    # Re-fetch webhook to get updated consecutive_failures
    active = store.active_store
    if hasattr(active, "get_webhook_record"):
        webhook = active.get_webhook_record(webhook_id)
    elif hasattr(active, "_webhooks"):
        webhooks = active._webhooks
        webhook = webhooks.get(webhook_id)
    else:
        webhook = None

    if not webhook:
        record.status = DeliveryStatus.FAILED
        record.completed_at = now_iso()
        store.save_delivery(record)
        return {"status": "failed", "reason": "webhook_deleted"}

    # Check if we should auto-disable
    if webhook.consecutive_failures >= config.failure_threshold:
        # Auto-disable webhook in storage
        store.disable_webhook(webhook_id)

        record.status = DeliveryStatus.FAILED
        record.completed_at = now_iso()
        store.save_delivery(record)

        logger.warning(
            f"Webhook {webhook_id} auto-disabled after {webhook.consecutive_failures} "
            f"consecutive failures"
        )

        if metrics_callback:
            metrics_callback("disabled", webhook_id, 0)

        return {
            "status": "disabled",
            "reason": "consecutive_failures",
            "failures": webhook.consecutive_failures,
        }

    # Check if we should retry
    if not result.should_retry or attempt >= config.max_retries:
        # No more retries
        record.status = DeliveryStatus.FAILED
        record.completed_at = now_iso()
        store.save_delivery(record)

        logger.warning(
            f"Webhook delivery failed (no retry): {webhook_id} "
            f"attempt={attempt} error={result.error}"
        )

        return {
            "status": "failed",
            "error": result.error,
            "attempt": attempt,
        }

    # Schedule retry
    next_attempt = attempt + 1
    retry_delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
    next_retry_at = delivery_service.calculate_next_retry(attempt)

    record.status = DeliveryStatus.PENDING
    record.next_retry_at = next_retry_at.isoformat()
    record.attempt = next_attempt
    store.save_delivery(record)

    # Enqueue retry job
    redis: ArqRedis = ctx["redis"]
    await redis.enqueue_job(
        "deliver_webhook_task",
        webhook_id,
        event_type,
        event_data,
        event_id,
        delivery_id,
        secret,
        next_attempt,
        _defer_by=retry_delay,
    )

    if metrics_callback:
        metrics_callback("retry", webhook_id, 0)

    logger.info(
        f"Webhook delivery scheduled for retry: {webhook_id} "
        f"attempt={next_attempt} delay={retry_delay}s error={result.error}"
    )

    return {
        "status": "retry_scheduled",
        "next_attempt": next_attempt,
        "retry_delay": retry_delay,
        "error": result.error,
    }


async def on_startup(ctx: dict[str, Any]) -> None:
    """arq worker startup hook.

    Initializes shared resources like the delivery service and store.
    """
    config: WebhookConfig = ctx["config"]

    # Initialize delivery service
    ctx["delivery_service"] = WebhookDeliveryService(
        timeout=config.delivery_timeout,
        max_retries=config.max_retries,
        allow_localhost=config.allow_localhost,
    )

    # Initialize store
    ctx["store"] = ResilientWebhookStore(
        redis_url=config.redis_url,
        fallback_enabled=config.fallback_enabled,
    )

    logger.info("Webhook worker started")


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """arq worker shutdown hook.

    Cleans up resources.
    """
    delivery_service: WebhookDeliveryService | None = ctx.get("delivery_service")
    if delivery_service:
        await delivery_service.close()

    logger.info("Webhook worker stopped")


def create_worker_settings(
    config: WebhookConfig,
    metrics_callback: Any | None = None,
) -> type:
    """Create arq worker settings class.

    Args:
        config: Webhook configuration
        metrics_callback: Optional metrics callback function

    Returns:
        WorkerSettings class for arq
    """
    from arq.connections import RedisSettings

    class _WebhookWorkerSettings:
        """arq worker settings for webhook delivery."""

        # Job functions
        functions: ClassVar[list[Callable[..., Any]]] = [deliver_webhook_task]

        # Lifecycle hooks
        on_startup = on_startup
        on_shutdown = on_shutdown

        # Redis connection
        redis_settings = RedisSettings.from_dsn(
            config.redis_url or "redis://localhost:6379"
        )

        # Concurrency
        max_jobs = config.max_inflight

        # Job settings
        job_timeout = config.delivery_timeout + 10  # Extra buffer
        max_tries = 1  # We handle retries ourselves

        # Custom context
        ctx: ClassVar[dict[str, Any]] = {
            "config": config,
            "metrics_callback": metrics_callback,
        }

    return _WebhookWorkerSettings


# Standalone worker settings (for running via `arq consoul.server.webhooks.worker.WorkerSettings`)
# Uses default config - in production, use create_worker_settings() with custom config
class WorkerSettings:
    """Default worker settings for standalone execution."""

    functions: ClassVar[list[Callable[..., Any]]] = [deliver_webhook_task]
    on_startup = on_startup
    on_shutdown = on_shutdown

    # Will be overridden by on_startup using config
    redis_settings: Any = None

    @staticmethod
    def get_redis_settings() -> Any:
        """Get Redis settings from environment."""
        from arq.connections import RedisSettings

        config = WebhookConfig()
        return RedisSettings.from_dsn(config.redis_url or "redis://localhost:6379")

    max_jobs = 10
    job_timeout = 40
    max_tries = 1

    ctx: ClassVar[dict[str, Any]] = {
        "config": WebhookConfig(),
        "metrics_callback": None,
    }


# Alias for public API
WebhookWorkerSettings = WorkerSettings
