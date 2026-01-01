"""HMAC-SHA256 signature generation and verification for webhooks.

Provides secure webhook signing following industry best practices:
- Timestamp-based replay protection
- Timing-safe comparison
- Multiple secret support for rotation

Signature Format:
    X-Consoul-Signature: t=1735689600,v1=abc123def456...

The signature is computed as:
    HMAC-SHA256(secret, "{timestamp}.{raw_payload}")

Example:
    >>> from consoul.server.webhooks.signature import sign_payload, verify_signature
    >>> import time
    >>>
    >>> secret = "whsec_test_secret_key"
    >>> payload = b'{"id": "evt_123", "type": "chat.completed"}'
    >>> timestamp = int(time.time())
    >>>
    >>> signature = sign_payload(payload, secret, timestamp)
    >>> print(signature)
    't=1735689600,v1=a1b2c3d4...'
    >>>
    >>> verify_signature(payload, signature, [secret])
    True
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
    "SignatureError",
    "parse_signature",
    "sign_payload",
    "verify_signature",
]

# Header name for webhook signatures
SIGNATURE_HEADER = "X-Consoul-Signature"

# Current signature version
SIGNATURE_VERSION = "v1"


class SignatureError(Exception):
    """Error during signature verification."""

    pass


def sign_payload(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: Raw request body bytes
        secret: Webhook secret for signing
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Signature string in format: t={timestamp},v1={hex_signature}

    Example:
        >>> sign_payload(b'{"id": "evt_123"}', "whsec_abc123", 1735689600)
        't=1735689600,v1=...'
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Construct signing string: "{timestamp}.{payload}"
    signing_string = f"{timestamp}.{payload.decode('utf-8')}"

    # Compute HMAC-SHA256
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=signing_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return f"t={timestamp},{SIGNATURE_VERSION}={signature}"


def parse_signature(signature: str) -> tuple[int, str]:
    """Parse signature header into components.

    Args:
        signature: Signature string (e.g., "t=1735689600,v1=abc123...")

    Returns:
        Tuple of (timestamp, hex_signature)

    Raises:
        SignatureError: If signature format is invalid
    """
    parts: dict[str, str] = {}

    for part in signature.split(","):
        if "=" not in part:
            raise SignatureError(f"Invalid signature part: {part}")
        key, value = part.split("=", 1)
        parts[key.strip()] = value.strip()

    if "t" not in parts:
        raise SignatureError("Missing timestamp in signature")

    if SIGNATURE_VERSION not in parts:
        raise SignatureError(f"Missing {SIGNATURE_VERSION} signature")

    try:
        timestamp = int(parts["t"])
    except ValueError as e:
        raise SignatureError(f"Invalid timestamp: {parts['t']}") from e

    return timestamp, parts[SIGNATURE_VERSION]


def verify_signature(
    payload: bytes,
    signature: str,
    secrets: Sequence[str],
    max_age_seconds: int = 300,
) -> bool:
    """Verify webhook signature with replay protection.

    Args:
        payload: Raw request body bytes
        signature: Signature header value
        secrets: List of valid secrets (supports rotation)
        max_age_seconds: Maximum age of signature in seconds (default: 5 minutes)

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SignatureError: If signature format is invalid or timestamp expired

    Example:
        >>> payload = b'{"id": "evt_123"}'
        >>> signature = "t=1735689600,v1=abc123..."
        >>> secrets = ["whsec_current", "whsec_previous"]
        >>> verify_signature(payload, signature, secrets)
        True

    Security Notes:
        - Uses timing-safe comparison to prevent timing attacks
        - Enforces timestamp to prevent replay attacks
        - Supports multiple secrets for zero-downtime rotation
    """
    if not secrets:
        raise SignatureError("No secrets provided for verification")

    # Parse signature
    try:
        timestamp, provided_signature = parse_signature(signature)
    except SignatureError:
        return False

    # Check timestamp freshness (replay protection)
    current_time = int(time.time())
    age = current_time - timestamp

    if age < 0:
        # Signature from the future - clock skew tolerance
        if abs(age) > 60:  # Allow 1 minute clock skew
            raise SignatureError("Signature timestamp is in the future")
    elif age > max_age_seconds:
        raise SignatureError(f"Signature expired: {age}s old (max: {max_age_seconds}s)")

    # Construct signing string
    signing_string = f"{timestamp}.{payload.decode('utf-8')}"

    # Try each secret (supports rotation)
    for secret in secrets:
        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=signing_string.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        if hmac.compare_digest(expected_signature, provided_signature):
            return True

    return False


def compute_signature(payload: bytes, secret: str, timestamp: int) -> str:
    """Compute raw HMAC-SHA256 signature (internal use).

    Args:
        payload: Raw request body bytes
        secret: Webhook secret
        timestamp: Unix timestamp

    Returns:
        Hex-encoded signature string
    """
    signing_string = f"{timestamp}.{payload.decode('utf-8')}"
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=signing_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
