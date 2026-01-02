"""Tests for Ollama context cache.

Tests for SOUL-353: Guard Ollama context cache against invalid timestamps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from consoul.ai.context_cache import OllamaContextCache


@pytest.fixture
def cache(tmp_path):
    """Create a cache instance with a temporary directory."""
    return OllamaContextCache(cache_dir=tmp_path)


class TestOllamaContextCacheGet:
    """Tests for OllamaContextCache.get() method."""

    def test_get_returns_none_for_missing_model(self, cache):
        """get() returns None when model is not in cache."""
        assert cache.get("nonexistent-model") is None

    def test_get_returns_context_size_for_valid_entry(self, cache):
        """get() returns context size for valid cache entry."""
        cache.set("llama3.2:latest", 8192)
        assert cache.get("llama3.2:latest") == 8192

    def test_get_returns_none_for_missing_cached_at(self, cache):
        """get() returns None when cached_at is missing (SOUL-353)."""
        with cache._lock:
            cache._cache["test-model"] = {"context_size": 4096}
        assert cache.get("test-model") is None

    def test_get_returns_none_for_empty_cached_at(self, cache):
        """get() returns None when cached_at is empty string (SOUL-353)."""
        with cache._lock:
            cache._cache["test-model"] = {"context_size": 4096, "cached_at": ""}
        assert cache.get("test-model") is None

    def test_get_returns_none_for_malformed_cached_at(self, cache):
        """get() returns None when cached_at is malformed (SOUL-353)."""
        with cache._lock:
            cache._cache["test-model"] = {
                "context_size": 4096,
                "cached_at": "not-a-valid-date",
            }
        assert cache.get("test-model") is None

    def test_get_returns_none_for_numeric_cached_at(self, cache):
        """get() returns None when cached_at is wrong type (SOUL-353)."""
        with cache._lock:
            cache._cache["test-model"] = {
                "context_size": 4096,
                "cached_at": 12345,  # Wrong type
            }
        assert cache.get("test-model") is None

    def test_get_returns_none_for_stale_entry(self, cache):
        """get() returns None for entries older than 7 days."""
        stale_date = datetime.now(timezone.utc) - timedelta(days=8)
        with cache._lock:
            cache._cache["test-model"] = {
                "context_size": 4096,
                "cached_at": stale_date.isoformat(),
            }
        assert cache.get("test-model") is None

    def test_get_returns_context_size_for_fresh_entry(self, cache):
        """get() returns context size for entries within 7 days."""
        fresh_date = datetime.now(timezone.utc) - timedelta(days=6)
        with cache._lock:
            cache._cache["test-model"] = {
                "context_size": 4096,
                "cached_at": fresh_date.isoformat(),
            }
        assert cache.get("test-model") == 4096


class TestOllamaContextCacheGetAll:
    """Tests for OllamaContextCache.get_all() method."""

    def test_get_all_skips_invalid_cached_at(self, cache):
        """get_all() skips entries with invalid cached_at."""
        cache.set("valid-model", 8192)
        with cache._lock:
            cache._cache["invalid-model"] = {
                "context_size": 4096,
                "cached_at": "invalid",
            }
        result = cache.get_all()
        assert "valid-model" in result
        assert "invalid-model" not in result
