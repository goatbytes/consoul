"""Session state storage protocols and implementations.

This module provides safe JSON-based session state persistence for HTTP endpoints
and multi-user backends, enabling session restoration across requests without
RCE vulnerabilities from pickle.

Key Features:
    - Protocol-based design for flexible storage backends
    - JSON-only serialization (no pickle/exec/eval)
    - Per-session locking for concurrent access safety
    - Multiple implementations: memory, file, Redis
    - TTL support for automatic session cleanup

Example - FastAPI with file storage:
    >>> from consoul.sdk import create_session, save_session_state, restore_session
    >>> from consoul.sdk.session_store import FileSessionStore
    >>>
    >>> store = FileSessionStore("/tmp/sessions")
    >>>
    >>> # Create and save session
    >>> console = create_session(session_id="user123", model="gpt-4o")
    >>> console.chat("Hello!")
    >>> state = save_session_state(console)
    >>> store.save("user123", state)
    >>>
    >>> # Later, restore session
    >>> state = store.load("user123")
    >>> console = restore_session(state)
    >>> console.chat("Continue conversation")

Example - Redis backend:
    >>> store = RedisSessionStore(redis_client, ttl=3600)
    >>> store.save("user123", state)
    >>> restored = store.load("user123")

Security Notes:
    - Only JSON-serializable data is stored (no executable code)
    - All session IDs should be cryptographically secure (UUID, JWT subject)
    - Implement rate limiting per session to prevent abuse
    - Use HTTPS for network-based stores (Redis, database)
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session state storage backends.

    Implementations must provide thread-safe methods for saving, loading,
    and deleting session state. All data is expected to be JSON-serializable.

    Methods:
        save: Store session state
        load: Retrieve session state
        delete: Remove session state
        exists: Check if session exists
        cleanup: Remove expired sessions (optional)

    Example Implementation:
        >>> class MyStore:
        ...     def save(self, session_id: str, state: dict[str, Any]) -> None:
        ...         # Store state in backend
        ...         pass
        ...
        ...     def load(self, session_id: str) -> dict[str, Any] | None:
        ...         # Retrieve state from backend
        ...         return None
        ...
        ...     def delete(self, session_id: str) -> None:
        ...         # Remove state from backend
        ...         pass
        ...
        ...     def exists(self, session_id: str) -> bool:
        ...         # Check if session exists
        ...         return False
    """

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Store session state.

        Args:
            session_id: Unique session identifier
            state: JSON-serializable session state dictionary

        Raises:
            ValueError: If state is not JSON-serializable
            IOError: If storage operation fails
        """
        ...

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session state.

        Args:
            session_id: Unique session identifier

        Returns:
            Session state dictionary if found, None if not found or expired

        Raises:
            IOError: If storage operation fails
        """
        ...

    def delete(self, session_id: str) -> None:
        """Remove session state.

        Args:
            session_id: Unique session identifier

        Raises:
            IOError: If storage operation fails
        """
        ...

    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists and not expired, False otherwise
        """
        ...

    def cleanup(self) -> int:
        """Remove expired sessions.

        Returns:
            Number of sessions cleaned up

        Note:
            This method is optional. Implementations may raise NotImplementedError.
        """
        ...

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List session IDs, optionally filtered by namespace prefix.

        Enables listing sessions per user/tenant when using namespaced session IDs
        (e.g., "user123:conv1", "user123:conv2").

        Args:
            namespace: Optional namespace prefix filter (e.g., "user123:")
            limit: Maximum sessions to return (default: 100)
            offset: Number of sessions to skip for pagination (default: 0)

        Returns:
            List of session IDs matching criteria

        Example - List all sessions for a user:
            >>> store.list_sessions(namespace="user123:")
            ['user123:conv1', 'user123:conv2', 'user123:conv3']

        Example - Paginated listing:
            >>> page1 = store.list_sessions(limit=10, offset=0)
            >>> page2 = store.list_sessions(limit=10, offset=10)

        Note:
            This method is optional. Implementations may raise NotImplementedError.
        """
        ...


class MemorySessionStore:
    """In-memory session storage with TTL support.

    Thread-safe implementation using dict and per-session locks.
    Suitable for development, testing, and single-process applications.

    Attributes:
        ttl: Time-to-live in seconds (None = no expiration)

    Example:
        >>> store = MemorySessionStore(ttl=3600)  # 1 hour TTL
        >>> store.save("user123", {"model": "gpt-4o", "messages": []})
        >>> state = store.load("user123")
        >>> store.cleanup()  # Remove expired sessions
        0

    Warning:
        Data is lost when process terminates. Use FileSessionStore or
        RedisSessionStore for persistent storage.
    """

    def __init__(self, ttl: float | None = None):
        """Initialize in-memory session store.

        Args:
            ttl: Time-to-live in seconds (None = no expiration)
        """
        self.ttl = ttl
        self._sessions: dict[str, dict[str, Any]] = {}
        self._timestamps: dict[str, float] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Store session state in memory.

        Args:
            session_id: Unique session identifier
            state: Session state dictionary

        Raises:
            ValueError: If state is not JSON-serializable
        """
        # Validate JSON serializability
        try:
            json.dumps(state)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Session state must be JSON-serializable: {e}") from e

        # Get or create session lock
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            lock = self._locks[session_id]

        # Store state
        with lock:
            self._sessions[session_id] = state.copy()
            self._timestamps[session_id] = time.time()
            logger.debug(f"Saved session {session_id} to memory")

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session state from memory.

        Args:
            session_id: Unique session identifier

        Returns:
            Session state dictionary if found and not expired, None otherwise
        """
        with self._global_lock:
            if session_id not in self._sessions:
                return None
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            lock = self._locks[session_id]

        with lock:
            # Check expiration
            if self.ttl is not None:
                created_at = self._timestamps.get(session_id, 0)
                if time.time() - created_at >= self.ttl:
                    logger.debug(f"Session {session_id} expired")
                    # Clean up expired session
                    self._sessions.pop(session_id, None)
                    self._timestamps.pop(session_id, None)
                    return None

            state = self._sessions.get(session_id)
            if state is not None:
                logger.debug(f"Loaded session {session_id} from memory")
                return state.copy()
            return None

    def delete(self, session_id: str) -> None:
        """Remove session state from memory.

        Args:
            session_id: Unique session identifier
        """
        with self._global_lock:
            lock = self._locks.pop(session_id) if session_id in self._locks else None

        if lock is not None:
            with lock:
                self._sessions.pop(session_id, None)
                self._timestamps.pop(session_id, None)
                logger.debug(f"Deleted session {session_id} from memory")

    def exists(self, session_id: str) -> bool:
        """Check if session exists in memory.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists and not expired, False otherwise
        """
        return self.load(session_id) is not None

    def cleanup(self) -> int:
        """Remove expired sessions from memory.

        Returns:
            Number of sessions cleaned up
        """
        if self.ttl is None:
            return 0

        now = time.time()
        expired = [
            sid
            for sid, created_at in self._timestamps.items()
            if now - created_at >= self.ttl
        ]

        for sid in expired:
            self.delete(sid)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions from memory")

        return len(expired)

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List session IDs with optional namespace filtering.

        Sessions are filtered by TTL (expired sessions excluded) and sorted
        by recency (most recently created/updated first).

        Args:
            namespace: Optional namespace prefix filter
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of session IDs matching criteria, sorted by recency
        """
        now = time.time()

        with self._global_lock:
            # Get non-expired sessions with timestamps
            valid_sessions: list[tuple[str, float]] = []
            for sid in self._sessions:
                timestamp = self._timestamps.get(sid, 0.0)
                # Check TTL if set
                if self.ttl is not None and now - timestamp >= self.ttl:
                    continue  # Skip expired sessions
                valid_sessions.append((sid, timestamp))

        # Filter by namespace prefix if provided
        if namespace:
            valid_sessions = [
                (sid, ts) for sid, ts in valid_sessions if sid.startswith(namespace)
            ]

        # Sort by recency (most recent first)
        valid_sessions.sort(key=lambda x: x[1], reverse=True)

        # Extract just the session IDs
        all_ids = [sid for sid, _ in valid_sessions]

        # Apply pagination
        return all_ids[offset : offset + limit]


class FileSessionStore:
    """File-based session storage with JSON serialization.

    Thread-safe implementation using file locks. Stores each session as a
    separate JSON file in the specified directory. Suitable for persistent
    storage in single-server deployments.

    Attributes:
        storage_dir: Directory path for session files
        ttl: Time-to-live in seconds (None = no expiration)

    Example:
        >>> store = FileSessionStore("/var/consoul/sessions", ttl=3600)
        >>> store.save("user123", {"model": "gpt-4o", "messages": []})
        >>> state = store.load("user123")
        >>> store.cleanup()  # Remove expired session files
        0

    File Format:
        {
            "session_id": "user123",
            "created_at": 1704067200.0,
            "updated_at": 1704067200.0,
            "state": { ... session state ... }
        }

    Security Notes:
        - Set appropriate file permissions (0600 recommended)
        - Use secure session IDs (UUID, not sequential)
        - Consider encrypting sensitive data before storage
    """

    def __init__(self, storage_dir: str | Path, ttl: float | None = None):
        """Initialize file-based session store.

        Args:
            storage_dir: Directory path for session files
            ttl: Time-to-live in seconds (None = no expiration)

        Raises:
            ValueError: If storage_dir is invalid
        """
        self.storage_dir = Path(storage_dir)
        self.ttl = ttl
        self._locks: dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()

        # Create storage directory
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Initialized file session store at {self.storage_dir}")
        except Exception as e:
            raise ValueError(f"Failed to create storage directory: {e}") from e

    def _get_session_path(self, session_id: str) -> Path:
        """Get file path for session.

        Args:
            session_id: Session identifier

        Returns:
            Path to session file
        """
        # Sanitize session_id to prevent path traversal
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "_-")
        return self.storage_dir / f"{safe_id}.json"

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Store session state to file.

        Args:
            session_id: Unique session identifier
            state: Session state dictionary

        Raises:
            ValueError: If state is not JSON-serializable
            IOError: If file write fails
        """
        # Validate JSON serializability
        try:
            json.dumps(state)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Session state must be JSON-serializable: {e}") from e

        # Get or create session lock
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            lock = self._locks[session_id]

        # Write to file
        path = self._get_session_path(session_id)
        with lock:
            try:
                now = time.time()
                wrapper = {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "state": state,
                }

                # Atomic write: write to temp file, then rename
                temp_path = path.with_suffix(".tmp")
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(wrapper, f, indent=2, ensure_ascii=False)

                temp_path.replace(path)
                logger.debug(f"Saved session {session_id} to {path}")

            except Exception as e:
                raise OSError(f"Failed to save session {session_id}: {e}") from e

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session state from file.

        Args:
            session_id: Unique session identifier

        Returns:
            Session state dictionary if found and not expired, None otherwise

        Raises:
            IOError: If file read fails
        """
        path = self._get_session_path(session_id)

        if not path.exists():
            return None

        # Get or create session lock
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            lock = self._locks[session_id]

        with lock:
            try:
                with open(path, encoding="utf-8") as f:
                    wrapper = json.load(f)

                # Check expiration
                if self.ttl is not None:
                    created_at = wrapper.get("created_at", 0)
                    if time.time() - created_at >= self.ttl:
                        logger.debug(f"Session {session_id} expired")
                        path.unlink()
                        return None

                logger.debug(f"Loaded session {session_id} from {path}")
                state: dict[str, Any] | None = wrapper.get("state")
                return state

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode session {session_id}: {e}")
                return None
            except Exception as e:
                raise OSError(f"Failed to load session {session_id}: {e}") from e

    def delete(self, session_id: str) -> None:
        """Remove session file.

        Args:
            session_id: Unique session identifier

        Raises:
            IOError: If file deletion fails
        """
        path = self._get_session_path(session_id)

        if not path.exists():
            return

        # Get or create session lock
        with self._global_lock:
            if session_id not in self._locks:
                self._locks[session_id] = threading.Lock()
            lock = self._locks[session_id]

        with lock:
            try:
                path.unlink()
                logger.debug(f"Deleted session {session_id} from {path}")
            except Exception as e:
                raise OSError(f"Failed to delete session {session_id}: {e}") from e

    def exists(self, session_id: str) -> bool:
        """Check if session file exists.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists and not expired, False otherwise
        """
        return self.load(session_id) is not None

    def cleanup(self) -> int:
        """Remove expired session files.

        Returns:
            Number of sessions cleaned up

        Raises:
            IOError: If cleanup fails
        """
        if self.ttl is None:
            return 0

        now = time.time()
        expired = []

        try:
            for path in self.storage_dir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        wrapper = json.load(f)
                    created_at = wrapper.get("created_at", 0)
                    if now - created_at >= self.ttl:
                        expired.append(path)
                except Exception as e:
                    logger.error(f"Error checking {path}: {e}")

            for path in expired:
                try:
                    path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting {path}: {e}")

            if expired:
                logger.info(
                    f"Cleaned up {len(expired)} expired sessions from {self.storage_dir}"
                )

            return len(expired)

        except Exception as e:
            raise OSError(f"Failed to cleanup sessions: {e}") from e

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List session IDs with optional namespace filtering.

        Sessions are filtered by TTL (expired sessions excluded) and sorted
        by recency (most recently modified first).

        Note: Reads session_id from JSON files since filenames are sanitized.

        Args:
            namespace: Optional namespace prefix filter
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of session IDs matching criteria, sorted by recency
        """
        # Collect sessions with their timestamps for sorting
        sessions_with_time: list[tuple[str, float]] = []

        try:
            for path in self.storage_dir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        wrapper = json.load(f)

                    # Get created_at timestamp
                    created_at = wrapper.get("created_at", 0.0)

                    # Check TTL if applicable
                    if self.ttl is not None and time.time() - created_at >= self.ttl:
                        continue  # Skip expired sessions

                    # Get actual session_id from file content (filename is sanitized)
                    session_id = wrapper.get("session_id", path.stem)
                    sessions_with_time.append((session_id, created_at))

                except (json.JSONDecodeError, KeyError):
                    # Skip invalid files
                    continue

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

        # Filter by namespace prefix if provided
        if namespace:
            sessions_with_time = [
                (sid, ts) for sid, ts in sessions_with_time if sid.startswith(namespace)
            ]

        # Sort by recency (most recent first)
        sessions_with_time.sort(key=lambda x: x[1], reverse=True)

        # Extract just session IDs
        session_ids = [sid for sid, _ in sessions_with_time]

        # Apply pagination
        return session_ids[offset : offset + limit]


class RedisSessionStore:
    """Redis-based session storage with automatic expiration.

    Thread-safe implementation using Redis operations. Suitable for
    distributed deployments and high-concurrency scenarios. Requires
    redis-py package.

    Attributes:
        redis: Redis client instance
        ttl: Time-to-live in seconds (None = no expiration)
        prefix: Key prefix for namespacing

    Example:
        >>> import redis
        >>> client = redis.Redis(host="localhost", port=6379, db=0)
        >>> store = RedisSessionStore(client, ttl=3600, prefix="consoul:session:")
        >>> store.save("user123", {"model": "gpt-4o", "messages": []})
        >>> state = store.load("user123")

    Security Notes:
        - Use TLS for Redis connections in production
        - Configure Redis AUTH password
        - Use separate Redis DB or prefix for session data
        - Consider encrypting sensitive data before storage

    Dependencies:
        >>> pip install redis
    """

    def __init__(
        self,
        redis_client: Redis,
        ttl: float | None = None,
        prefix: str = "consoul:session:",
    ):
        """Initialize Redis-based session store.

        Args:
            redis_client: Redis client instance
            ttl: Time-to-live in seconds (None = no expiration)
            prefix: Key prefix for namespacing

        Raises:
            ImportError: If redis package is not installed
            ConnectionError: If Redis connection fails
        """
        try:
            # Verify redis is installed
            import redis  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "redis package required for RedisSessionStore. "
                "Install with: pip install redis"
            ) from e

        self.redis = redis_client
        self.ttl = ttl
        self.prefix = prefix

        # Test connection
        try:
            self.redis.ping()
            logger.debug(f"Initialized Redis session store with prefix '{prefix}'")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}") from e

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session.

        Args:
            session_id: Session identifier

        Returns:
            Redis key with prefix
        """
        return f"{self.prefix}{session_id}"

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Store session state in Redis.

        Args:
            session_id: Unique session identifier
            state: Session state dictionary

        Raises:
            ValueError: If state is not JSON-serializable
            IOError: If Redis operation fails
        """
        # Validate JSON serializability
        try:
            json_data = json.dumps(state, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Session state must be JSON-serializable: {e}") from e

        key = self._get_key(session_id)

        try:
            if self.ttl is not None:
                self.redis.setex(key, int(self.ttl), json_data)
            else:
                self.redis.set(key, json_data)

            logger.debug(f"Saved session {session_id} to Redis key {key}")

        except Exception as e:
            raise OSError(f"Failed to save session {session_id} to Redis: {e}") from e

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve session state from Redis.

        Args:
            session_id: Unique session identifier

        Returns:
            Session state dictionary if found, None if not found or expired

        Raises:
            IOError: If Redis operation fails
        """
        key = self._get_key(session_id)

        try:
            json_data = self.redis.get(key)
            if json_data is None:
                return None

            loaded_state: dict[str, Any] = json.loads(json_data)
            logger.debug(f"Loaded session {session_id} from Redis key {key}")
            return loaded_state

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode session {session_id} from Redis: {e}")
            return None
        except Exception as e:
            raise OSError(f"Failed to load session {session_id} from Redis: {e}") from e

    def delete(self, session_id: str) -> None:
        """Remove session from Redis.

        Args:
            session_id: Unique session identifier

        Raises:
            IOError: If Redis operation fails
        """
        key = self._get_key(session_id)

        try:
            self.redis.delete(key)
            logger.debug(f"Deleted session {session_id} from Redis key {key}")
        except Exception as e:
            raise OSError(
                f"Failed to delete session {session_id} from Redis: {e}"
            ) from e

    def exists(self, session_id: str) -> bool:
        """Check if session exists in Redis.

        Args:
            session_id: Unique session identifier

        Returns:
            True if session exists, False otherwise
        """
        key = self._get_key(session_id)
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            logger.error(f"Failed to check session {session_id} in Redis: {e}")
            return False

    def cleanup(self, batch_size: int = 100) -> int:
        """Remove orphaned sessions without TTL that have expired.

        Scans Redis for session keys without TTL (TTL=-1) and checks
        if they should have expired based on their created_at timestamp.
        Sessions with valid Redis TTL are skipped as Redis handles their
        expiration automatically.

        Args:
            batch_size: Number of keys to process per SCAN iteration

        Returns:
            Count of sessions deleted

        Note:
            Uses SCAN (not KEYS) for production safety. Only deletes sessions
            where TTL=-1 (no expiry set) AND age >= self.ttl.
        """
        if self.ttl is None:
            # No TTL configured, can't determine what's expired
            return 0

        pattern = f"{self.prefix}*"
        cursor = 0
        deleted_count = 0
        now = time.time()

        try:
            while True:
                cursor, keys = self.redis.scan(
                    cursor=cursor, match=pattern, count=batch_size
                )

                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key

                    # Check if key has no TTL (orphaned)
                    key_ttl = self.redis.ttl(key_str)
                    if key_ttl == -1:  # No expiry set
                        try:
                            json_data = self.redis.get(key_str)
                            if json_data:
                                data = json.loads(json_data)
                                created_at = data.get("created_at", 0.0)
                                if now - created_at >= self.ttl:
                                    self.redis.delete(key_str)
                                    deleted_count += 1
                        except (json.JSONDecodeError, TypeError):
                            # Corrupted session, delete it
                            self.redis.delete(key_str)
                            deleted_count += 1

                if cursor == 0:
                    break

        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")

        if deleted_count > 0:
            logger.info(f"Session GC: cleaned {deleted_count} orphaned sessions")

        return deleted_count

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List session IDs with optional namespace filtering using SCAN.

        Uses Redis SCAN for production-safe, non-blocking iteration.
        Sessions are sorted by recency (most recently created/updated first)
        for consistency with other SessionStore implementations.

        Args:
            namespace: Optional namespace prefix filter
            limit: Maximum sessions to return
            offset: Number of sessions to skip

        Returns:
            List of session IDs matching criteria, sorted by recency

        Note:
            For very large numbers of sessions, consider using a Redis sorted set
            to track session timestamps for more efficient recency-based listing.
            The current implementation loads each session to get timestamps.
        """
        pattern = f"{self.prefix}*"
        if namespace:
            pattern = f"{self.prefix}{namespace}*"

        # Collect sessions with timestamps for recency sorting
        sessions_with_time: list[tuple[str, float]] = []
        cursor = 0

        try:
            # Collect all matching sessions first
            while True:
                cursor, keys = self.redis.scan(cursor=cursor, match=pattern, count=100)

                for key in keys:
                    # Extract session_id from key (remove prefix)
                    key_str = key.decode() if isinstance(key, bytes) else key
                    session_id = key_str[len(self.prefix) :]

                    # Get timestamp from session data for recency sorting
                    try:
                        json_data = self.redis.get(key)
                        if json_data:
                            data = json.loads(json_data)
                            # Use updated_at if available, else created_at, else 0
                            timestamp = data.get(
                                "updated_at", data.get("created_at", 0.0)
                            )
                            sessions_with_time.append((session_id, timestamp))
                    except (json.JSONDecodeError, TypeError):
                        # If we can't get timestamp, use 0 (will sort to end)
                        sessions_with_time.append((session_id, 0.0))

                if cursor == 0:
                    break

            # Filter by namespace prefix if provided (already filtered by pattern,
            # but double-check in case of edge cases)
            if namespace:
                sessions_with_time = [
                    (sid, ts)
                    for sid, ts in sessions_with_time
                    if sid.startswith(namespace)
                ]

            # Sort by recency (most recent first)
            sessions_with_time.sort(key=lambda x: x[1], reverse=True)

            # Extract just session IDs
            all_session_ids = [sid for sid, _ in sessions_with_time]

            # Apply pagination
            return all_session_ids[offset : offset + limit]

        except Exception as e:
            logger.error(f"Error listing sessions from Redis: {e}")
            return []


class HookedSessionStore:
    """SessionStore wrapper that applies lifecycle hooks.

    Wraps any SessionStore implementation to add hook execution around
    save/load operations. Enables encryption, summarization, redaction,
    and custom processing without modifying store implementations.

    Supports both sync and async hooks - auto-detects and handles both.

    Attributes:
        store: Underlying SessionStore implementation
        hooks: List of SessionHooks to apply (in order)

    Example - Encryption + Audit logging:
        >>> base_store = RedisSessionStore(client, ttl=3600)
        >>> hooked_store = HookedSessionStore(
        ...     store=base_store,
        ...     hooks=[
        ...         EncryptionHook(key_provider),
        ...         AuditLoggingHook(audit_logger),
        ...     ]
        ... )
        >>> hooked_store.save(session_id, state)  # Encrypted then logged

    Example - PII redaction:
        >>> from consoul.sdk.redaction import PiiRedactor
        >>> redactor = PiiRedactor(fields=["password", "ssn"])
        >>> hooked_store = HookedSessionStore(
        ...     store=FileSessionStore("/var/sessions"),
        ...     hooks=[RedactionHook(redactor)]
        ... )

    Note:
        Hooks are applied in order for on_before_save (first to last)
        and reverse order for on_after_load (last to first).
    """

    def __init__(
        self,
        store: SessionStore,
        hooks: list[Any] | None = None,
    ) -> None:
        """Initialize hooked store wrapper.

        Args:
            store: Underlying SessionStore to wrap
            hooks: List of SessionHooks to apply
        """
        self.store = store
        self.hooks: list[Any] = hooks or []

    def _get_hook_method(self, hook: Any, method_name: str) -> Any | None:
        """Get a hook method if it exists, None otherwise.

        Supports partial hook implementations by returning None for
        missing methods instead of raising AttributeError.
        """
        method = getattr(hook, method_name, None)
        return method if callable(method) else None

    def _run_hook_sync(
        self,
        hook_method: Any,
        *args: Any,
    ) -> Any:
        """Run a hook method, handling both sync and async.

        Uses inspect.iscoroutinefunction to detect async methods.
        For async methods, runs them with asyncio.
        """
        import asyncio
        import inspect

        if inspect.iscoroutinefunction(hook_method):
            # Async hook - run with asyncio
            try:
                asyncio.get_running_loop()
                # We're in an async context, need to use a thread pool
                # to avoid "cannot run event loop while another is running"
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, hook_method(*args))
                    return future.result()
            except RuntimeError:
                # No running loop - safe to use asyncio.run
                return asyncio.run(hook_method(*args))
        else:
            # Sync hook - call directly
            return hook_method(*args)

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Save session state with hook transformations.

        Applies on_before_save hooks, saves to store, then calls on_after_save.
        Hooks can implement any subset of methods (partial implementation).
        """
        transformed_state = state.copy()

        # Apply on_before_save hooks (in order)
        for hook in self.hooks:
            hook_method = self._get_hook_method(hook, "on_before_save")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                result = self._run_hook_sync(hook_method, session_id, transformed_state)
                if result is not None:
                    transformed_state = result
            except Exception as e:
                logger.error(
                    f"Hook {hook.__class__.__name__}.on_before_save failed: {e}"
                )
                raise

        # Save to underlying store
        self.store.save(session_id, transformed_state)

        # Call on_after_save hooks (for audit/notification)
        for hook in self.hooks:
            hook_method = self._get_hook_method(hook, "on_after_save")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                self._run_hook_sync(hook_method, session_id, transformed_state)
            except Exception as e:
                # Don't fail the save for after-save hooks
                logger.warning(
                    f"Hook {hook.__class__.__name__}.on_after_save failed: {e}"
                )

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session state with hook transformations.

        Applies on_before_load hooks, loads from store, then applies
        on_after_load hooks in reverse order.
        Hooks can implement any subset of methods (partial implementation).
        """
        current_session_id = session_id

        # Apply on_before_load hooks (in order) for access control/transformation
        for hook in self.hooks:
            hook_method = self._get_hook_method(hook, "on_before_load")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                result = self._run_hook_sync(hook_method, current_session_id)
                if result is None:
                    # Hook returned None - abort load (access denied)
                    return None
                current_session_id = result
            except Exception as e:
                logger.error(
                    f"Hook {hook.__class__.__name__}.on_before_load failed: {e}"
                )
                raise

        # Load from underlying store
        state = self.store.load(current_session_id)

        if state is None:
            return None

        # Apply on_after_load hooks (in reverse order for unwrapping)
        for hook in reversed(self.hooks):
            hook_method = self._get_hook_method(hook, "on_after_load")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                result = self._run_hook_sync(hook_method, session_id, state)
                if result is not None:
                    state = result
                else:
                    # Hook returned None - propagate as session not found
                    return None
            except Exception as e:
                logger.error(
                    f"Hook {hook.__class__.__name__}.on_after_load failed: {e}"
                )
                raise

        return state

    def delete(self, session_id: str) -> None:
        """Delete session with hook callbacks.

        Calls on_before_delete hooks, deletes from store, then on_after_delete.
        Hooks can implement any subset of methods (partial implementation).
        """
        # Apply on_before_delete hooks (in order)
        for hook in self.hooks:
            hook_method = self._get_hook_method(hook, "on_before_delete")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                self._run_hook_sync(hook_method, session_id)
            except Exception as e:
                logger.error(
                    f"Hook {hook.__class__.__name__}.on_before_delete failed: {e}"
                )
                raise

        # Delete from underlying store
        self.store.delete(session_id)

        # Call on_after_delete hooks (for audit/notification)
        for hook in self.hooks:
            hook_method = self._get_hook_method(hook, "on_after_delete")
            if hook_method is None:
                continue  # Hook doesn't implement this method
            try:
                self._run_hook_sync(hook_method, session_id)
            except Exception as e:
                # Don't fail the delete for after-delete hooks
                logger.warning(
                    f"Hook {hook.__class__.__name__}.on_after_delete failed: {e}"
                )

    def exists(self, session_id: str) -> bool:
        """Check if session exists (delegates to underlying store)."""
        return self.store.exists(session_id)

    def cleanup(self) -> int:
        """Cleanup expired sessions (delegates to underlying store)."""
        return self.store.cleanup()

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List sessions (delegates to underlying store)."""
        return self.store.list_sessions(namespace=namespace, limit=limit, offset=offset)


__all__ = [
    "FileSessionStore",
    "HookedSessionStore",
    "MemorySessionStore",
    "RedisSessionStore",
    "SessionStore",
]
