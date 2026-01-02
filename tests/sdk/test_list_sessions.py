"""Tests for list_sessions across all SessionStore implementations."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from consoul.sdk.session_store import (
    FileSessionStore,
    MemorySessionStore,
    RedisSessionStore,
)


class TestMemorySessionStoreListSessions:
    """Test MemorySessionStore.list_sessions()."""

    def test_list_empty_store(self) -> None:
        """list_sessions returns empty list for empty store."""
        store = MemorySessionStore()
        assert store.list_sessions() == []

    def test_list_all_sessions(self) -> None:
        """list_sessions returns all session IDs."""
        store = MemorySessionStore()
        store.save("session1", {"messages": []})
        store.save("session2", {"messages": []})
        store.save("session3", {"messages": []})

        sessions = store.list_sessions()
        assert len(sessions) == 3
        assert set(sessions) == {"session1", "session2", "session3"}

    def test_namespace_filter(self) -> None:
        """list_sessions filters by namespace prefix."""
        store = MemorySessionStore()
        store.save("alice:conv1", {"messages": []})
        store.save("alice:conv2", {"messages": []})
        store.save("bob:conv1", {"messages": []})
        store.save("charlie:conv1", {"messages": []})

        alice_sessions = store.list_sessions(namespace="alice:")
        assert len(alice_sessions) == 2
        assert all(s.startswith("alice:") for s in alice_sessions)

        bob_sessions = store.list_sessions(namespace="bob:")
        assert len(bob_sessions) == 1
        assert bob_sessions[0] == "bob:conv1"

    def test_limit(self) -> None:
        """list_sessions respects limit parameter."""
        store = MemorySessionStore()
        for i in range(10):
            store.save(f"session{i}", {"messages": []})

        sessions = store.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_offset(self) -> None:
        """list_sessions respects offset parameter."""
        store = MemorySessionStore()
        # Add sessions with delays to ensure ordering
        for i in range(5):
            store.save(f"session{i}", {"messages": []})
            time.sleep(0.001)

        all_sessions = store.list_sessions()
        offset_sessions = store.list_sessions(offset=2)

        assert len(offset_sessions) == 3
        # Offset should skip the first 2
        assert offset_sessions == all_sessions[2:]

    def test_pagination(self) -> None:
        """list_sessions pagination works correctly."""
        store = MemorySessionStore()
        for i in range(10):
            store.save(f"session{i:02d}", {"messages": []})
            time.sleep(0.001)

        # Get all sessions for comparison
        all_sessions = store.list_sessions()

        # Paginate through
        page1 = store.list_sessions(limit=3, offset=0)
        page2 = store.list_sessions(limit=3, offset=3)
        page3 = store.list_sessions(limit=3, offset=6)
        page4 = store.list_sessions(limit=3, offset=9)

        assert len(page1) == 3
        assert len(page2) == 3
        assert len(page3) == 3
        assert len(page4) == 1

        # Reconstruct should match
        reconstructed = page1 + page2 + page3 + page4
        assert reconstructed == all_sessions

    def test_sorted_by_recency(self) -> None:
        """list_sessions sorts by recency (most recent first)."""
        store = MemorySessionStore()

        # Create sessions with delays
        store.save("first", {"messages": []})
        time.sleep(0.01)
        store.save("second", {"messages": []})
        time.sleep(0.01)
        store.save("third", {"messages": []})

        sessions = store.list_sessions()

        # Most recent first
        assert sessions[0] == "third"
        assert sessions[1] == "second"
        assert sessions[2] == "first"

    def test_filters_expired_sessions(self) -> None:
        """list_sessions excludes expired sessions."""
        store = MemorySessionStore(ttl=0.05)  # 50ms TTL

        store.save("will_expire", {"messages": []})
        time.sleep(0.06)  # Wait for expiry
        store.save("still_valid", {"messages": []})

        sessions = store.list_sessions()

        assert "still_valid" in sessions
        assert "will_expire" not in sessions

    def test_no_ttl_includes_all(self) -> None:
        """list_sessions includes all when TTL is None."""
        store = MemorySessionStore(ttl=None)

        store.save("old", {"messages": []})
        time.sleep(0.01)
        store.save("new", {"messages": []})

        sessions = store.list_sessions()
        assert len(sessions) == 2


class TestFileSessionStoreListSessions:
    """Test FileSessionStore.list_sessions()."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_list_empty_store(self, temp_dir: Path) -> None:
        """list_sessions returns empty list for empty store."""
        store = FileSessionStore(temp_dir)
        assert store.list_sessions() == []

    def test_list_all_sessions(self, temp_dir: Path) -> None:
        """list_sessions returns all session IDs."""
        store = FileSessionStore(temp_dir)
        store.save("session1", {"messages": []})
        store.save("session2", {"messages": []})
        store.save("session3", {"messages": []})

        sessions = store.list_sessions()
        assert len(sessions) == 3
        assert set(sessions) == {"session1", "session2", "session3"}

    def test_namespace_filter(self, temp_dir: Path) -> None:
        """list_sessions filters by namespace prefix."""
        store = FileSessionStore(temp_dir)
        store.save("alice:conv1", {"messages": []})
        store.save("alice:conv2", {"messages": []})
        store.save("bob:conv1", {"messages": []})

        alice_sessions = store.list_sessions(namespace="alice:")
        assert len(alice_sessions) == 2
        assert all(s.startswith("alice:") for s in alice_sessions)

    def test_limit(self, temp_dir: Path) -> None:
        """list_sessions respects limit parameter."""
        store = FileSessionStore(temp_dir)
        for i in range(10):
            store.save(f"session{i}", {"messages": []})

        sessions = store.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_offset(self, temp_dir: Path) -> None:
        """list_sessions respects offset parameter."""
        store = FileSessionStore(temp_dir)
        for i in range(5):
            store.save(f"session{i}", {"messages": []})

        offset_sessions = store.list_sessions(offset=2)

        assert len(offset_sessions) == 3

    def test_sorted_by_modification_time(self, temp_dir: Path) -> None:
        """list_sessions sorts by file modification time (most recent first)."""
        store = FileSessionStore(temp_dir)

        store.save("first", {"messages": []})
        time.sleep(0.01)
        store.save("second", {"messages": []})
        time.sleep(0.01)
        store.save("third", {"messages": []})

        sessions = store.list_sessions()

        # Most recent first
        assert sessions[0] == "third"
        assert sessions[1] == "second"
        assert sessions[2] == "first"

    def test_filters_expired_sessions(self, temp_dir: Path) -> None:
        """list_sessions excludes expired sessions."""
        store = FileSessionStore(temp_dir, ttl=0.05)

        store.save("will_expire", {"messages": []})
        time.sleep(0.06)
        store.save("still_valid", {"messages": []})

        sessions = store.list_sessions()

        assert "still_valid" in sessions
        assert "will_expire" not in sessions

    def test_handles_special_characters(self, temp_dir: Path) -> None:
        """list_sessions handles session IDs with URL-encoded characters."""
        store = FileSessionStore(temp_dir)

        # These should be sanitized in filenames
        store.save("user:conv", {"messages": []})
        store.save("tenant:user:session", {"messages": []})

        sessions = store.list_sessions()
        assert len(sessions) == 2


class TestFileSessionStoreCollisionPrevention:
    """Tests for SOUL-351: Collision-proof session ID mapping."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_colon_separator_no_collision(self, temp_dir: Path) -> None:
        """Session IDs with colons don't collide with plain IDs."""
        store = FileSessionStore(temp_dir)

        # These used to collide: alice:conv1 -> aliceconv1, aliceconv1 -> aliceconv1
        store.save("alice:conv1", {"data": "with_colon"})
        store.save("aliceconv1", {"data": "without_colon"})

        # Verify distinct storage
        assert store.load("alice:conv1")["data"] == "with_colon"
        assert store.load("aliceconv1")["data"] == "without_colon"

        # Verify two separate files exist
        json_files = list(temp_dir.glob("*.json"))
        assert len(json_files) == 2

    def test_multi_colon_no_collision(self, temp_dir: Path) -> None:
        """Multiple colons don't cause collisions."""
        store = FileSessionStore(temp_dir)

        store.save("user:tenant:conv", {"data": "multi"})
        store.save("usertenantconv", {"data": "plain"})
        store.save("user:tenantconv", {"data": "mixed"})

        assert store.load("user:tenant:conv")["data"] == "multi"
        assert store.load("usertenantconv")["data"] == "plain"
        assert store.load("user:tenantconv")["data"] == "mixed"

        json_files = list(temp_dir.glob("*.json"))
        assert len(json_files) == 3

    def test_special_characters_preserved(self, temp_dir: Path) -> None:
        """Session IDs with special characters are stored correctly."""
        store = FileSessionStore(temp_dir)

        special_ids = [
            "user@example.com:session1",
            "tenant/user/conv",
            "id with spaces",
            "emoji_\U0001f600_id",
            "../etc/passwd",  # Path traversal attempt
        ]

        for i, sid in enumerate(special_ids):
            store.save(sid, {"index": i})

        for i, sid in enumerate(special_ids):
            loaded = store.load(sid)
            assert loaded is not None, f"Failed to load: {sid}"
            assert loaded["index"] == i

    def test_list_sessions_returns_original_ids(self, temp_dir: Path) -> None:
        """list_sessions returns original session IDs, not encoded filenames."""
        store = FileSessionStore(temp_dir)

        original_ids = ["alice:conv1", "bob:conv2", "user@tenant:session"]
        for sid in original_ids:
            store.save(sid, {"messages": []})

        listed = store.list_sessions()

        assert set(listed) == set(original_ids)
        # Verify they're the original IDs, not Base64-encoded
        assert "alice:conv1" in listed

    def test_namespace_filter_with_colons(self, temp_dir: Path) -> None:
        """Namespace filtering works with colon-separated IDs."""
        store = FileSessionStore(temp_dir)

        store.save("alice:conv1", {"messages": []})
        store.save("alice:conv2", {"messages": []})
        store.save("bob:conv1", {"messages": []})

        alice_sessions = store.list_sessions(namespace="alice:")

        assert len(alice_sessions) == 2
        assert all(s.startswith("alice:") for s in alice_sessions)

    def test_path_traversal_prevention(self, temp_dir: Path) -> None:
        """Path traversal attempts are safely handled."""
        store = FileSessionStore(temp_dir)

        # These should all be stored safely without escaping storage_dir
        dangerous_ids = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/absolute/path",
            "normal/../../../escape",
        ]

        for sid in dangerous_ids:
            store.save(sid, {"data": "safe"})
            loaded = store.load(sid)
            assert loaded is not None
            assert loaded["data"] == "safe"

        # Verify no files created outside storage_dir
        for path in temp_dir.iterdir():
            assert path.parent == temp_dir


class TestListSessionsEdgeCases:
    """Test edge cases for list_sessions."""

    def test_offset_beyond_count(self) -> None:
        """Offset beyond session count returns empty list."""
        store = MemorySessionStore()
        store.save("session1", {"messages": []})

        sessions = store.list_sessions(offset=100)
        assert sessions == []

    def test_limit_zero(self) -> None:
        """Limit of 0 returns empty list."""
        store = MemorySessionStore()
        store.save("session1", {"messages": []})

        sessions = store.list_sessions(limit=0)
        assert sessions == []

    def test_namespace_no_matches(self) -> None:
        """Namespace with no matches returns empty list."""
        store = MemorySessionStore()
        store.save("alice:conv1", {"messages": []})

        sessions = store.list_sessions(namespace="bob:")
        assert sessions == []

    def test_namespace_partial_match(self) -> None:
        """Namespace filters by prefix, not substring."""
        store = MemorySessionStore()
        store.save("alice:conv1", {"messages": []})
        store.save("malice:conv1", {"messages": []})  # Contains "alice" but not prefix

        sessions = store.list_sessions(namespace="alice:")
        assert len(sessions) == 1
        assert sessions[0] == "alice:conv1"

    def test_concurrent_modifications(self) -> None:
        """list_sessions handles concurrent modifications safely."""
        import threading

        store = MemorySessionStore()
        errors: list[Exception] = []

        def writer() -> None:
            try:
                for i in range(50):
                    store.save(
                        f"session{threading.current_thread().name}{i}", {"messages": []}
                    )
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                for _ in range(50):
                    store.list_sessions()
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            threads.append(threading.Thread(target=writer, name=f"writer{i}"))
            threads.append(threading.Thread(target=reader, name=f"reader{i}"))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


try:
    import redis  # noqa: F401

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


@pytest.mark.skipif(not HAS_REDIS, reason="redis package not installed")
class TestRedisSessionStoreListSessions:
    """Test RedisSessionStore.list_sessions() with mocked Redis client."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        """Create a mock Redis client with ping configured."""
        mock = MagicMock()
        mock.ping.return_value = True  # Required for connection test
        return mock

    @pytest.fixture
    def store(self, mock_redis: MagicMock) -> RedisSessionStore:
        """Create RedisSessionStore with mock client."""
        return RedisSessionStore(mock_redis, prefix="test:")

    def test_list_empty_store(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions returns empty list for empty store."""
        # Mock SCAN returning empty
        mock_redis.scan.return_value = (0, [])

        sessions = store.list_sessions()

        assert sessions == []
        mock_redis.scan.assert_called()

    def test_list_all_sessions(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions returns all session IDs sorted by recency."""
        # Mock SCAN returning 3 keys
        mock_redis.scan.return_value = (
            0,
            [b"test:session1", b"test:session2", b"test:session3"],
        )

        # Mock GET for each session with different timestamps
        def mock_get(key: bytes) -> bytes:
            timestamps = {
                b"test:session1": 1000.0,  # Oldest
                b"test:session2": 2000.0,
                b"test:session3": 3000.0,  # Newest
            }
            ts = timestamps.get(key, 0.0)
            return json.dumps({"created_at": ts}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions()

        # Should be sorted by recency (most recent first)
        assert len(sessions) == 3
        assert sessions[0] == "session3"
        assert sessions[1] == "session2"
        assert sessions[2] == "session1"

    def test_namespace_filter(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions filters by namespace prefix."""
        # Mock SCAN with pattern matching
        mock_redis.scan.return_value = (
            0,
            [b"test:alice:conv1", b"test:alice:conv2"],
        )

        def mock_get(key: bytes) -> bytes:
            return json.dumps({"created_at": 1000.0}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions(namespace="alice:")

        assert len(sessions) == 2
        # Verify scan was called with the right pattern
        mock_redis.scan.assert_called()
        call_args = mock_redis.scan.call_args
        assert "test:alice:*" in str(call_args)

    def test_limit(self, store: RedisSessionStore, mock_redis: MagicMock) -> None:
        """list_sessions respects limit parameter."""
        # Return 10 sessions
        mock_redis.scan.return_value = (
            0,
            [f"test:session{i}".encode() for i in range(10)],
        )

        def mock_get(key: bytes) -> bytes:
            # Different timestamps for each
            key_str = key.decode()
            idx = int(key_str.replace("test:session", ""))
            return json.dumps({"created_at": float(idx)}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions(limit=5)

        assert len(sessions) == 5

    def test_offset(self, store: RedisSessionStore, mock_redis: MagicMock) -> None:
        """list_sessions respects offset parameter."""
        # Return 5 sessions
        mock_redis.scan.return_value = (
            0,
            [f"test:session{i}".encode() for i in range(5)],
        )

        def mock_get(key: bytes) -> bytes:
            key_str = key.decode()
            idx = int(key_str.replace("test:session", ""))
            # Higher index = more recent
            return json.dumps({"created_at": float(idx)}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions(offset=2)

        # Should skip the 2 most recent
        assert len(sessions) == 3

    def test_sorted_by_recency(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions sorts by recency (most recent first)."""
        # Sessions with specific timestamps
        mock_redis.scan.return_value = (
            0,
            [b"test:first", b"test:second", b"test:third"],
        )

        def mock_get(key: bytes) -> bytes:
            timestamps = {
                b"test:first": 1000.0,
                b"test:second": 2000.0,
                b"test:third": 3000.0,
            }
            ts = timestamps.get(key, 0.0)
            return json.dumps({"updated_at": ts}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions()

        # Most recent first (uses updated_at over created_at)
        assert sessions[0] == "third"
        assert sessions[1] == "second"
        assert sessions[2] == "first"

    def test_handles_missing_timestamps(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions handles sessions without timestamps."""
        mock_redis.scan.return_value = (
            0,
            [b"test:with_ts", b"test:without_ts"],
        )

        def mock_get(key: bytes) -> bytes:
            if key == b"test:with_ts":
                return json.dumps({"created_at": 1000.0}).encode()
            else:
                return json.dumps({}).encode()  # No timestamp

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions()

        assert len(sessions) == 2
        # Session with timestamp should come first (1000.0 > 0.0)
        assert sessions[0] == "with_ts"
        assert sessions[1] == "without_ts"

    def test_handles_json_decode_error(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions handles invalid JSON gracefully."""
        mock_redis.scan.return_value = (
            0,
            [b"test:valid", b"test:invalid"],
        )

        def mock_get(key: bytes) -> bytes:
            if key == b"test:valid":
                return json.dumps({"created_at": 1000.0}).encode()
            else:
                return b"not valid json"

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions()

        # Both should be included, invalid one gets timestamp 0
        assert len(sessions) == 2

    def test_multi_page_scan(
        self, store: RedisSessionStore, mock_redis: MagicMock
    ) -> None:
        """list_sessions handles multi-page SCAN results."""
        # First call returns cursor 42, second returns 0
        mock_redis.scan.side_effect = [
            (42, [b"test:page1_sess1", b"test:page1_sess2"]),
            (0, [b"test:page2_sess1"]),
        ]

        def mock_get(key: bytes) -> bytes:
            return json.dumps({"created_at": 1000.0}).encode()

        mock_redis.get.side_effect = mock_get

        sessions = store.list_sessions()

        # Should have collected from both pages
        assert len(sessions) == 3
        assert mock_redis.scan.call_count == 2
