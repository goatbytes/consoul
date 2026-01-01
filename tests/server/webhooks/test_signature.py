"""Tests for webhook signature generation and verification."""

from __future__ import annotations

import time

import pytest

from consoul.server.webhooks.signature import (
    SignatureError,
    parse_signature,
    sign_payload,
    verify_signature,
)


class TestSignPayload:
    """Tests for sign_payload function."""

    def test_sign_payload_basic(self) -> None:
        """Test basic signature generation."""
        payload = b'{"id": "evt_123", "type": "chat.completed"}'
        secret = "whsec_test_secret_key"
        timestamp = 1735689600

        signature = sign_payload(payload, secret, timestamp)

        assert signature.startswith(f"t={timestamp},")
        assert ",v1=" in signature
        # Signature should be consistent
        assert sign_payload(payload, secret, timestamp) == signature

    def test_sign_payload_different_secrets(self) -> None:
        """Test that different secrets produce different signatures."""
        payload = b'{"id": "evt_123"}'
        timestamp = 1735689600

        sig1 = sign_payload(payload, "secret1", timestamp)
        sig2 = sign_payload(payload, "secret2", timestamp)

        assert sig1 != sig2

    def test_sign_payload_default_timestamp(self) -> None:
        """Test that timestamp defaults to current time."""
        payload = b'{"test": true}'
        secret = "test_secret"

        signature = sign_payload(payload, secret)
        timestamp, _ = parse_signature(signature)

        # Should be within last 5 seconds
        assert abs(time.time() - timestamp) < 5


class TestParseSignature:
    """Tests for parse_signature function."""

    def test_parse_valid_signature(self) -> None:
        """Test parsing a valid signature."""
        signature = "t=1735689600,v1=abc123def456"

        timestamp, sig = parse_signature(signature)

        assert timestamp == 1735689600
        assert sig == "abc123def456"

    def test_parse_signature_with_spaces(self) -> None:
        """Test parsing signature with spaces around values."""
        signature = "t = 1735689600 , v1 = abc123"

        timestamp, sig = parse_signature(signature)

        assert timestamp == 1735689600
        assert sig == "abc123"

    def test_parse_signature_missing_timestamp(self) -> None:
        """Test error on missing timestamp."""
        with pytest.raises(SignatureError, match="Missing timestamp"):
            parse_signature("v1=abc123")

    def test_parse_signature_missing_version(self) -> None:
        """Test error on missing v1 signature."""
        with pytest.raises(SignatureError, match="Missing v1"):
            parse_signature("t=1735689600")

    def test_parse_signature_invalid_timestamp(self) -> None:
        """Test error on invalid timestamp."""
        with pytest.raises(SignatureError, match="Invalid timestamp"):
            parse_signature("t=notanumber,v1=abc123")

    def test_parse_signature_invalid_format(self) -> None:
        """Test error on invalid format."""
        with pytest.raises(SignatureError, match="Invalid signature"):
            parse_signature("invalid")


class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_valid_signature(self) -> None:
        """Test verification of a valid signature."""
        payload = b'{"id": "evt_123", "type": "chat.completed"}'
        secret = "whsec_test_secret_key"
        timestamp = int(time.time())

        signature = sign_payload(payload, secret, timestamp)

        assert verify_signature(payload, signature, [secret]) is True

    def test_verify_invalid_signature(self) -> None:
        """Test rejection of invalid signature."""
        payload = b'{"id": "evt_123"}'
        secret = "correct_secret"
        timestamp = int(time.time())

        signature = sign_payload(payload, secret, timestamp)

        assert verify_signature(payload, signature, ["wrong_secret"]) is False

    def test_verify_multiple_secrets(self) -> None:
        """Test verification with multiple secrets (rotation support)."""
        payload = b'{"id": "evt_123"}'
        current_secret = "new_secret"
        previous_secret = "old_secret"
        timestamp = int(time.time())

        # Sign with old secret
        signature = sign_payload(payload, previous_secret, timestamp)

        # Verify with both secrets - should pass
        assert (
            verify_signature(payload, signature, [current_secret, previous_secret])
            is True
        )

    def test_verify_expired_signature(self) -> None:
        """Test rejection of expired signature."""
        payload = b'{"id": "evt_123"}'
        secret = "test_secret"
        old_timestamp = int(time.time()) - 600  # 10 minutes ago

        signature = sign_payload(payload, secret, old_timestamp)

        with pytest.raises(SignatureError, match="expired"):
            verify_signature(payload, signature, [secret], max_age_seconds=300)

    def test_verify_future_signature(self) -> None:
        """Test rejection of future signature (clock skew)."""
        payload = b'{"id": "evt_123"}'
        secret = "test_secret"
        future_timestamp = int(time.time()) + 120  # 2 minutes in future

        signature = sign_payload(payload, secret, future_timestamp)

        with pytest.raises(SignatureError, match="future"):
            verify_signature(payload, signature, [secret])

    def test_verify_empty_secrets_list(self) -> None:
        """Test error on empty secrets list."""
        payload = b'{"id": "evt_123"}'
        signature = "t=1735689600,v1=abc123"

        with pytest.raises(SignatureError, match="No secrets"):
            verify_signature(payload, signature, [])

    def test_verify_tampered_payload(self) -> None:
        """Test rejection of tampered payload."""
        original_payload = b'{"id": "evt_123"}'
        tampered_payload = b'{"id": "evt_999"}'
        secret = "test_secret"
        timestamp = int(time.time())

        signature = sign_payload(original_payload, secret, timestamp)

        assert verify_signature(tampered_payload, signature, [secret]) is False

    def test_verify_custom_max_age(self) -> None:
        """Test custom max age setting."""
        payload = b'{"id": "evt_123"}'
        secret = "test_secret"
        old_timestamp = int(time.time()) - 120  # 2 minutes ago

        signature = sign_payload(payload, secret, old_timestamp)

        # Should pass with 180 second max age
        assert (
            verify_signature(payload, signature, [secret], max_age_seconds=180) is True
        )

        # Should fail with 60 second max age
        with pytest.raises(SignatureError, match="expired"):
            verify_signature(payload, signature, [secret], max_age_seconds=60)
