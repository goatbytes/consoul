"""Resilient session store with automatic Redis fallback and recovery.

SOUL-328: Add graceful Redis degradation with fallback to in-memory storage.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

    from consoul.sdk.session_store import MemorySessionStore, RedisSessionStore

logger = logging.getLogger(__name__)


class ResilientSessionStore:
    """SessionStore wrapper with automatic Redis fallback and recovery.

    When Redis is unavailable:
    - Falls back to in-memory storage if fallback_enabled=True
    - Periodically attempts reconnection at reconnect_interval
    - Logs state transitions (WARNING on degradation, INFO on recovery)
    - Emits metrics for monitoring via callback

    Mode transitions:
    - "redis": Primary Redis store active
    - "degraded": Started with Redis config but using memory fallback
    - "memory": No Redis configured, using memory only (not used by this class)

    Example:
        >>> store = ResilientSessionStore(
        ...     redis_url="redis://localhost:6379",
        ...     ttl=3600,
        ...     prefix="consoul:session:",
        ...     fallback_enabled=True,
        ...     reconnect_interval=60,
        ... )
        >>> store.mode  # "redis" or "degraded"
    """

    def __init__(
        self,
        redis_url: str,
        ttl: int,
        prefix: str,
        fallback_enabled: bool,
        reconnect_interval: int,
        metrics_callback: Callable[[str, bool], None] | None = None,
    ) -> None:
        """Initialize resilient session store.

        Args:
            redis_url: Redis connection URL.
            ttl: Session time-to-live in seconds.
            prefix: Redis key prefix for sessions.
            fallback_enabled: Whether to fall back to memory on Redis failure.
            reconnect_interval: Seconds between reconnection attempts.
            metrics_callback: Optional callback for metrics events.
                Called with ("degraded", True) when entering degraded mode,
                ("recovered", True) when Redis recovers.

        Raises:
            RuntimeError: If Redis unavailable and fallback_enabled=False.
        """
        self._redis_url = redis_url
        self._ttl = ttl
        self._prefix = prefix
        self._fallback_enabled = fallback_enabled
        self._reconnect_interval = reconnect_interval
        self._metrics_callback = metrics_callback

        self._mode: Literal["redis", "degraded"] = "redis"
        self._primary: RedisSessionStore | None = None
        self._fallback: MemorySessionStore | None = None
        self._last_check: float = 0.0
        self._was_connected: bool = False  # Track if we ever had Redis working

        self._initialize()

    def _initialize(self) -> None:
        """Try to connect to Redis, fall back to memory if enabled."""
        try:
            import redis

            from consoul.sdk.session_store import RedisSessionStore

            redis_client = redis.from_url(self._redis_url)
            redis_client.ping()  # Verify connection

            self._primary = RedisSessionStore(
                redis_client=redis_client,
                ttl=self._ttl,
                prefix=self._prefix,
            )
            self._mode = "redis"
            self._was_connected = True
            logger.info(f"Session store: Redis ({self._redis_url})")

        except Exception as e:
            if not self._fallback_enabled:
                raise RuntimeError(
                    f"Redis session store configured but unavailable: {e}. "
                    "Set CONSOUL_SESSION_REDIS_URL='' to use in-memory storage, "
                    "or set CONSOUL_REDIS_FALLBACK_ENABLED=true for degraded mode."
                ) from e

            from consoul.sdk.session_store import MemorySessionStore

            self._fallback = MemorySessionStore(ttl=self._ttl)
            self._mode = "degraded"
            self._last_check = time.monotonic()

            logger.warning(
                "Redis unavailable - running in degraded mode with in-memory storage. "
                "Sessions will not persist across restarts."
            )
            if self._metrics_callback:
                self._metrics_callback("degraded", True)

    @property
    def mode(self) -> Literal["redis", "degraded"]:
        """Current operating mode."""
        return self._mode

    @property
    def active_store(self) -> Any:
        """Return the currently active store."""
        if self._mode == "redis" and self._primary:
            return self._primary
        return self._fallback

    def _try_recover(self) -> bool:
        """Attempt to reconnect to Redis. Returns True if successful.

        Only attempts reconnection if reconnect_interval has elapsed since
        the last check. This prevents excessive connection attempts.
        """
        now = time.monotonic()
        if now - self._last_check < self._reconnect_interval:
            return False

        self._last_check = now

        try:
            import redis

            from consoul.sdk.session_store import RedisSessionStore

            redis_client = redis.from_url(self._redis_url)
            redis_client.ping()

            self._primary = RedisSessionStore(
                redis_client=redis_client,
                ttl=self._ttl,
                prefix=self._prefix,
            )
            self._mode = "redis"
            self._was_connected = True

            logger.info("Redis connection recovered")
            if self._metrics_callback:
                self._metrics_callback("recovered", True)

            return True
        except Exception:
            return False

    def _ensure_fallback(self) -> None:
        """Ensure fallback store exists (lazy initialization)."""
        if self._fallback is None:
            from consoul.sdk.session_store import MemorySessionStore

            self._fallback = MemorySessionStore(ttl=self._ttl)

    def _handle_redis_failure(self, operation: str, error: Exception) -> None:
        """Handle Redis failure during operation.

        If fallback is enabled, switches to degraded mode. Otherwise re-raises.

        Args:
            operation: Name of the operation that failed (for logging).
            error: The exception that occurred.

        Raises:
            Exception: Re-raises if fallback is disabled.
        """
        if not self._fallback_enabled:
            raise error

        # Switch to degraded mode
        if self._mode == "redis":
            self._mode = "degraded"
            self._last_check = time.monotonic()
            self._ensure_fallback()

            if self._was_connected:
                # We had Redis working before - sessions are lost
                logger.critical(
                    "Redis connection lost - existing sessions are unavailable. "
                    "New sessions will use in-memory storage (not distributed)."
                )
            else:
                logger.warning(
                    f"Redis {operation} failed - using in-memory fallback. "
                    "Sessions will not persist across restarts."
                )

            if self._metrics_callback:
                self._metrics_callback("degraded", True)

    # -------------------------------------------------------------------------
    # SessionStore Protocol Methods - Delegate to active store
    # -------------------------------------------------------------------------

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        """Save session state.

        In degraded mode, attempts recovery before each operation.
        """
        if self._mode == "degraded":
            self._try_recover()

        try:
            self.active_store.save(session_id, state)
        except Exception as e:
            self._handle_redis_failure("save", e)
            # Retry with fallback store
            self.active_store.save(session_id, state)

    def load(self, session_id: str) -> dict[str, Any] | None:
        """Load session state.

        In degraded mode, attempts recovery before each operation.
        """
        if self._mode == "degraded":
            self._try_recover()

        try:
            return self.active_store.load(session_id)  # type: ignore[no-any-return]
        except Exception as e:
            self._handle_redis_failure("load", e)
            return self.active_store.load(session_id)  # type: ignore[no-any-return]

    def delete(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            return self.active_store.delete(session_id)  # type: ignore[no-any-return]
        except Exception as e:
            self._handle_redis_failure("delete", e)
            return self.active_store.delete(session_id)  # type: ignore[no-any-return]

    def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        try:
            return self.active_store.exists(session_id)  # type: ignore[no-any-return]
        except Exception as e:
            self._handle_redis_failure("exists", e)
            return self.active_store.exists(session_id)  # type: ignore[no-any-return]

    def cleanup(self) -> int:
        """Clean up expired sessions."""
        try:
            return self.active_store.cleanup()  # type: ignore[no-any-return]
        except Exception as e:
            self._handle_redis_failure("cleanup", e)
            return self.active_store.cleanup()  # type: ignore[no-any-return]

    def list_sessions(
        self,
        namespace: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List session IDs."""
        try:
            return self.active_store.list_sessions(namespace, limit, offset)  # type: ignore[no-any-return]
        except Exception as e:
            self._handle_redis_failure("list_sessions", e)
            return self.active_store.list_sessions(namespace, limit, offset)  # type: ignore[no-any-return]
