"""Webhook-specific error codes.

Error codes in the E4xx range for webhook operations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class WebhookErrorCode(str, Enum):
    """Webhook-specific error codes (E4xx range)."""

    # E40x - Webhook resource errors
    WEBHOOK_NOT_FOUND = "E400"
    WEBHOOK_URL_INVALID = "E401"
    WEBHOOK_SSRF_BLOCKED = "E402"
    WEBHOOK_SECRET_INVALID = "E403"
    WEBHOOK_ALREADY_EXISTS = "E404"
    WEBHOOK_FORBIDDEN = "E405"

    # E41x - Webhook state errors
    WEBHOOK_QUEUE_FULL = "E410"
    WEBHOOK_DISABLED = "E411"
    WEBHOOK_RATE_LIMITED = "E412"

    # E42x - Delivery errors
    DELIVERY_NOT_FOUND = "E420"
    DELIVERY_REPLAY_FAILED = "E421"
    DELIVERY_EXPIRED = "E422"


# Error registry mapping codes to HTTP status and metadata
WEBHOOK_ERROR_REGISTRY: dict[WebhookErrorCode, dict[str, Any]] = {
    # E40x - Resource errors
    WebhookErrorCode.WEBHOOK_NOT_FOUND: {
        "error": "webhook_not_found",
        "http_status": 404,
        "recoverable": False,
        "message": "Webhook not found",
    },
    WebhookErrorCode.WEBHOOK_URL_INVALID: {
        "error": "webhook_url_invalid",
        "http_status": 400,
        "recoverable": False,
        "message": "Webhook URL is invalid or not accessible",
    },
    WebhookErrorCode.WEBHOOK_SSRF_BLOCKED: {
        "error": "webhook_ssrf_blocked",
        "http_status": 400,
        "recoverable": False,
        "message": "Webhook URL blocked for security reasons",
    },
    WebhookErrorCode.WEBHOOK_SECRET_INVALID: {
        "error": "webhook_secret_invalid",
        "http_status": 400,
        "recoverable": False,
        "message": "Webhook secret must be at least 16 characters",
    },
    WebhookErrorCode.WEBHOOK_ALREADY_EXISTS: {
        "error": "webhook_already_exists",
        "http_status": 409,
        "recoverable": False,
        "message": "A webhook for this URL already exists",
    },
    WebhookErrorCode.WEBHOOK_FORBIDDEN: {
        "error": "webhook_forbidden",
        "http_status": 403,
        "recoverable": False,
        "message": "You do not have permission to access this webhook",
    },
    # E41x - State errors
    WebhookErrorCode.WEBHOOK_QUEUE_FULL: {
        "error": "webhook_queue_full",
        "http_status": 503,
        "recoverable": True,
        "message": "Webhook delivery queue is full, try again later",
    },
    WebhookErrorCode.WEBHOOK_DISABLED: {
        "error": "webhook_disabled",
        "http_status": 409,
        "recoverable": False,
        "message": "Webhook is disabled due to consecutive delivery failures",
    },
    WebhookErrorCode.WEBHOOK_RATE_LIMITED: {
        "error": "webhook_rate_limited",
        "http_status": 429,
        "recoverable": True,
        "message": "Webhook management rate limit exceeded",
    },
    # E42x - Delivery errors
    WebhookErrorCode.DELIVERY_NOT_FOUND: {
        "error": "delivery_not_found",
        "http_status": 404,
        "recoverable": False,
        "message": "Delivery record not found",
    },
    WebhookErrorCode.DELIVERY_REPLAY_FAILED: {
        "error": "delivery_replay_failed",
        "http_status": 500,
        "recoverable": True,
        "message": "Failed to replay delivery, try again later",
    },
    WebhookErrorCode.DELIVERY_EXPIRED: {
        "error": "delivery_expired",
        "http_status": 410,
        "recoverable": False,
        "message": "Delivery record has expired and cannot be replayed",
    },
}


def get_webhook_error_status(code: WebhookErrorCode) -> int:
    """Get HTTP status for a webhook error code."""
    entry = WEBHOOK_ERROR_REGISTRY.get(code)
    if entry is None:
        return 500
    status = entry.get("http_status")
    return int(status) if status is not None else 500


def get_webhook_error_message(code: WebhookErrorCode) -> str:
    """Get default message for a webhook error code."""
    entry = WEBHOOK_ERROR_REGISTRY.get(code)
    if entry is None:
        return "Unknown webhook error"
    message = entry.get("message")
    return str(message) if message is not None else "Unknown webhook error"
