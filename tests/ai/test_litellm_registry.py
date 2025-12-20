"""Tests for LiteLLM registry integration."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from consoul.ai.litellm_registry import (
    CACHE_TTL_HOURS,
    get_cache_info,
    get_litellm_context_window,
    refresh_cache,
)


@pytest.fixture
def mock_registry_data():
    """Sample LiteLLM registry data for testing."""
    return {
        "gpt-4o-2025-01-15": {
            "max_input_tokens": 128_000,
            "max_output_tokens": 16_384,
            "input_cost_per_token": 2.5e-06,
            "output_cost_per_token": 1e-05,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "openai/gpt-4.1": {
            "max_input_tokens": 1_047_576,
            "max_output_tokens": 32_768,
            "input_cost_per_token": 2e-06,
            "output_cost_per_token": 8e-06,
            "litellm_provider": "openai",
            "mode": "chat",
        },
        "anthropic/claude-3-opus-20240229": {
            "max_input_tokens": 200_000,
            "max_output_tokens": 4_096,
            "input_cost_per_token": 1.5e-05,
            "output_cost_per_token": 7.5e-05,
            "litellm_provider": "anthropic",
            "mode": "chat",
            "supports_vision": True,
        },
    }


@pytest.fixture
def mock_cache_file(tmp_path, monkeypatch):
    """Mock cache file location to use temp directory."""
    cache_dir = tmp_path / ".consoul"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "litellm_cache.json"

    # Patch the cache file location
    monkeypatch.setattr("consoul.ai.litellm_registry.CACHE_FILE", cache_file)
    monkeypatch.setattr("consoul.ai.litellm_registry.CACHE_DIR", cache_dir)

    return cache_file


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset global cache state before each test."""
    import consoul.ai.litellm_registry as registry_module

    registry_module._REGISTRY_CACHE = None
    registry_module._CACHE_LOADED = False
    registry_module._LAST_FETCH_ATTEMPT = None
    yield
    # Cleanup after test
    registry_module._REGISTRY_CACHE = None
    registry_module._CACHE_LOADED = False
    registry_module._LAST_FETCH_ATTEMPT = None


class TestCacheLoading:
    """Tests for cache loading and TTL logic."""

    def test_load_valid_cache(self, mock_cache_file, mock_registry_data):
        """Test loading a valid cache file."""
        from consoul.ai.litellm_registry import _load_cache

        # Create valid cache
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "models": mock_registry_data,
        }
        mock_cache_file.write_text(json.dumps(cache_data))

        # Load cache
        loaded = _load_cache()
        assert loaded is not None
        assert loaded["models"] == mock_registry_data

    def test_load_expired_cache(self, mock_cache_file, mock_registry_data):
        """Test that expired cache returns None."""
        from consoul.ai.litellm_registry import _load_cache

        # Create expired cache (25 hours old)
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        cache_data = {
            "fetched_at": expired_time.isoformat(),
            "models": mock_registry_data,
        }
        mock_cache_file.write_text(json.dumps(cache_data))

        # Load cache should return None
        loaded = _load_cache()
        assert loaded is None

    def test_load_missing_cache(self, mock_cache_file):
        """Test loading when cache file doesn't exist."""
        from consoul.ai.litellm_registry import _load_cache

        # Ensure file doesn't exist
        if mock_cache_file.exists():
            mock_cache_file.unlink()

        loaded = _load_cache()
        assert loaded is None

    def test_load_malformed_cache(self, mock_cache_file):
        """Test loading malformed JSON returns None."""
        from consoul.ai.litellm_registry import _load_cache

        # Write invalid JSON
        mock_cache_file.write_text("not valid json {")

        loaded = _load_cache()
        assert loaded is None


class TestCacheSaving:
    """Tests for cache saving logic."""

    def test_save_cache(self, mock_cache_file, mock_registry_data):
        """Test saving cache data to disk."""
        from consoul.ai.litellm_registry import _save_cache

        _save_cache(mock_registry_data)

        # Verify file was created
        assert mock_cache_file.exists()

        # Verify content
        cache_data = json.loads(mock_cache_file.read_text())
        assert "fetched_at" in cache_data
        assert "models" in cache_data
        assert cache_data["models"] == mock_registry_data

    def test_save_cache_creates_directory(
        self, tmp_path, monkeypatch, mock_registry_data
    ):
        """Test that save_cache creates directory if missing."""
        from consoul.ai.litellm_registry import _save_cache

        # Set cache to non-existent directory
        cache_dir = tmp_path / "new_dir" / ".consoul"
        cache_file = cache_dir / "litellm_cache.json"
        monkeypatch.setattr("consoul.ai.litellm_registry.CACHE_FILE", cache_file)
        monkeypatch.setattr("consoul.ai.litellm_registry.CACHE_DIR", cache_dir)

        _save_cache(mock_registry_data)

        # Verify directory and file were created
        assert cache_dir.exists()
        assert cache_file.exists()


class TestRegistryFetching:
    """Tests for fetching from LiteLLM GitHub."""

    @patch("urllib.request.urlopen")
    def test_fetch_registry_success(self, mock_urlopen, mock_registry_data):
        """Test successful registry fetch."""
        from consoul.ai.litellm_registry import _fetch_registry

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_registry_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        # Fetch registry
        data = _fetch_registry()
        assert data == mock_registry_data

    @patch("urllib.request.urlopen")
    def test_fetch_registry_http_error(self, mock_urlopen):
        """Test handling of HTTP errors."""
        from consoul.ai.litellm_registry import _fetch_registry

        # Mock HTTP 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        data = _fetch_registry()
        assert data is None

    @patch("urllib.request.urlopen")
    def test_fetch_registry_network_error(self, mock_urlopen):
        """Test handling of network errors."""
        from consoul.ai.litellm_registry import _fetch_registry

        # Mock network error
        mock_urlopen.side_effect = Exception("Network error")

        data = _fetch_registry()
        assert data is None


class TestContextWindowLookup:
    """Tests for get_litellm_context_window()."""

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_exact_match(self, mock_get_registry, mock_registry_data):
        """Test exact model ID match."""
        mock_get_registry.return_value = mock_registry_data

        context = get_litellm_context_window("gpt-4o-2025-01-15")
        assert context == 128_000

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_prefixed_match_slash(self, mock_get_registry, mock_registry_data):
        """Test matching model with provider prefix (/)."""
        mock_get_registry.return_value = mock_registry_data

        # Query without prefix should find "openai/gpt-4.1"
        context = get_litellm_context_window("gpt-4.1")
        assert context == 1_047_576

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_prefixed_match_colon(self, mock_get_registry):
        """Test matching model with provider prefix (:)."""
        registry_data = {
            "anthropic:claude-3-opus-20240229": {
                "max_input_tokens": 200_000,
                "max_output_tokens": 4_096,
            }
        }
        mock_get_registry.return_value = registry_data

        context = get_litellm_context_window("claude-3-opus-20240229")
        assert context == 200_000

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_model_not_found(self, mock_get_registry, mock_registry_data):
        """Test lookup of unknown model."""
        mock_get_registry.return_value = mock_registry_data

        context = get_litellm_context_window("unknown-model-xyz")
        assert context is None

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_model_without_max_input_tokens(self, mock_get_registry):
        """Test model entry without max_input_tokens field."""
        registry_data = {
            "test-model": {
                "max_output_tokens": 4_096,
                # Missing max_input_tokens
            }
        }
        mock_get_registry.return_value = registry_data

        context = get_litellm_context_window("test-model")
        assert context is None

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_model_with_zero_tokens(self, mock_get_registry):
        """Test model with zero max_input_tokens."""
        registry_data = {
            "test-model": {
                "max_input_tokens": 0,
                "max_output_tokens": 4_096,
            }
        }
        mock_get_registry.return_value = registry_data

        context = get_litellm_context_window("test-model")
        assert context is None


class TestRefreshCache:
    """Tests for cache refresh functionality."""

    @patch("consoul.ai.litellm_registry._fetch_registry")
    @patch("consoul.ai.litellm_registry._save_cache")
    def test_refresh_cache_success(
        self, mock_save, mock_fetch, mock_cache_file, mock_registry_data
    ):
        """Test successful cache refresh."""
        mock_fetch.return_value = mock_registry_data

        success = refresh_cache()
        assert success is True
        mock_fetch.assert_called_once()
        mock_save.assert_called_once_with(mock_registry_data)

    @patch("consoul.ai.litellm_registry._fetch_registry")
    def test_refresh_cache_failure(self, mock_fetch):
        """Test cache refresh failure."""
        mock_fetch.return_value = None

        success = refresh_cache()
        assert success is False


class TestCacheInfo:
    """Tests for get_cache_info()."""

    def test_cache_info_not_loaded(self):
        """Test cache info when cache not loaded."""
        info = get_cache_info()
        assert info["loaded"] is False
        assert "cache_file" in info
        assert "ttl_hours" in info
        assert info["ttl_hours"] == CACHE_TTL_HOURS

    @patch("consoul.ai.litellm_registry._get_registry")
    def test_cache_info_loaded(self, mock_get_registry, mock_registry_data):
        """Test cache info when cache is loaded."""
        import consoul.ai.litellm_registry as registry_module

        # Simulate loaded cache
        registry_module._REGISTRY_CACHE = mock_registry_data
        registry_module._CACHE_LOADED = True

        info = get_cache_info()
        assert info["loaded"] is True
        assert info["model_count"] == len(mock_registry_data)

    def test_cache_info_with_file(self, mock_cache_file, mock_registry_data):
        """Test cache info when cache file exists."""
        # Create cache file
        cache_data = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "models": mock_registry_data,
        }
        mock_cache_file.write_text(json.dumps(cache_data))

        info = get_cache_info()
        assert "fetched_at" in info
        assert "age_hours" in info
        assert "expired" in info
        assert info["expired"] is False

    def test_cache_info_with_expired_file(self, mock_cache_file, mock_registry_data):
        """Test cache info with expired cache file."""
        # Create expired cache
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        cache_data = {
            "fetched_at": expired_time.isoformat(),
            "models": mock_registry_data,
        }
        mock_cache_file.write_text(json.dumps(cache_data))

        info = get_cache_info()
        assert info["expired"] is True
        assert info["age_hours"] > CACHE_TTL_HOURS


class TestRetryBehavior:
    """Tests for retry behavior after transient failures."""

    @patch("urllib.request.urlopen")
    def test_retry_after_transient_failure(
        self, mock_urlopen, mock_cache_file, mock_registry_data
    ):
        """Test that registry retries after initial fetch failure."""
        import consoul.ai.litellm_registry as registry_module

        # Ensure no disk cache exists
        if mock_cache_file.exists():
            mock_cache_file.unlink()

        # First call fails
        mock_urlopen.side_effect = Exception("Network error")

        context = get_litellm_context_window("gpt-4o-2025-01-15")
        assert context is None  # No data available

        # Verify we tracked the failure
        assert registry_module._LAST_FETCH_ATTEMPT is not None
        assert registry_module._REGISTRY_CACHE is None  # NOT cached as empty

        # Second call within retry window should not fetch again
        mock_urlopen.reset_mock()
        context = get_litellm_context_window("gpt-4o-2025-01-15")
        assert context is None
        mock_urlopen.assert_not_called()  # No retry yet

        # Simulate time passing (beyond retry window)
        from datetime import timedelta
        from unittest.mock import patch as mock_patch

        future_time = registry_module._LAST_FETCH_ATTEMPT + timedelta(
            minutes=registry_module.RETRY_AFTER_FAILURE_MINUTES + 1
        )

        with mock_patch("consoul.ai.litellm_registry.datetime") as mock_datetime:
            mock_datetime.now.return_value = future_time
            mock_datetime.fromisoformat = datetime.fromisoformat

            # Now make fetch succeed
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = json.dumps(mock_registry_data).encode(
                "utf-8"
            )
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_urlopen.side_effect = None
            mock_urlopen.return_value = mock_response

            # Should retry and succeed
            context = get_litellm_context_window("gpt-4o-2025-01-15")
            assert context == 128_000
            mock_urlopen.assert_called_once()

            # Verify failure tracking was reset
            assert registry_module._LAST_FETCH_ATTEMPT is None
            assert registry_module._REGISTRY_CACHE is not None

    @patch("urllib.request.urlopen")
    def test_empty_result_not_permanently_cached(self, mock_urlopen, mock_cache_file):
        """Test that empty results from failures are not permanently cached."""
        import consoul.ai.litellm_registry as registry_module

        # Ensure no disk cache exists
        if mock_cache_file.exists():
            mock_cache_file.unlink()

        # Simulate fetch failure
        mock_urlopen.side_effect = Exception("Network error")

        # First lookup
        context1 = get_litellm_context_window("unknown-model")
        assert context1 is None

        # Verify empty result is NOT in _REGISTRY_CACHE
        assert registry_module._REGISTRY_CACHE is None

        # Multiple lookups within retry window should keep returning empty
        context2 = get_litellm_context_window("unknown-model")
        assert context2 is None

        # But should still allow retry after window expires
        assert registry_module._LAST_FETCH_ATTEMPT is not None

    @patch("urllib.request.urlopen")
    def test_refresh_cache_resets_failure_tracking(
        self, mock_urlopen, mock_cache_file, mock_registry_data
    ):
        """Test that refresh_cache clears failure state."""
        import consoul.ai.litellm_registry as registry_module

        # Ensure no disk cache exists
        if mock_cache_file.exists():
            mock_cache_file.unlink()

        # Initial fetch fails
        mock_urlopen.side_effect = Exception("Network error")
        get_litellm_context_window("test-model")

        # Verify failure was tracked
        assert registry_module._LAST_FETCH_ATTEMPT is not None

        # Refresh should clear failure tracking
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_registry_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.side_effect = None
        mock_urlopen.return_value = mock_response

        success = refresh_cache()
        assert success is True
        assert registry_module._LAST_FETCH_ATTEMPT is None
        assert registry_module._REGISTRY_CACHE is not None


class TestIntegration:
    """Integration tests for full workflow."""

    @patch("urllib.request.urlopen")
    def test_full_cache_workflow(
        self, mock_urlopen, mock_cache_file, mock_registry_data
    ):
        """Test complete workflow: fetch, cache, lookup."""
        # Mock successful HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(mock_registry_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        # First lookup should fetch from network
        context = get_litellm_context_window("gpt-4o-2025-01-15")
        assert context == 128_000

        # Verify cache was saved
        assert mock_cache_file.exists()

        # Second lookup should use cache (no new HTTP call)
        mock_urlopen.reset_mock()
        context2 = get_litellm_context_window("gpt-4o-2025-01-15")
        assert context2 == 128_000
        mock_urlopen.assert_not_called()
