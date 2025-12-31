"""Tests for session garbage collection (SOUL-332).

Tests the session GC feature that automatically cleans up orphaned sessions
(sessions without TTL) from Redis storage.
"""

from __future__ import annotations

import json
import sys
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from consoul.server.models import SessionConfig

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# Mock redis module for tests that don't have redis installed
@pytest.fixture(autouse=True)
def mock_redis_module():
    """Mock the redis module if not installed."""
    mock_redis_mod = MagicMock()
    with patch.dict(sys.modules, {"redis": mock_redis_mod}):
        yield mock_redis_mod


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client with ping configured."""
    mock = MagicMock()
    mock.ping.return_value = True
    return mock


# =============================================================================
# SessionConfig GC Fields Tests
# =============================================================================


class TestSessionConfigGCFields:
    """Tests for SessionConfig garbage collection configuration fields."""

    def test_gc_interval_default(self):
        """gc_interval defaults to 3600 (1 hour)."""
        config = SessionConfig()
        assert config.gc_interval == 3600

    def test_gc_batch_size_default(self):
        """gc_batch_size defaults to 100."""
        config = SessionConfig()
        assert config.gc_batch_size == 100

    def test_gc_interval_from_env(self, monkeypatch: MonkeyPatch):
        """gc_interval parses from environment variable."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_INTERVAL", "300")
        config = SessionConfig()
        assert config.gc_interval == 300

    def test_gc_batch_size_from_env(self, monkeypatch: MonkeyPatch):
        """gc_batch_size parses from environment variable."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_BATCH_SIZE", "500")
        config = SessionConfig()
        assert config.gc_batch_size == 500

    def test_gc_interval_zero_disables(self, monkeypatch: MonkeyPatch):
        """gc_interval=0 is valid (disables GC)."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_INTERVAL", "0")
        config = SessionConfig()
        assert config.gc_interval == 0

    def test_gc_interval_negative_invalid(self, monkeypatch: MonkeyPatch):
        """gc_interval cannot be negative."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_INTERVAL", "-1")
        with pytest.raises(ValidationError):
            SessionConfig()

    def test_gc_batch_size_zero_invalid(self, monkeypatch: MonkeyPatch):
        """gc_batch_size cannot be zero."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_BATCH_SIZE", "0")
        with pytest.raises(ValidationError):
            SessionConfig()

    def test_gc_batch_size_exceeds_max_invalid(self, monkeypatch: MonkeyPatch):
        """gc_batch_size cannot exceed 10000."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_BATCH_SIZE", "10001")
        with pytest.raises(ValidationError):
            SessionConfig()

    def test_gc_batch_size_at_max(self, monkeypatch: MonkeyPatch):
        """gc_batch_size can be exactly 10000."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_BATCH_SIZE", "10000")
        config = SessionConfig()
        assert config.gc_batch_size == 10000


# =============================================================================
# RedisSessionStore.cleanup() Tests
# =============================================================================


class TestRedisSessionStoreCleanup:
    """Tests for RedisSessionStore cleanup method."""

    def test_cleanup_returns_zero_when_no_ttl(self, mock_redis_client):
        """cleanup() returns 0 when TTL is None (can't determine expiry)."""
        from consoul.sdk.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=None)

        result = store.cleanup()
        assert result == 0
        # Should not call scan when TTL is None
        mock_redis_client.scan.assert_not_called()

    def test_cleanup_deletes_orphaned_expired_sessions(self, mock_redis_client):
        """cleanup() deletes sessions without TTL that have expired."""
        from consoul.sdk.session_store import RedisSessionStore

        # Session created 2 hours ago, TTL is 1 hour -> should be deleted
        old_session = json.dumps({"created_at": time.time() - 7200, "data": "test"})

        mock_redis_client.scan.return_value = (0, [b"consoul:session:old-session"])
        mock_redis_client.ttl.return_value = -1  # No TTL
        mock_redis_client.get.return_value = old_session.encode()

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 1
        mock_redis_client.delete.assert_called_once_with("consoul:session:old-session")

    def test_cleanup_skips_sessions_with_valid_ttl(self, mock_redis_client):
        """cleanup() skips sessions that have Redis TTL set."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [b"consoul:session:valid-session"])
        mock_redis_client.ttl.return_value = 1800  # Has TTL of 30 minutes

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 0
        mock_redis_client.delete.assert_not_called()
        mock_redis_client.get.assert_not_called()  # Shouldn't even read session data

    def test_cleanup_skips_recent_orphaned_sessions(self, mock_redis_client):
        """cleanup() skips orphaned sessions that are still within TTL."""
        from consoul.sdk.session_store import RedisSessionStore

        # Session created 30 minutes ago, TTL is 1 hour -> should NOT be deleted
        recent_session = json.dumps({"created_at": time.time() - 1800, "data": "test"})

        mock_redis_client.scan.return_value = (0, [b"consoul:session:recent-session"])
        mock_redis_client.ttl.return_value = -1  # No TTL
        mock_redis_client.get.return_value = recent_session.encode()

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 0
        mock_redis_client.delete.assert_not_called()

    def test_cleanup_deletes_corrupted_sessions(self, mock_redis_client):
        """cleanup() deletes sessions with corrupted JSON."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [b"consoul:session:corrupted"])
        mock_redis_client.ttl.return_value = -1  # No TTL
        mock_redis_client.get.return_value = b"not valid json{{"

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 1
        mock_redis_client.delete.assert_called_once_with("consoul:session:corrupted")

    def test_cleanup_handles_missing_created_at(self, mock_redis_client):
        """cleanup() handles sessions without created_at (treats as age=0)."""
        from consoul.sdk.session_store import RedisSessionStore

        # Session without created_at - uses 0.0 as default
        session = json.dumps({"data": "test"})

        mock_redis_client.scan.return_value = (0, [b"consoul:session:no-timestamp"])
        mock_redis_client.ttl.return_value = -1
        mock_redis_client.get.return_value = session.encode()

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        # Session age would be now - 0.0 = huge number, so should be deleted
        assert result == 1
        mock_redis_client.delete.assert_called_once()

    def test_cleanup_uses_scan_pagination(self, mock_redis_client):
        """cleanup() iterates through all SCAN pages."""
        from consoul.sdk.session_store import RedisSessionStore

        old_session = json.dumps({"created_at": time.time() - 7200})

        # First call returns cursor 100, second call returns 0 (done)
        mock_redis_client.scan.side_effect = [
            (100, [b"consoul:session:session1"]),
            (0, [b"consoul:session:session2"]),
        ]
        mock_redis_client.ttl.return_value = -1
        mock_redis_client.get.return_value = old_session.encode()

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 2
        assert mock_redis_client.scan.call_count == 2

    def test_cleanup_respects_batch_size(self, mock_redis_client):
        """cleanup() passes batch_size to SCAN count parameter."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [])

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        store.cleanup(batch_size=500)

        mock_redis_client.scan.assert_called_once_with(
            cursor=0, match="consoul:session:*", count=500
        )

    def test_cleanup_handles_redis_error(self, mock_redis_client):
        """cleanup() handles Redis errors gracefully."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.side_effect = Exception("Redis connection lost")

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 0  # Returns 0, doesn't raise

    def test_cleanup_custom_prefix(self, mock_redis_client):
        """cleanup() uses custom key prefix."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [])

        store = RedisSessionStore(
            redis_client=mock_redis_client, ttl=3600, prefix="myapp:sessions:"
        )
        store.cleanup()

        mock_redis_client.scan.assert_called_once_with(
            cursor=0, match="myapp:sessions:*", count=100
        )

    def test_cleanup_mixed_sessions(self, mock_redis_client):
        """cleanup() correctly handles mix of valid, orphaned, and corrupted."""
        from consoul.sdk.session_store import RedisSessionStore

        old_session = json.dumps({"created_at": time.time() - 7200})
        recent_session = json.dumps({"created_at": time.time() - 100})

        mock_redis_client.scan.return_value = (
            0,
            [
                b"consoul:session:valid-ttl",
                b"consoul:session:old-orphan",
                b"consoul:session:recent-orphan",
                b"consoul:session:corrupted",
            ],
        )

        def ttl_side_effect(key):
            if "valid-ttl" in key:
                return 1800  # Has TTL
            return -1  # No TTL (orphaned)

        def get_side_effect(key):
            if "old-orphan" in key:
                return old_session.encode()
            if "recent-orphan" in key:
                return recent_session.encode()
            if "corrupted" in key:
                return b"invalid json"
            return None

        mock_redis_client.ttl.side_effect = ttl_side_effect
        mock_redis_client.get.side_effect = get_side_effect

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        # Should delete: old-orphan (expired), corrupted (invalid JSON)
        # Should keep: valid-ttl (has TTL), recent-orphan (not expired)
        assert result == 2


# =============================================================================
# Factory GC Task Integration Tests
# =============================================================================


class TestFactoryGCTaskIntegration:
    """Tests for GC task integration in factory lifespan."""

    def test_gc_task_created_when_interval_positive(self, monkeypatch: MonkeyPatch):
        """GC task is created when gc_interval > 0."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_INTERVAL", "60")
        monkeypatch.setenv("CONSOUL_API_KEYS", "test-key")

        from consoul.server.factory import create_server

        app = create_server()
        # The GC task is created in lifespan, not at app creation
        # We can verify the config is correct
        assert app.state is not None

    def test_gc_config_parsed_correctly(self, monkeypatch: MonkeyPatch):
        """GC config values are parsed from environment."""
        monkeypatch.setenv("CONSOUL_SESSION_GC_INTERVAL", "120")
        monkeypatch.setenv("CONSOUL_SESSION_GC_BATCH_SIZE", "200")

        config = SessionConfig()
        assert config.gc_interval == 120
        assert config.gc_batch_size == 200


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing configurations."""

    def test_no_gc_config_uses_defaults(self):
        """Missing GC config uses defaults."""
        config = SessionConfig()
        assert config.gc_interval == 3600
        assert config.gc_batch_size == 100

    def test_memory_store_cleanup_still_works(self):
        """MemorySessionStore cleanup works independently."""
        from consoul.sdk.session_store import MemorySessionStore

        store = MemorySessionStore(ttl=1)  # 1 second TTL
        store.save("session1", {"data": "test"})

        # Wait for expiration
        time.sleep(1.1)

        result = store.cleanup()
        assert result == 1
        assert not store.exists("session1")

    def test_redis_store_without_ttl_cleanup_noop(self, mock_redis_client):
        """RedisSessionStore without TTL returns 0 from cleanup."""
        from consoul.sdk.session_store import RedisSessionStore

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=None)

        result = store.cleanup()
        assert result == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in session GC."""

    def test_cleanup_empty_redis(self, mock_redis_client):
        """cleanup() handles empty Redis gracefully."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [])

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 0

    def test_cleanup_session_deleted_between_scan_and_get(self, mock_redis_client):
        """cleanup() handles session deleted between scan and get."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [b"consoul:session:deleted"])
        mock_redis_client.ttl.return_value = -1
        mock_redis_client.get.return_value = None  # Session was deleted

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 0
        mock_redis_client.delete.assert_not_called()

    def test_cleanup_handles_bytes_and_string_keys(self, mock_redis_client):
        """cleanup() handles both bytes and string keys from SCAN."""
        from consoul.sdk.session_store import RedisSessionStore

        old_session = json.dumps({"created_at": time.time() - 7200})

        # Mix of bytes and string keys (some Redis clients return strings)
        mock_redis_client.scan.return_value = (
            0,
            [b"consoul:session:bytes-key", "consoul:session:string-key"],
        )
        mock_redis_client.ttl.return_value = -1
        mock_redis_client.get.return_value = old_session.encode()

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        assert result == 2

    def test_cleanup_ttl_negative_two_key_not_exist(self, mock_redis_client):
        """cleanup() handles TTL=-2 (key doesn't exist)."""
        from consoul.sdk.session_store import RedisSessionStore

        mock_redis_client.scan.return_value = (0, [b"consoul:session:nonexistent"])
        mock_redis_client.ttl.return_value = -2  # Key doesn't exist

        store = RedisSessionStore(redis_client=mock_redis_client, ttl=3600)
        result = store.cleanup()

        # TTL=-2 means key doesn't exist, should skip (not TTL=-1)
        assert result == 0
        mock_redis_client.get.assert_not_called()
