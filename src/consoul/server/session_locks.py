"""Per-session async lock manager for request serialization.

This module provides application-level locking to ensure that concurrent
requests to the same session_id are serialized, preventing race conditions
in the load→chat→save flow.

The SessionStore implementations provide per-operation locking, but that's
insufficient for HTTP endpoints where the full request flow must be atomic.

Example:
    >>> from consoul.server.session_locks import SessionLockManager, SessionLock
    >>>
    >>> lock_manager = SessionLockManager()
    >>>
    >>> async def chat_handler(session_id: str):
    ...     async with SessionLock(lock_manager, session_id):
    ...         # This block is atomic per session_id
    ...         state = store.load(session_id)
    ...         response = console.chat(message)
    ...         store.save(session_id, new_state)

Security Notes:
    - Lock cleanup prevents memory exhaustion from abandoned sessions
    - Reference counting ensures locks are only released when fully unused
    - The manager lock prevents race conditions during acquire/release
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

__all__ = ["SessionLock", "SessionLockManager"]


class SessionLockManager:
    """Manages per-session async locks to prevent concurrent request races.

    Ensures the load→chat→save sequence is atomic per session_id. Uses
    reference counting to automatically clean up locks for inactive sessions.

    Attributes:
        _locks: Dictionary mapping session_id to asyncio.Lock
        _lock_counts: Reference count for each session lock
        _manager_lock: Global lock protecting internal state

    Example:
        >>> manager = SessionLockManager()
        >>> async with SessionLock(manager, "user123"):
        ...     # Exclusive access to session "user123"
        ...     pass
    """

    def __init__(self) -> None:
        """Initialize the session lock manager."""
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._lock_counts: dict[str, int] = defaultdict(int)
        self._manager_lock = asyncio.Lock()

    async def acquire(self, session_id: str) -> asyncio.Lock:
        """Get or create lock for session_id.

        Increments the reference count for the session's lock.

        Args:
            session_id: Unique session identifier

        Returns:
            asyncio.Lock for the specified session
        """
        async with self._manager_lock:
            self._lock_counts[session_id] += 1
            return self._locks[session_id]

    async def release(self, session_id: str) -> None:
        """Release lock and cleanup if no longer needed.

        Decrements the reference count. If count reaches zero, removes
        the lock from memory to prevent unbounded growth.

        Args:
            session_id: Unique session identifier
        """
        async with self._manager_lock:
            self._lock_counts[session_id] -= 1
            if self._lock_counts[session_id] <= 0:
                self._locks.pop(session_id, None)
                self._lock_counts.pop(session_id, None)
                logger.debug(f"Cleaned up lock for session: {session_id}")

    def active_sessions(self) -> int:
        """Return count of sessions with active locks.

        Returns:
            Number of session_ids currently holding locks
        """
        return len(self._locks)


class SessionLock:
    """Async context manager for per-session locking.

    Provides a convenient way to acquire exclusive access to a session
    for the duration of a request.

    Attributes:
        manager: The SessionLockManager instance
        session_id: The session to lock
        _lock: The acquired asyncio.Lock (set during __aenter__)

    Example:
        >>> manager = SessionLockManager()
        >>> async with SessionLock(manager, "user123"):
        ...     # All operations here are serialized per session
        ...     state = await asyncio.to_thread(store.load, "user123")
        ...     response = await asyncio.to_thread(console.chat, message)
        ...     await asyncio.to_thread(store.save, "user123", new_state)
    """

    def __init__(self, manager: SessionLockManager, session_id: str) -> None:
        """Initialize session lock.

        Args:
            manager: The SessionLockManager to use
            session_id: The session identifier to lock
        """
        self.manager = manager
        self.session_id = session_id
        self._lock: asyncio.Lock | None = None

    async def __aenter__(self) -> SessionLock:
        """Acquire the session lock.

        Returns:
            self for use in async with statements
        """
        self._lock = await self.manager.acquire(self.session_id)
        await self._lock.acquire()
        logger.debug(f"Acquired lock for session: {self.session_id}")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Release the session lock.

        Always releases the lock, even if an exception occurred.

        Args:
            exc_type: Exception type if one was raised
            exc_val: Exception instance if one was raised
            exc_tb: Traceback if an exception was raised
        """
        if self._lock is not None:
            self._lock.release()
            logger.debug(f"Released lock for session: {self.session_id}")
        await self.manager.release(self.session_id)
