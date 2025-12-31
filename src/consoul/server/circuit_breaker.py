"""Circuit breaker pattern for LLM provider resilience.

SOUL-342: Protect against cascading failures when LLM providers are unavailable.

The circuit breaker pattern prevents repeated calls to a failing service,
allowing it time to recover while providing fast-fail responses to clients.

State Machine:
    CLOSED: Normal operation, failures are counted
    OPEN: Fast-fail all requests, timer running until half-open
    HALF_OPEN: Limited test requests allowed to probe recovery

Example:
    >>> from consoul.server.circuit_breaker import CircuitBreakerManager
    >>>
    >>> manager = CircuitBreakerManager(failure_threshold=5, timeout=60)
    >>> breaker = await manager.get_breaker("openai")
    >>>
    >>> # Wrap LLM calls with circuit breaker protection
    >>> async for chunk in breaker.call_async_generator(model.astream, messages):
    ...     yield chunk

Environment Variables:
    CONSOUL_CIRCUIT_BREAKER_ENABLED: Enable circuit breaker (default: true)
    CONSOUL_CIRCUIT_BREAKER_FAILURE_THRESHOLD: Failures before open (default: 5)
    CONSOUL_CIRCUIT_BREAKER_SUCCESS_THRESHOLD: Successes to close (default: 3)
    CONSOUL_CIRCUIT_BREAKER_TIMEOUT: Seconds before half-open (default: 60)
    CONSOUL_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: Test requests in half-open (default: 3)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

logger = logging.getLogger(__name__)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerManager",
    "CircuitBreakerStats",
    "CircuitState",
]

T = TypeVar("T")


class CircuitState(IntEnum):
    """Circuit breaker states.

    Values match Prometheus metric encoding:
        0 = CLOSED (normal operation)
        1 = HALF_OPEN (testing recovery)
        2 = OPEN (fast-failing)
    """

    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2


@dataclass
class CircuitBreakerStats:
    """Statistics for a single circuit breaker.

    Attributes:
        failure_count: Consecutive failures in current period
        success_count: Consecutive successes (used in half-open state)
        last_failure_time: Monotonic timestamp of last failure
        trips_total: Total times circuit has tripped to OPEN
        rejections_total: Total requests rejected while OPEN
    """

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    trips_total: int = 0
    rejections_total: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit breaker prevents request execution.

    Attributes:
        provider: LLM provider name
        state: Current circuit breaker state
        retry_after: Seconds until client should retry
    """

    def __init__(self, provider: str, state: CircuitState, retry_after: int) -> None:
        """Initialize circuit breaker error.

        Args:
            provider: LLM provider name (e.g., "openai")
            state: Current circuit state
            retry_after: Seconds until retry recommended
        """
        self.provider = provider
        self.state = state
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker {state.name} for {provider}")


class CircuitBreaker:
    """Circuit breaker for a single LLM provider.

    Implements the circuit breaker pattern with three states:
    - CLOSED: Normal operation, tracking failures
    - OPEN: Fast-failing all requests
    - HALF_OPEN: Testing recovery with limited requests

    Thread-safe via asyncio.Lock for state transitions.

    Example:
        >>> breaker = CircuitBreaker("openai", failure_threshold=5)
        >>> async for chunk in breaker.call_async_generator(model.astream, messages):
        ...     yield chunk
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: int = 60,
        half_open_max_calls: int = 3,
        metrics_callback: Callable[[str, CircuitState], None] | None = None,
        rejection_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize circuit breaker for a provider.

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")
            failure_threshold: Consecutive failures before opening circuit
            success_threshold: Successes in half-open required to close
            timeout: Seconds before transitioning from OPEN to HALF_OPEN
            half_open_max_calls: Maximum test requests in HALF_OPEN state
            metrics_callback: Optional callback for state transitions
            rejection_callback: Optional callback for rejected requests
        """
        self._provider = provider
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout
        self._half_open_max_calls = half_open_max_calls
        self._metrics_callback = metrics_callback
        self._rejection_callback = rejection_callback

        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def provider(self) -> str:
        """Get provider name."""
        return self._provider

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get current statistics."""
        return self._stats

    def _should_allow_request(self) -> bool:
        """Check if request should be allowed based on current state.

        Handles automatic transition from OPEN to HALF_OPEN when timeout elapses.

        Returns:
            True if request should proceed, False to reject
        """
        now = time.monotonic()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # Check if timeout has elapsed for transition to HALF_OPEN
            if now - self._stats.last_failure_time >= self._timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        # HALF_OPEN: Allow limited test requests
        if self._half_open_calls < self._half_open_max_calls:
            self._half_open_calls += 1
            return True
        return False

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state with logging and metrics.

        Args:
            new_state: Target circuit state
        """
        if self._state == new_state:
            return

        self._state = new_state

        if new_state == CircuitState.OPEN:
            self._stats.trips_total += 1
            logger.warning(
                "Circuit breaker OPEN for %s (failures: %d, total trips: %d)",
                self._provider,
                self._stats.failure_count,
                self._stats.trips_total,
            )
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._stats.success_count = 0
            logger.info(
                "Circuit breaker HALF_OPEN for %s (testing recovery)",
                self._provider,
            )
        elif new_state == CircuitState.CLOSED:
            self._stats.failure_count = 0
            self._stats.success_count = 0
            logger.info(
                "Circuit breaker CLOSED for %s (recovered after %d successes)",
                self._provider,
                self._success_threshold,
            )

        if self._metrics_callback:
            try:
                self._metrics_callback(self._provider, new_state)
            except Exception as e:
                logger.debug("Metrics callback failed: %s", e)

    def record_success(self) -> None:
        """Record successful request.

        In HALF_OPEN state, transitions to CLOSED after success_threshold successes.
        """
        self._stats.success_count += 1

        if (
            self._state == CircuitState.HALF_OPEN
            and self._stats.success_count >= self._success_threshold
        ):
            self._transition_to(CircuitState.CLOSED)

    def record_failure(self, error: Exception | None = None) -> None:
        """Record failed request.

        In CLOSED state, transitions to OPEN after failure_threshold failures.
        In HALF_OPEN state, immediately transitions back to OPEN.

        Args:
            error: Optional exception that caused the failure
        """
        self._stats.failure_count += 1
        self._stats.last_failure_time = time.monotonic()

        if error:
            logger.debug(
                "Circuit breaker %s recorded failure: %s",
                self._provider,
                type(error).__name__,
            )

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open immediately reopens
            self._transition_to(CircuitState.OPEN)
        elif (
            self._state == CircuitState.CLOSED
            and self._stats.failure_count >= self._failure_threshold
        ):
            self._transition_to(CircuitState.OPEN)

    async def call_async_generator(
        self,
        func: Callable[..., AsyncIterator[T]],
        *args: Any,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Execute async generator with circuit breaker protection.

        Wraps an async generator function (like model.astream) with circuit
        breaker logic. Rejects requests when circuit is OPEN, tracks failures
        and successes for state transitions.

        Args:
            func: Async generator function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Yields:
            Items from the async generator

        Raises:
            CircuitBreakerError: When circuit is OPEN or HALF_OPEN at capacity
        """
        async with self._lock:
            if not self._should_allow_request():
                self._stats.rejections_total += 1
                # Notify metrics of rejection
                if self._rejection_callback:
                    try:
                        self._rejection_callback(self._provider)
                    except Exception as e:
                        logger.debug("Rejection callback failed: %s", e)
                retry_after = max(
                    0,
                    int(
                        self._timeout
                        - (time.monotonic() - self._stats.last_failure_time)
                    ),
                )
                raise CircuitBreakerError(self._provider, self._state, retry_after)

        try:
            async for item in func(*args, **kwargs):
                yield item
            self.record_success()
        except CircuitBreakerError:
            # Don't double-count circuit breaker errors
            raise
        except Exception as e:
            self.record_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state.

        Useful for testing or manual intervention.
        """
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._half_open_calls = 0
        logger.info("Circuit breaker %s manually reset to CLOSED", self._provider)


class CircuitBreakerManager:
    """Manages per-provider circuit breakers.

    Creates and maintains circuit breakers for each LLM provider,
    ensuring provider-specific isolation (OpenAI down != Anthropic down).

    Thread-safe via asyncio.Lock for breaker creation.

    Example:
        >>> manager = CircuitBreakerManager(failure_threshold=5, timeout=60)
        >>> breaker = await manager.get_breaker("openai")
        >>> states = manager.get_all_states()
        >>> print(states)  # {"openai": CircuitState.CLOSED}
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout: int = 60,
        half_open_max_calls: int = 3,
        metrics_callback: Callable[[str, CircuitState], None] | None = None,
        rejection_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize circuit breaker manager.

        Args:
            failure_threshold: Failures before opening (applies to all breakers)
            success_threshold: Successes to close (applies to all breakers)
            timeout: Seconds before half-open (applies to all breakers)
            half_open_max_calls: Test requests in half-open (applies to all breakers)
            metrics_callback: Callback for state transitions (provider, state)
            rejection_callback: Callback for rejected requests (provider)
        """
        self._failure_threshold = failure_threshold
        self._success_threshold = success_threshold
        self._timeout = timeout
        self._half_open_max_calls = half_open_max_calls
        self._metrics_callback = metrics_callback
        self._rejection_callback = rejection_callback
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(self, provider: str) -> CircuitBreaker:
        """Get or create circuit breaker for provider.

        Creates a new breaker on first access for a provider.
        Subsequent calls return the same breaker instance.

        Args:
            provider: LLM provider name (e.g., "openai", "anthropic")

        Returns:
            CircuitBreaker instance for the provider
        """
        if provider not in self._breakers:
            async with self._lock:
                # Double-check pattern for thread safety
                if provider not in self._breakers:
                    self._breakers[provider] = CircuitBreaker(
                        provider=provider,
                        failure_threshold=self._failure_threshold,
                        success_threshold=self._success_threshold,
                        timeout=self._timeout,
                        half_open_max_calls=self._half_open_max_calls,
                        metrics_callback=self._metrics_callback,
                        rejection_callback=self._rejection_callback,
                    )
                    logger.debug("Created circuit breaker for provider: %s", provider)
        return self._breakers[provider]

    def get_all_states(self) -> dict[str, CircuitState]:
        """Get current state of all circuit breakers.

        Returns:
            Dictionary mapping provider name to current state
        """
        return {name: breaker.state for name, breaker in self._breakers.items()}

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers.

        Returns:
            Dictionary mapping provider name to stats
        """
        return {name: breaker.stats for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset to CLOSED")
