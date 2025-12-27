"""Tests for session ID utilities."""

from __future__ import annotations

import pytest

from consoul.sdk.session_id import (
    ParsedSessionId,
    SessionIdBuilder,
    build_session_id,
    generate_session_id,
    is_namespaced,
    parse_session_id,
)


class TestGenerateSessionId:
    """Test generate_session_id function."""

    def test_default_length(self) -> None:
        """Default length is 12 characters."""
        session_id = generate_session_id()
        assert len(session_id) == 12

    def test_custom_length(self) -> None:
        """Custom length is respected."""
        session_id = generate_session_id(length=24)
        assert len(session_id) == 24

    def test_with_prefix(self) -> None:
        """Prefix is prepended to ID."""
        session_id = generate_session_id(prefix="sess_")
        assert session_id.startswith("sess_")
        assert len(session_id) == 5 + 12  # prefix + random

    def test_uniqueness(self) -> None:
        """Generated IDs are unique."""
        ids = {generate_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_hex_characters(self) -> None:
        """Generated IDs contain only hex characters."""
        session_id = generate_session_id()
        assert all(c in "0123456789abcdef" for c in session_id)


class TestSessionIdBuilder:
    """Test SessionIdBuilder fluent API."""

    def test_session_only(self) -> None:
        """Build with session ID only."""
        session_id = SessionIdBuilder().session("conv123").build()
        assert session_id == "conv123"

    def test_user_and_session(self) -> None:
        """Build with user and session."""
        session_id = SessionIdBuilder().user("alice").session("conv123").build()
        assert session_id == "alice:conv123"

    def test_tenant_user_session(self) -> None:
        """Build with tenant, user, and session."""
        session_id = (
            SessionIdBuilder().tenant("acme").user("alice").session("conv123").build()
        )
        assert session_id == "acme:alice:conv123"

    def test_custom_separator(self) -> None:
        """Custom separator is used."""
        session_id = (
            SessionIdBuilder(separator="/")
            .tenant("org")
            .user("bob")
            .session("chat")
            .build()
        )
        assert session_id == "org/bob/chat"

    def test_auto_generate_session(self) -> None:
        """Auto-generates session ID when None passed."""
        session_id = SessionIdBuilder().user("alice").session().build()
        assert session_id.startswith("alice:")
        assert len(session_id) > 7  # "alice:" + at least 1 char

    def test_requires_session(self) -> None:
        """Raises ValueError if session not set."""
        with pytest.raises(ValueError, match="Session ID must be set"):
            SessionIdBuilder().user("alice").build()

    def test_url_encoding_separator_in_values(self) -> None:
        """URL-encodes separator characters in values."""
        session_id = (
            SessionIdBuilder()
            .tenant("acme:corp")  # Contains separator
            .user("alice:bob")  # Contains separator
            .session("conv123")
            .build()
        )
        # Values should be URL-encoded
        assert "acme%3Acorp" in session_id
        assert "alice%3Abob" in session_id


class TestBuildSessionId:
    """Test build_session_id convenience function."""

    def test_session_only(self) -> None:
        """Build with explicit session ID."""
        result = build_session_id("conv123")
        assert result == "conv123"

    def test_auto_generate(self) -> None:
        """Auto-generates session ID when not provided."""
        result = build_session_id()
        assert len(result) == 12  # Default generate_session_id length

    def test_user_namespace(self) -> None:
        """Adds user namespace."""
        result = build_session_id("conv123", user_id="alice")
        assert result == "alice:conv123"

    def test_tenant_namespace(self) -> None:
        """Adds tenant and user namespace."""
        result = build_session_id("conv123", user_id="alice", tenant_id="acme")
        assert result == "acme:alice:conv123"

    def test_prevents_double_namespacing(self) -> None:
        """Already-namespaced IDs returned as-is."""
        # 2-part (user:session) - already namespaced
        result = build_session_id("alice:conv123", user_id="alice")
        assert result == "alice:conv123"

        # 3-part (tenant:user:session) - already namespaced
        result = build_session_id(
            "acme:alice:conv123", user_id="alice", tenant_id="acme"
        )
        assert result == "acme:alice:conv123"

    def test_url_encoding_round_trip(self) -> None:
        """Values with separator round-trip correctly."""
        # Build with separator in values
        built = build_session_id(
            "conv123",
            user_id="alice:bob",
            tenant_id="acme:corp",
        )

        # Parse back
        parsed = parse_session_id(built)

        assert parsed.tenant_id == "acme:corp"
        assert parsed.user_id == "alice:bob"
        assert parsed.session_id == "conv123"


class TestIsNamespaced:
    """Test is_namespaced function."""

    def test_single_part(self) -> None:
        """Single part is not namespaced."""
        assert is_namespaced("conv123") is False

    def test_two_parts(self) -> None:
        """Two parts is namespaced (user:session)."""
        assert is_namespaced("alice:conv123") is True

    def test_three_parts(self) -> None:
        """Three parts is namespaced (tenant:user:session)."""
        assert is_namespaced("acme:alice:conv123") is True

    def test_four_plus_parts(self) -> None:
        """Four or more parts is not considered namespaced."""
        assert is_namespaced("a:b:c:d") is False

    def test_custom_separator(self) -> None:
        """Respects custom separator."""
        assert is_namespaced("alice/conv123", separator="/") is True
        assert is_namespaced("alice:conv123", separator="/") is False


class TestParseSessionId:
    """Test parse_session_id function."""

    def test_single_part(self) -> None:
        """Parse session-only ID."""
        result = parse_session_id("conv123")

        assert result.full_id == "conv123"
        assert result.tenant_id is None
        assert result.user_id is None
        assert result.session_id == "conv123"

    def test_two_parts(self) -> None:
        """Parse user:session ID."""
        result = parse_session_id("alice:conv123")

        assert result.full_id == "alice:conv123"
        assert result.tenant_id is None
        assert result.user_id == "alice"
        assert result.session_id == "conv123"

    def test_three_parts(self) -> None:
        """Parse tenant:user:session ID."""
        result = parse_session_id("acme:alice:conv123")

        assert result.full_id == "acme:alice:conv123"
        assert result.tenant_id == "acme"
        assert result.user_id == "alice"
        assert result.session_id == "conv123"

    def test_url_decoding(self) -> None:
        """URL-decodes components."""
        # Tenant was "acme:corp", user was "alice:bob"
        result = parse_session_id("acme%3Acorp:alice%3Abob:conv123")

        assert result.tenant_id == "acme:corp"
        assert result.user_id == "alice:bob"
        assert result.session_id == "conv123"

    def test_expected_parts_validation(self) -> None:
        """Validates expected_parts when provided."""
        # Should work
        result = parse_session_id("alice:conv123", expected_parts=2)
        assert result.user_id == "alice"

        # Should fail
        with pytest.raises(ValueError, match="Expected 3 parts"):
            parse_session_id("alice:conv123", expected_parts=3)

    def test_four_plus_parts_error(self) -> None:
        """Four or more parts raises error."""
        with pytest.raises(ValueError, match="has 4 parts"):
            parse_session_id("a:b:c:d")

    def test_custom_separator(self) -> None:
        """Respects custom separator."""
        result = parse_session_id("alice/conv123", separator="/")

        assert result.user_id == "alice"
        assert result.session_id == "conv123"


class TestParsedSessionId:
    """Test ParsedSessionId dataclass."""

    def test_dataclass_fields(self) -> None:
        """ParsedSessionId has correct fields."""
        parsed = ParsedSessionId(
            full_id="acme:alice:conv123",
            tenant_id="acme",
            user_id="alice",
            session_id="conv123",
        )

        assert parsed.full_id == "acme:alice:conv123"
        assert parsed.tenant_id == "acme"
        assert parsed.user_id == "alice"
        assert parsed.session_id == "conv123"

    def test_equality(self) -> None:
        """ParsedSessionId equality works."""
        p1 = ParsedSessionId("a:b", None, "a", "b")
        p2 = ParsedSessionId("a:b", None, "a", "b")
        p3 = ParsedSessionId("x:y", None, "x", "y")

        assert p1 == p2
        assert p1 != p3


class TestBuildParseRoundTrip:
    """Test round-trip between build and parse."""

    @pytest.mark.parametrize(
        "tenant_id,user_id,session_id",
        [
            (None, None, "simple"),
            (None, "alice", "conv123"),
            ("acme", "alice", "conv123"),
            ("acme:corp", "alice:bob", "conv:123"),  # With separators
            ("multi:part:tenant", "user", "session"),  # Multiple separators
        ],
    )
    def test_round_trip(
        self,
        tenant_id: str | None,
        user_id: str | None,
        session_id: str,
    ) -> None:
        """Build then parse preserves all components."""
        built = build_session_id(
            session_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )
        parsed = parse_session_id(built)

        assert parsed.tenant_id == tenant_id
        assert parsed.user_id == user_id
        assert parsed.session_id == session_id
