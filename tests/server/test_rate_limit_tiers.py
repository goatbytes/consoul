"""Tests for per-API-key rate limit tiers (SOUL-331).

Tests the tiered rate limiting feature that allows different rate limits
based on API key patterns (e.g., premium vs basic customers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from consoul.server.middleware.rate_limit import create_tiered_limit_func
from consoul.server.models import RateLimitConfig, parse_json_dict

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# =============================================================================
# parse_json_dict Validator Tests
# =============================================================================


class TestParseJsonDict:
    """Tests for the parse_json_dict validator function."""

    def test_none_passthrough(self):
        """None input returns None."""
        assert parse_json_dict(None) is None

    def test_dict_passthrough(self):
        """Dict input is passed through with string conversion."""
        result = parse_json_dict({"tier": "100/minute"})
        assert result == {"tier": "100/minute"}

    def test_dict_with_non_string_values(self):
        """Dict values are converted to strings."""
        result = parse_json_dict({"key": 100})
        assert result == {"key": "100"}

    def test_valid_json_string(self):
        """Valid JSON string is parsed."""
        result = parse_json_dict('{"premium": "100/minute", "basic": "30/minute"}')
        assert result == {"premium": "100/minute", "basic": "30/minute"}

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert parse_json_dict("") is None
        assert parse_json_dict("   ") is None

    def test_malformed_json_raises(self):
        """Malformed JSON raises ValueError."""
        with pytest.raises(ValueError, match="Malformed JSON"):
            parse_json_dict('{"key": "value"')  # Missing }

    def test_json_array_raises(self):
        """JSON array (not object) raises ValueError."""
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_json_dict('["item1", "item2"]')

    def test_json_number_raises(self):
        """JSON primitive (not object) raises ValueError."""
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_json_dict("123")

    def test_json_string_raises(self):
        """JSON string (not object) raises ValueError."""
        with pytest.raises(ValueError, match="Expected JSON object"):
            parse_json_dict('"just a string"')

    def test_complex_nested_json(self):
        """Complex nested JSON values are converted to strings."""
        # Note: nested objects become string representations
        result = parse_json_dict('{"key": "value", "number": "42"}')
        assert result == {"key": "value", "number": "42"}


# =============================================================================
# RateLimitConfig Tier Fields Tests
# =============================================================================


class TestRateLimitConfigTiers:
    """Tests for RateLimitConfig tier configuration fields."""

    def test_tier_limits_from_env_json(self, monkeypatch: MonkeyPatch):
        """tier_limits parses JSON from environment variable."""
        monkeypatch.setenv(
            "CONSOUL_RATE_LIMIT_TIERS",
            '{"premium": "100/minute", "basic": "30/minute"}',
        )
        config = RateLimitConfig()
        assert config.tier_limits == {"premium": "100/minute", "basic": "30/minute"}

    def test_api_key_tiers_from_env_json(self, monkeypatch: MonkeyPatch):
        """api_key_tiers parses JSON from environment variable."""
        monkeypatch.setenv(
            "CONSOUL_API_KEY_TIERS",
            '{"sk-premium-*": "premium", "sk-basic-*": "basic"}',
        )
        config = RateLimitConfig()
        assert config.api_key_tiers == {
            "sk-premium-*": "premium",
            "sk-basic-*": "basic",
        }

    def test_tier_limits_malformed_json_raises(self, monkeypatch: MonkeyPatch):
        """Malformed JSON in CONSOUL_RATE_LIMIT_TIERS raises ValidationError."""
        monkeypatch.setenv("CONSOUL_RATE_LIMIT_TIERS", '{"premium": "100/minute"')
        with pytest.raises(ValidationError):
            RateLimitConfig()

    def test_api_key_tiers_malformed_json_raises(self, monkeypatch: MonkeyPatch):
        """Malformed JSON in CONSOUL_API_KEY_TIERS raises ValidationError."""
        monkeypatch.setenv("CONSOUL_API_KEY_TIERS", '{"sk-*": "tier"')
        with pytest.raises(ValidationError):
            RateLimitConfig()

    def test_tier_limits_default_none(self):
        """tier_limits defaults to None when not configured."""
        config = RateLimitConfig()
        assert config.tier_limits is None

    def test_api_key_tiers_default_none(self):
        """api_key_tiers defaults to None when not configured."""
        config = RateLimitConfig()
        assert config.api_key_tiers is None

    def test_backward_compatibility_no_tiers(self):
        """Existing behavior preserved when tiers not configured."""
        config = RateLimitConfig()
        assert config.enabled is True
        assert config.default_limits == ["10 per minute"]
        assert config.tier_limits is None
        assert config.api_key_tiers is None

    def test_tier_limits_with_dict(self):
        """tier_limits accepts dict directly."""
        config = RateLimitConfig(tier_limits={"premium": "100/minute"})
        assert config.tier_limits == {"premium": "100/minute"}

    def test_api_key_tiers_with_dict(self):
        """api_key_tiers accepts dict directly."""
        config = RateLimitConfig(api_key_tiers={"sk-*": "default"})
        assert config.api_key_tiers == {"sk-*": "default"}


# =============================================================================
# create_tiered_limit_func Tests
# =============================================================================


class MockRequest:
    """Mock request for testing rate limit functions."""

    def __init__(self, api_key: str | None = None, header_name: str = "X-API-Key"):
        self.headers = {header_name: api_key} if api_key else {}
        self.state = MagicMock()


class TestCreateTieredLimitFunc:
    """Tests for the tiered limit function factory."""

    def test_premium_key_gets_premium_limit(self):
        """API key matching premium pattern gets premium limit."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute", "basic": "30/minute"},
            api_key_tiers={"sk-premium-*": "premium", "sk-basic-*": "basic"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-premium-abc123")
        result = limit_func(request)
        assert result == "100/minute"
        assert request.state.rate_limit_tier == "premium"

    def test_basic_key_gets_basic_limit(self):
        """API key matching basic pattern gets basic limit."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute", "basic": "30/minute"},
            api_key_tiers={"sk-premium-*": "premium", "sk-basic-*": "basic"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-basic-xyz789")
        result = limit_func(request)
        assert result == "30/minute"
        assert request.state.rate_limit_tier == "basic"

    def test_unknown_key_gets_default_limit(self):
        """API key matching no pattern gets default limit."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute"},
            api_key_tiers={"sk-premium-*": "premium"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-unknown-123")
        result = limit_func(request)
        assert result == "10/minute"
        assert request.state.rate_limit_tier == "default"

    def test_missing_api_key_uses_default(self):
        """Request without API key header uses default limit."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute"},
            api_key_tiers={"sk-premium-*": "premium"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key=None)
        result = limit_func(request)
        assert result == "10/minute"
        assert request.state.rate_limit_tier == "default"

    def test_empty_api_key_uses_default(self):
        """Request with empty API key uses default limit."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute"},
            api_key_tiers={"sk-premium-*": "premium"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="")
        result = limit_func(request)
        assert result == "10/minute"

    def test_missing_tier_in_tier_limits_uses_default(self):
        """Missing tier in tier_limits falls back to default with warning."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute"},  # Missing "basic" tier
            api_key_tiers={"sk-basic-*": "basic"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-basic-abc")
        result = limit_func(request)
        assert result == "10/minute"
        assert "missing" in request.state.rate_limit_tier

    def test_wildcard_suffix_pattern(self):
        """Suffix wildcard pattern works."""
        limit_func = create_tiered_limit_func(
            tier_limits={"enterprise": "1000/minute"},
            api_key_tiers={"*-enterprise": "enterprise"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-abc-enterprise")
        result = limit_func(request)
        assert result == "1000/minute"

    def test_wildcard_prefix_pattern(self):
        """Prefix wildcard pattern works."""
        limit_func = create_tiered_limit_func(
            tier_limits={"special": "500/minute"},
            api_key_tiers={"special-*": "special"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="special-key-123")
        result = limit_func(request)
        assert result == "500/minute"

    def test_wildcard_middle_pattern(self):
        """Middle wildcard pattern works."""
        limit_func = create_tiered_limit_func(
            tier_limits={"enterprise": "1000/minute"},
            api_key_tiers={"sk-*-enterprise-*": "enterprise"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-abc-enterprise-xyz")
        result = limit_func(request)
        assert result == "1000/minute"

    def test_exact_match_pattern(self):
        """Exact match (no wildcards) works."""
        limit_func = create_tiered_limit_func(
            tier_limits={"admin": "unlimited"},
            api_key_tiers={"admin-master-key": "admin"},
            default_limit="10/minute",
        )

        request = MockRequest(api_key="admin-master-key")
        result = limit_func(request)
        assert result == "unlimited"

        # Different key should not match
        request2 = MockRequest(api_key="admin-master-key-extra")
        result2 = limit_func(request2)
        assert result2 == "10/minute"

    def test_first_pattern_wins(self):
        """First matching pattern is used (order matters)."""
        limit_func = create_tiered_limit_func(
            tier_limits={"a": "100/minute", "b": "50/minute"},
            api_key_tiers={
                "sk-*": "a",  # Matches first
                "sk-special-*": "b",  # Would also match, but comes second
            },
            default_limit="10/minute",
        )

        request = MockRequest(api_key="sk-special-key")
        result = limit_func(request)
        assert result == "100/minute"  # First pattern wins

    def test_custom_header_name(self):
        """Custom header name is used for API key extraction."""
        limit_func = create_tiered_limit_func(
            tier_limits={"premium": "100/minute"},
            api_key_tiers={"premium-*": "premium"},
            default_limit="10/minute",
            header_name="Authorization",
        )

        # With custom header
        request = MockRequest(api_key="premium-token", header_name="Authorization")
        result = limit_func(request)
        assert result == "100/minute"

        # Without custom header (wrong header name)
        request2 = MockRequest(api_key="premium-token", header_name="X-API-Key")
        result2 = limit_func(request2)
        assert result2 == "10/minute"  # Falls back to default

    def test_question_mark_wildcard(self):
        """Question mark matches single character."""
        limit_func = create_tiered_limit_func(
            tier_limits={"tier1": "100/minute"},
            api_key_tiers={"sk-?": "tier1"},  # Matches sk-X where X is single char
            default_limit="10/minute",
        )

        request1 = MockRequest(api_key="sk-a")
        assert limit_func(request1) == "100/minute"

        request2 = MockRequest(api_key="sk-ab")  # Two chars, doesn't match
        assert limit_func(request2) == "10/minute"

    def test_multiple_tiers(self):
        """Multiple tiers with multiple patterns work correctly."""
        limit_func = create_tiered_limit_func(
            tier_limits={
                "enterprise": "1000/minute",
                "premium": "100/minute",
                "basic": "30/minute",
                "trial": "5/minute",
            },
            api_key_tiers={
                "sk-enterprise-*": "enterprise",
                "sk-premium-*": "premium",
                "sk-basic-*": "basic",
                "sk-trial-*": "trial",
            },
            default_limit="10/minute",
        )

        # Test each tier
        assert limit_func(MockRequest(api_key="sk-enterprise-123")) == "1000/minute"
        assert limit_func(MockRequest(api_key="sk-premium-456")) == "100/minute"
        assert limit_func(MockRequest(api_key="sk-basic-789")) == "30/minute"
        assert limit_func(MockRequest(api_key="sk-trial-abc")) == "5/minute"
        assert limit_func(MockRequest(api_key="sk-unknown-xyz")) == "10/minute"


# =============================================================================
# Integration Tests
# =============================================================================


class TestTieredRateLimitingIntegration:
    """Integration tests for tiered rate limiting with server configuration."""

    def test_config_with_both_tier_settings(self, monkeypatch: MonkeyPatch):
        """Server config with both tier settings loads correctly."""
        monkeypatch.setenv(
            "CONSOUL_RATE_LIMIT_TIERS",
            '{"premium": "100/minute", "basic": "30/minute"}',
        )
        monkeypatch.setenv(
            "CONSOUL_API_KEY_TIERS",
            '{"sk-premium-*": "premium", "sk-basic-*": "basic"}',
        )

        config = RateLimitConfig()
        assert config.tier_limits is not None
        assert config.api_key_tiers is not None
        assert "premium" in config.tier_limits
        assert "sk-premium-*" in config.api_key_tiers

    def test_config_partial_tier_settings(self, monkeypatch: MonkeyPatch):
        """Partial tier settings (only one set) loads without error."""
        monkeypatch.setenv(
            "CONSOUL_RATE_LIMIT_TIERS",
            '{"premium": "100/minute"}',
        )
        # api_key_tiers not set

        config = RateLimitConfig()
        assert config.tier_limits == {"premium": "100/minute"}
        assert config.api_key_tiers is None

    def test_config_preserves_other_settings(self, monkeypatch: MonkeyPatch):
        """Tier settings don't affect other rate limit settings."""
        monkeypatch.setenv("CONSOUL_ENABLED", "true")
        monkeypatch.setenv("CONSOUL_DEFAULT_LIMITS", "50/minute")
        monkeypatch.setenv(
            "CONSOUL_RATE_LIMIT_TIERS",
            '{"premium": "100/minute"}',
        )

        config = RateLimitConfig()
        assert config.enabled is True
        assert config.default_limits == ["50/minute"]
        assert config.tier_limits == {"premium": "100/minute"}


# =============================================================================
# Factory Integration Tests - Per-API-Key Bucketing
# =============================================================================


class TestFactoryPerApiKeyBucketing:
    """Tests that the factory configures per-API-key bucketing when tiers are enabled."""

    def test_limiter_uses_api_key_bucketing_when_tiers_configured(
        self, monkeypatch: MonkeyPatch
    ):
        """Limiter uses API key (not IP) for bucketing when tiers are configured."""
        from consoul.server import create_server
        from consoul.server.models import RateLimitConfig, SecurityConfig, ServerConfig

        config = ServerConfig(
            security=SecurityConfig(api_keys=["sk-premium-key", "sk-basic-key"]),
            rate_limit=RateLimitConfig(
                tier_limits={"premium": "100/minute", "basic": "30/minute"},
                api_key_tiers={"sk-premium-*": "premium", "sk-basic-*": "basic"},
            ),
        )
        app = create_server(config)

        # Verify limiter uses custom key function (not default IP-based)
        limiter = app.state.limiter
        assert limiter.key_func is not None
        # The key_func should NOT be get_remote_address when tiers are configured
        from slowapi.util import get_remote_address

        assert limiter.key_func != get_remote_address

    def test_limiter_uses_ip_bucketing_without_tiers(self):
        """Limiter uses IP-based bucketing when tiers are NOT configured."""
        from consoul.server import create_server
        from consoul.server.models import RateLimitConfig, ServerConfig

        config = ServerConfig(
            rate_limit=RateLimitConfig(default_limits=["30/minute"]),
        )
        app = create_server(config)

        # Verify limiter uses default key function (IP-based)
        limiter = app.state.limiter
        from slowapi.util import get_remote_address

        assert limiter.key_func == get_remote_address

    def test_api_key_bucket_function_extracts_key(self, monkeypatch: MonkeyPatch):
        """Per-API-key bucket function correctly extracts API key from header."""
        from consoul.server import create_server
        from consoul.server.models import RateLimitConfig, SecurityConfig, ServerConfig

        config = ServerConfig(
            security=SecurityConfig(
                api_keys=["sk-premium-key"], header_name="X-API-Key"
            ),
            rate_limit=RateLimitConfig(
                tier_limits={"premium": "100/minute"},
                api_key_tiers={"sk-premium-*": "premium"},
            ),
        )
        app = create_server(config)

        limiter = app.state.limiter

        # Create mock request with API key
        request = MockRequest(api_key="sk-premium-abc123")
        bucket_key = limiter.key_func(request)
        assert bucket_key == "sk-premium-abc123"

    def test_api_key_bucket_function_falls_back_to_ip(self, monkeypatch: MonkeyPatch):
        """Per-API-key bucket function falls back to IP when no API key."""
        from consoul.server import create_server
        from consoul.server.models import RateLimitConfig, SecurityConfig, ServerConfig

        config = ServerConfig(
            security=SecurityConfig(
                api_keys=["sk-premium-key"], header_name="X-API-Key"
            ),
            rate_limit=RateLimitConfig(
                tier_limits={"premium": "100/minute"},
                api_key_tiers={"sk-premium-*": "premium"},
            ),
        )
        app = create_server(config)

        limiter = app.state.limiter

        # Create mock request WITHOUT API key
        request = MockRequest(api_key=None)
        # Add mock for get_remote_address to return an IP
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        bucket_key = limiter.key_func(request)
        # Should fall back to IP address
        assert bucket_key == "192.168.1.100"
