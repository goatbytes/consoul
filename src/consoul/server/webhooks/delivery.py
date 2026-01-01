"""Webhook delivery service using httpx.

Handles the actual HTTP delivery of webhooks with connection pooling,
timeouts, and result handling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from consoul.server.webhooks.config import RETRY_DELAYS
from consoul.server.webhooks.models import (
    DeliveryMetadata,
    DeliveryRecord,
    DeliveryStatus,
    WebhookEventType,
    WebhookPayload,
)
from consoul.server.webhooks.security import URLValidationError, WebhookURLValidator
from consoul.server.webhooks.signature import SIGNATURE_HEADER, sign_payload
from consoul.server.webhooks.store import generate_delivery_id, generate_event_id

if TYPE_CHECKING:
    import httpx

    from consoul.server.webhooks.store import WebhookRecord

logger = logging.getLogger(__name__)

__all__ = [
    "DeliveryResult",
    "WebhookDeliveryService",
]


@dataclass
class DeliveryResult:
    """Result of a webhook delivery attempt."""

    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    should_retry: bool = False
    duration_ms: float = 0.0


def now_iso() -> str:
    """Get current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class WebhookDeliveryService:
    """Handles webhook HTTP delivery.

    Uses httpx.AsyncClient for efficient connection pooling and
    async HTTP requests.

    Example:
        >>> service = WebhookDeliveryService(timeout=30)
        >>> result = await service.deliver(webhook, payload, secret)
        >>> if result.success:
        ...     print("Delivered successfully")
        ... elif result.should_retry:
        ...     print(f"Retry needed: {result.error}")
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 5,
        allow_localhost: bool = False,
        max_response_size: int = 1024,
    ) -> None:
        """Initialize delivery service.

        Args:
            timeout: HTTP timeout in seconds
            max_retries: Maximum retry attempts
            allow_localhost: Allow localhost URLs (development only)
            max_response_size: Max response body to store (bytes)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_response_size = max_response_size
        self.url_validator = WebhookURLValidator(allow_localhost=allow_localhost)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=False,  # We handle redirects manually for security
                http2=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def deliver(
        self,
        webhook: WebhookRecord,
        event_type: WebhookEventType,
        event_data: dict[str, Any],
        secret: str,
        delivery_id: str | None = None,
        event_id: str | None = None,
        attempt: int = 1,
    ) -> DeliveryResult:
        """Deliver a webhook event.

        Args:
            webhook: The webhook to deliver to
            event_type: Type of event
            event_data: Event-specific data
            secret: Webhook secret for signing
            delivery_id: Optional delivery ID (generated if not provided)
            event_id: Optional event ID (generated if not provided)
            attempt: Current attempt number

        Returns:
            DeliveryResult with success status and details
        """
        import time

        import httpx

        start_time = time.monotonic()

        # Generate IDs if not provided
        if not delivery_id:
            delivery_id = generate_delivery_id()
        if not event_id:
            event_id = generate_event_id()

        # Build payload
        payload = WebhookPayload(
            id=event_id,
            type=event_type,
            created=now_iso(),
            api_version="2025-01-01",
            delivery=DeliveryMetadata(
                id=delivery_id,
                attempt=attempt,
                webhook_id=webhook.id,
            ),
            data=event_data,
            metadata=webhook.metadata,
        )

        payload_bytes = payload.model_dump_json().encode("utf-8")

        # Sign payload
        signature = sign_payload(payload_bytes, secret)

        # Validate URL (re-validate at delivery time for DNS rebinding protection)
        try:
            self.url_validator.validate(webhook.url)
        except URLValidationError as e:
            duration = (time.monotonic() - start_time) * 1000
            return DeliveryResult(
                success=False,
                error=f"URL validation failed: {e.reason}",
                should_retry=False,  # Don't retry URL validation failures
                duration_ms=duration,
            )

        # Deliver
        try:
            client = await self._get_client()
            response = await client.post(
                webhook.url,
                content=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    SIGNATURE_HEADER: signature,
                    "User-Agent": "Consoul-Webhooks/1.0",
                },
            )

            duration = (time.monotonic() - start_time) * 1000

            # Truncate response body
            response_body = response.text[: self.max_response_size]

            # Check success (2xx status codes)
            if 200 <= response.status_code < 300:
                return DeliveryResult(
                    success=True,
                    status_code=response.status_code,
                    response_body=response_body,
                    duration_ms=duration,
                )

            # Determine if we should retry based on status code
            should_retry = response.status_code >= 500 or response.status_code == 429

            return DeliveryResult(
                success=False,
                status_code=response.status_code,
                response_body=response_body,
                error=f"HTTP {response.status_code}",
                should_retry=should_retry,
                duration_ms=duration,
            )

        except httpx.TimeoutException as e:
            duration = (time.monotonic() - start_time) * 1000
            return DeliveryResult(
                success=False,
                error=f"Timeout: {e}",
                should_retry=True,
                duration_ms=duration,
            )

        except httpx.ConnectError as e:
            duration = (time.monotonic() - start_time) * 1000
            return DeliveryResult(
                success=False,
                error=f"Connection error: {e}",
                should_retry=True,
                duration_ms=duration,
            )

        except httpx.HTTPError as e:
            duration = (time.monotonic() - start_time) * 1000
            return DeliveryResult(
                success=False,
                error=f"HTTP error: {e}",
                should_retry=True,
                duration_ms=duration,
            )

        except Exception as e:
            duration = (time.monotonic() - start_time) * 1000
            logger.exception(f"Unexpected error delivering webhook: {e}")
            return DeliveryResult(
                success=False,
                error=f"Unexpected error: {type(e).__name__}: {e}",
                should_retry=False,
                duration_ms=duration,
            )

    def calculate_next_retry(self, attempt: int) -> datetime:
        """Calculate when to schedule the next retry.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            datetime for next retry
        """
        from datetime import timedelta

        if attempt > len(RETRY_DELAYS):
            # Use last delay for any attempts beyond the schedule
            delay = RETRY_DELAYS[-1]
        else:
            delay = RETRY_DELAYS[attempt - 1]

        return datetime.now(timezone.utc) + timedelta(seconds=delay)

    def should_disable_webhook(self, consecutive_failures: int, threshold: int) -> bool:
        """Check if webhook should be auto-disabled.

        Args:
            consecutive_failures: Number of consecutive failures
            threshold: Failure threshold for auto-disable

        Returns:
            True if webhook should be disabled
        """
        return consecutive_failures >= threshold

    async def create_delivery_record(
        self,
        webhook_id: str,
        event_id: str,
        event_type: WebhookEventType,
        attempt: int = 1,
        max_attempts: int | None = None,
    ) -> DeliveryRecord:
        """Create a new delivery record.

        Args:
            webhook_id: ID of the target webhook
            event_id: ID of the event
            event_type: Type of event
            attempt: Current attempt number
            max_attempts: Maximum attempts (defaults to self.max_retries)

        Returns:
            New DeliveryRecord
        """
        now = now_iso()
        return DeliveryRecord(
            id=generate_delivery_id(),
            webhook_id=webhook_id,
            event_id=event_id,
            event_type=event_type,
            status=DeliveryStatus.PENDING,
            attempt=attempt,
            max_attempts=max_attempts or self.max_retries,
            created_at=now,
            scheduled_at=now,
        )
