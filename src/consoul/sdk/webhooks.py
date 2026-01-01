"""SDK helper for verifying Consoul webhook signatures.

This module provides a simple interface for webhook consumers to verify
incoming webhook requests.

Example:
    >>> from consoul.webhooks import verify
    >>> from fastapi import Request, HTTPException
    >>>
    >>> @app.post("/webhook")
    >>> async def handle_webhook(request: Request):
    ...     body = await request.body()
    ...     signature = request.headers.get("X-Consoul-Signature", "")
    ...     secret = os.environ["CONSOUL_WEBHOOK_SECRET"]
    ...
    ...     if not verify(body, signature, secret):
    ...         raise HTTPException(401, "Invalid webhook signature")
    ...
    ...     event = await request.json()
    ...     # Process event...

Flask Example:
    >>> from consoul.webhooks import verify
    >>> from flask import Flask, request, abort
    >>>
    >>> @app.route("/webhook", methods=["POST"])
    >>> def handle_webhook():
    ...     body = request.get_data()
    ...     signature = request.headers.get("X-Consoul-Signature", "")
    ...     secret = os.environ["CONSOUL_WEBHOOK_SECRET"]
    ...
    ...     if not verify(body, signature, secret):
    ...         abort(401)
    ...
    ...     event = request.get_json()
    ...     # Process event...
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "SIGNATURE_HEADER",
    "WebhookVerificationError",
    "verify",
    "verify_with_timestamp",
]

# Header name for webhook signatures
SIGNATURE_HEADER = "X-Consoul-Signature"

# Signature version prefix
_SIGNATURE_VERSION = "v1"

# Default max age for signatures (5 minutes)
DEFAULT_MAX_AGE = 300


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails.

    Attributes:
        reason: Human-readable reason for failure
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def verify(
    payload: bytes,
    signature: str,
    secret: str,
    max_age: int = DEFAULT_MAX_AGE,
) -> bool:
    """Verify a Consoul webhook signature.

    This is the primary function for webhook verification. It validates
    the HMAC-SHA256 signature and checks for replay attacks.

    Args:
        payload: Raw request body bytes (must be exact bytes received)
        signature: Value of X-Consoul-Signature header
        secret: Your webhook secret
        max_age: Maximum age of signature in seconds (default: 300)

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> body = b'{"id": "evt_abc123", "type": "chat.completed", ...}'
        >>> sig = "t=1735689600,v1=a1b2c3d4e5f6..."
        >>> secret = "whsec_your_secret_here"
        >>> verify(body, sig, secret)
        True

    Notes:
        - Always use the raw request body, not parsed JSON
        - The signature header is case-insensitive
        - Signatures expire after max_age seconds (default 5 minutes)
    """
    try:
        return verify_with_timestamp(payload, signature, secret, max_age)[0]
    except WebhookVerificationError:
        return False


def verify_with_timestamp(
    payload: bytes,
    signature: str,
    secret: str | Sequence[str],
    max_age: int = DEFAULT_MAX_AGE,
) -> tuple[bool, int]:
    """Verify signature and return timestamp.

    Extended verification that returns the signature timestamp, useful
    for logging or additional validation.

    Args:
        payload: Raw request body bytes
        signature: Value of X-Consoul-Signature header
        secret: Your webhook secret (or list of secrets for rotation)
        max_age: Maximum age of signature in seconds

    Returns:
        Tuple of (is_valid, timestamp)

    Raises:
        WebhookVerificationError: If signature format is invalid or expired

    Example:
        >>> try:
        ...     valid, timestamp = verify_with_timestamp(body, sig, secret)
        ...     print(f"Signed at: {timestamp}, valid: {valid}")
        ... except WebhookVerificationError as e:
        ...     print(f"Verification failed: {e.reason}")
    """
    # Normalize secrets to list
    secrets: list[str] = [secret] if isinstance(secret, str) else list(secret)

    if not secrets:
        raise WebhookVerificationError("No secrets provided")

    if not signature:
        raise WebhookVerificationError("Missing signature")

    # Parse signature components
    parts: dict[str, str] = {}
    for part in signature.split(","):
        if "=" not in part:
            raise WebhookVerificationError(f"Invalid signature format: {part}")
        key, value = part.split("=", 1)
        parts[key.strip()] = value.strip()

    # Extract timestamp
    if "t" not in parts:
        raise WebhookVerificationError("Missing timestamp in signature")

    try:
        timestamp = int(parts["t"])
    except ValueError as e:
        raise WebhookVerificationError(f"Invalid timestamp: {parts['t']}") from e

    # Extract signature
    if _SIGNATURE_VERSION not in parts:
        raise WebhookVerificationError(f"Missing {_SIGNATURE_VERSION} in signature")

    provided_sig = parts[_SIGNATURE_VERSION]

    # Check timestamp freshness
    current_time = int(time.time())
    age = current_time - timestamp

    if age < -60:  # 1 minute clock skew tolerance
        raise WebhookVerificationError("Signature timestamp is in the future")

    if age > max_age:
        raise WebhookVerificationError(
            f"Signature expired: {age}s old (max: {max_age}s)"
        )

    # Construct expected signature
    signing_string = f"{timestamp}.{payload.decode('utf-8')}"

    # Try each secret
    for sec in secrets:
        expected_sig = hmac.new(
            key=sec.encode("utf-8"),
            msg=signing_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        if hmac.compare_digest(expected_sig, provided_sig):
            return True, timestamp

    return False, timestamp
