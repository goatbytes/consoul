"""Tests for server configuration models and environment variable handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from consoul.server.models import (
    CORSConfig,
    RateLimitConfig,
    SecurityConfig,
    ServerConfig,
    SessionConfig,
    parse_comma_separated_list,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# =============================================================================
# JSON Parsing Tests
# =============================================================================


def test_parse_comma_separated():
    """Comma-separated values work as before."""
    assert parse_comma_separated_list("a,b,c") == ["a", "b", "c"]


def test_parse_json_array():
    """Valid JSON arrays are parsed."""
    assert parse_comma_separated_list('["a","b","c"]') == ["a", "b", "c"]


def test_parse_malformed_json_raises():
    """Malformed JSON raises ValueError, not silent fallback."""
    with pytest.raises(ValueError, match="Malformed JSON array"):
        parse_comma_separated_list('["a","b"')  # Missing ]

    with pytest.raises(ValueError, match="Malformed JSON array"):
        parse_comma_separated_list('["a",]')  # Trailing comma


def test_parse_json_object_raises():
    """JSON objects (not arrays) raise ValueError."""
    with pytest.raises(ValueError, match="Expected JSON array"):
        parse_comma_separated_list('{"key":"value"}')


def test_parse_empty_string():
    """Empty string returns empty list."""
    assert parse_comma_separated_list("") == []
    assert parse_comma_separated_list("   ") == []


def test_parse_list_passthrough():
    """List values are passed through."""
    assert parse_comma_separated_list(["a", "b", "c"]) == ["a", "b", "c"]


# =============================================================================
# SecurityConfig JSON Behavior Tests
# =============================================================================


def test_security_api_keys_json(monkeypatch: MonkeyPatch):
    """SecurityConfig accepts JSON array for api_keys."""
    monkeypatch.setenv("CONSOUL_API_KEYS", '["key1","key2"]')
    config = SecurityConfig()
    assert config.api_keys == ["key1", "key2"]


def test_security_api_keys_malformed_json_raises(monkeypatch: MonkeyPatch):
    """Malformed JSON in CONSOUL_API_KEYS raises ValidationError."""
    monkeypatch.setenv("CONSOUL_API_KEYS", '["key1"')
    with pytest.raises(ValidationError):
        SecurityConfig()


def test_security_bypass_paths_json(monkeypatch: MonkeyPatch):
    """SecurityConfig accepts JSON array for bypass_paths."""
    monkeypatch.setenv("CONSOUL_BYPASS_PATHS", '["/health","/metrics"]')
    config = SecurityConfig()
    assert config.bypass_paths == ["/health", "/metrics"]


def test_security_api_keys_comma_separated(monkeypatch: MonkeyPatch):
    """SecurityConfig accepts comma-separated api_keys."""
    monkeypatch.setenv("CONSOUL_API_KEYS", "key1,key2,key3")
    config = SecurityConfig()
    assert config.api_keys == ["key1", "key2", "key3"]


# =============================================================================
# CORS Parsing Tests
# =============================================================================


def test_cors_origins_comma_separated(monkeypatch: MonkeyPatch):
    """CORS origins parse from comma-separated env var."""
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", "https://a.com,https://b.com")
    config = CORSConfig()
    assert config.allowed_origins == ["https://a.com", "https://b.com"]


def test_cors_origins_json_array(monkeypatch: MonkeyPatch):
    """CORS origins parse from JSON array env var."""
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", '["https://a.com","https://b.com"]')
    config = CORSConfig()
    assert config.allowed_origins == ["https://a.com", "https://b.com"]


def test_cors_origins_malformed_json_raises(monkeypatch: MonkeyPatch):
    """Malformed JSON in CONSOUL_CORS_ORIGINS raises ValidationError."""
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", '["https://a.com"')  # Missing ]
    with pytest.raises(ValidationError):
        CORSConfig()


def test_cors_origins_alias(monkeypatch: MonkeyPatch):
    """CONSOUL_CORS_ALLOWED_ORIGINS alias works."""
    monkeypatch.setenv("CONSOUL_CORS_ALLOWED_ORIGINS", "https://app.com")
    config = CORSConfig()
    assert config.allowed_origins == ["https://app.com"]


def test_cors_origins_single_value(monkeypatch: MonkeyPatch):
    """Single origin value works correctly."""
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", "https://app.com")
    config = CORSConfig()
    assert config.allowed_origins == ["https://app.com"]


def test_cors_default_wildcard():
    """Default CORS origins is wildcard."""
    config = CORSConfig()
    assert config.allowed_origins == ["*"]


def test_cors_allow_methods_comma_separated(monkeypatch: MonkeyPatch):
    """CORS allow_methods parse from comma-separated env var."""
    monkeypatch.setenv("CONSOUL_CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE")
    config = CORSConfig()
    assert config.allow_methods == ["GET", "POST", "PUT", "DELETE"]


def test_cors_allow_methods_json_array(monkeypatch: MonkeyPatch):
    """CORS allow_methods parse from JSON array env var."""
    monkeypatch.setenv("CONSOUL_CORS_ALLOW_METHODS", '["GET","POST"]')
    config = CORSConfig()
    assert config.allow_methods == ["GET", "POST"]


def test_cors_allow_headers_comma_separated(monkeypatch: MonkeyPatch):
    """CORS allow_headers parse from comma-separated env var."""
    monkeypatch.setenv(
        "CONSOUL_CORS_ALLOW_HEADERS", "X-Auth,Content-Type,Authorization"
    )
    config = CORSConfig()
    assert config.allow_headers == ["X-Auth", "Content-Type", "Authorization"]


def test_cors_allow_headers_json_array(monkeypatch: MonkeyPatch):
    """CORS allow_headers parse from JSON array env var."""
    monkeypatch.setenv("CONSOUL_CORS_ALLOW_HEADERS", '["X-Auth","Content-Type"]')
    config = CORSConfig()
    assert config.allow_headers == ["X-Auth", "Content-Type"]


def test_cors_allow_credentials_from_env(monkeypatch: MonkeyPatch):
    """CORS allow_credentials can be configured from env var."""
    monkeypatch.setenv("CONSOUL_CORS_ALLOW_CREDENTIALS", "true")
    config = CORSConfig()
    assert config.allow_credentials is True


def test_cors_max_age_from_env(monkeypatch: MonkeyPatch):
    """CORS max_age can be configured from env var."""
    monkeypatch.setenv("CONSOUL_CORS_MAX_AGE", "3600")
    config = CORSConfig()
    assert config.max_age == 3600


# =============================================================================
# Session Redis URL Precedence Tests
# =============================================================================


def test_session_redis_explicit(monkeypatch: MonkeyPatch):
    """CONSOUL_SESSION_REDIS_URL is used when set."""
    monkeypatch.setenv("CONSOUL_SESSION_REDIS_URL", "redis://explicit:6379/1")
    config = SessionConfig()
    assert config.redis_url == "redis://explicit:6379/1"


def test_session_redis_universal_fallback(monkeypatch: MonkeyPatch):
    """REDIS_URL is used as fallback when CONSOUL_SESSION_REDIS_URL not set."""
    monkeypatch.delenv("CONSOUL_SESSION_REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://universal:6379/0")
    config = SessionConfig()
    assert config.redis_url == "redis://universal:6379/0"


def test_session_redis_explicit_takes_precedence(monkeypatch: MonkeyPatch):
    """CONSOUL_SESSION_REDIS_URL takes precedence over REDIS_URL."""
    monkeypatch.setenv("CONSOUL_SESSION_REDIS_URL", "redis://explicit:6379/1")
    monkeypatch.setenv("REDIS_URL", "redis://universal:6379/0")
    config = SessionConfig()
    assert config.redis_url == "redis://explicit:6379/1"


def test_session_defaults():
    """Session config uses defaults when no env vars set."""
    config = SessionConfig()
    assert config.redis_url is None
    assert config.ttl == 3600
    assert config.key_prefix == "consoul:session:"


# =============================================================================
# Rate Limit Redis URL Precedence Tests
# =============================================================================


def test_ratelimit_redis_explicit(monkeypatch: MonkeyPatch):
    """CONSOUL_RATE_LIMIT_REDIS_URL is used when set."""
    monkeypatch.setenv("CONSOUL_RATE_LIMIT_REDIS_URL", "redis://explicit:6379/0")
    config = RateLimitConfig()
    assert config.storage_url == "redis://explicit:6379/0"


def test_ratelimit_redis_universal_fallback(monkeypatch: MonkeyPatch):
    """REDIS_URL is used as fallback when CONSOUL_RATE_LIMIT_REDIS_URL not set."""
    monkeypatch.delenv("CONSOUL_RATE_LIMIT_REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://universal:6379/0")
    config = RateLimitConfig()
    assert config.storage_url == "redis://universal:6379/0"


def test_ratelimit_redis_explicit_takes_precedence(monkeypatch: MonkeyPatch):
    """CONSOUL_RATE_LIMIT_REDIS_URL takes precedence over REDIS_URL."""
    monkeypatch.setenv("CONSOUL_RATE_LIMIT_REDIS_URL", "redis://explicit:6379/0")
    monkeypatch.setenv("REDIS_URL", "redis://universal:6379/0")
    config = RateLimitConfig()
    assert config.storage_url == "redis://explicit:6379/0"


def test_ratelimit_defaults():
    """Rate limit config uses defaults when no env vars set."""
    config = RateLimitConfig()
    assert config.enabled is True
    assert config.default_limits == ["10 per minute"]
    assert config.storage_url is None
    assert config.strategy == "moving-window"
    assert config.key_prefix == "consoul:ratelimit"


# =============================================================================
# Separate Redis Instances Test
# =============================================================================


def test_separate_redis_instances(monkeypatch: MonkeyPatch):
    """Session and rate limiting can use separate Redis instances."""
    monkeypatch.setenv("CONSOUL_SESSION_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CONSOUL_RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")

    config = ServerConfig()

    assert config.session.redis_url == "redis://localhost:6379/1"
    assert config.rate_limit.storage_url == "redis://localhost:6379/0"


# =============================================================================
# ServerConfig Integration Tests
# =============================================================================


def test_server_config_from_environment(monkeypatch: MonkeyPatch):
    """ServerConfig loads all nested configs from environment."""
    monkeypatch.setenv("CONSOUL_API_KEYS", "key1,key2")
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", "https://app.com")
    monkeypatch.setenv("CONSOUL_SESSION_REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("CONSOUL_RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CONSOUL_HOST", "127.0.0.1")
    monkeypatch.setenv("CONSOUL_PORT", "9000")

    config = ServerConfig()

    assert config.security.api_keys == ["key1", "key2"]
    assert config.cors.allowed_origins == ["https://app.com"]
    assert config.session.redis_url == "redis://localhost:6379/1"
    assert config.rate_limit.storage_url == "redis://localhost:6379/0"
    assert config.host == "127.0.0.1"
    assert config.port == 9000


def test_server_config_defaults():
    """ServerConfig uses sensible defaults."""
    config = ServerConfig()

    assert config.security.api_keys == []
    assert config.cors.allowed_origins == ["*"]
    assert config.session.redis_url is None
    assert config.rate_limit.storage_url is None
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.reload is False
    assert config.app_name == "Consoul API"


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_cors_origins_whitespace_handling(monkeypatch: MonkeyPatch):
    """CORS origins handles whitespace correctly."""
    monkeypatch.setenv("CONSOUL_CORS_ORIGINS", " https://a.com , https://b.com ")
    config = CORSConfig()
    assert config.allowed_origins == ["https://a.com", "https://b.com"]


def test_security_empty_api_keys(monkeypatch: MonkeyPatch):
    """Empty CONSOUL_API_KEYS env var results in empty list."""
    monkeypatch.setenv("CONSOUL_API_KEYS", "")
    config = SecurityConfig()
    assert config.api_keys == []


def test_session_ttl_from_env(monkeypatch: MonkeyPatch):
    """Session TTL can be configured from environment."""
    monkeypatch.setenv("CONSOUL_SESSION_TTL", "7200")
    config = SessionConfig()
    assert config.ttl == 7200


def test_session_key_prefix_from_env(monkeypatch: MonkeyPatch):
    """Session key prefix can be configured from environment."""
    monkeypatch.setenv("CONSOUL_SESSION_KEY_PREFIX", "myapp:session:")
    config = SessionConfig()
    assert config.key_prefix == "myapp:session:"


def test_ratelimit_enabled_from_env(monkeypatch: MonkeyPatch):
    """Rate limiting can be disabled via environment."""
    monkeypatch.setenv("CONSOUL_ENABLED", "false")
    config = RateLimitConfig()
    assert config.enabled is False


def test_ratelimit_strategy_from_env(monkeypatch: MonkeyPatch):
    """Rate limiting strategy can be configured from environment."""
    monkeypatch.setenv("CONSOUL_STRATEGY", "fixed-window")
    config = RateLimitConfig()
    assert config.strategy == "fixed-window"
