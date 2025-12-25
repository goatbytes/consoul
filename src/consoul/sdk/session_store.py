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

    def cleanup(self) -> int:
        """Redis handles expiration automatically via TTL.

        Returns:
            Always returns 0 (Redis auto-expires keys)

        Note:
            Redis automatically removes expired keys. This method is a no-op
            for compatibility with the SessionStore protocol.
        """
        return 0


__all__ = [
    "FileSessionStore",
    "MemorySessionStore",
    "RedisSessionStore",
    "SessionStore",
]
