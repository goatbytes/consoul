"""Tests for circuit breaker functionality (SOUL-342).

Tests the circuit breaker pattern for LLM provider resilience.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from consoul.server.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
)
from consoul.server.models import CircuitBreakerConfig


class TestCircuitBreakerConfig:
    """Test CircuitBreakerConfig model."""

    def test_default_values(self) -> None:
        """Config has sensible defaults."""
        config = CircuitBreakerConfig()
        assert config.enabled is True
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout == 60
        assert config.half_open_max_calls == 3

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = CircuitBreakerConfig(
            enabled=False,
            failure_threshold=10,
            success_threshold=5,
            timeout=120,
            half_open_max_calls=5,
        )
        assert config.enabled is False
        assert config.failure_threshold == 10
        assert config.success_threshold == 5
        assert config.timeout == 120
        assert config.half_open_max_calls == 5

    def test_validation_constraints(self) -> None:
        """Config validates field constraints."""
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

        with pytest.raises(ValueError):
            CircuitBreakerConfig(timeout=4)


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self) -> None:
        """Circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED

    def test_closed_to_open_after_threshold_failures(self) -> None:
        """Circuit opens after failure_threshold failures."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.stats.trips_total == 1

    def test_open_to_half_open_after_timeout(self) -> None:
        """Circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker("test", failure_threshold=1, timeout=1)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker._stats.last_failure_time = time.monotonic() - 2

        assert breaker._should_allow_request() is True
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_after_success_threshold(self) -> None:
        """Circuit closes after success_threshold successes in HALF_OPEN."""
        breaker = CircuitBreaker("test", failure_threshold=1, success_threshold=2)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker._transition_to(CircuitState.HALF_OPEN)
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_success()
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self) -> None:
        """Circuit reopens immediately on failure in HALF_OPEN."""
        breaker = CircuitBreaker("test", failure_threshold=1)

        breaker.record_failure()
        breaker._transition_to(CircuitState.HALF_OPEN)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.stats.trips_total == 2


class TestCircuitBreakerRequestHandling:
    """Test request allow/reject behavior."""

    def test_closed_allows_requests(self) -> None:
        """CLOSED state allows all requests."""
        breaker = CircuitBreaker("test")
        assert breaker._should_allow_request() is True

    def test_open_rejects_requests(self) -> None:
        """OPEN state rejects requests."""
        breaker = CircuitBreaker("test", failure_threshold=1)
        breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
        assert breaker._should_allow_request() is False

    def test_half_open_allows_limited_requests(self) -> None:
        """HALF_OPEN allows up to half_open_max_calls requests."""
        breaker = CircuitBreaker("test", failure_threshold=1, half_open_max_calls=2)

        breaker.record_failure()
        breaker._transition_to(CircuitState.HALF_OPEN)

        assert breaker._should_allow_request() is True
        assert breaker._should_allow_request() is True
        assert breaker._should_allow_request() is False


class TestCircuitBreakerAsyncGenerator:
    """Test async generator wrapping."""

    @pytest.mark.asyncio
    async def test_successful_generator_records_success(self) -> None:
        """Successful generator execution records success."""
        breaker = CircuitBreaker("test")

        async def successful_gen() -> AsyncIterator[str]:
            yield "hello"
            yield "world"

        results = []
        async for item in breaker.call_async_generator(successful_gen):
            results.append(item)

        assert results == ["hello", "world"]
        assert breaker.stats.success_count == 1

    @pytest.mark.asyncio
    async def test_failed_generator_records_failure(self) -> None:
        """Failed generator execution records failure."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        async def failing_gen() -> AsyncIterator[str]:
            yield "start"
            raise ValueError("simulated failure")

        results = []
        with pytest.raises(ValueError, match="simulated failure"):
            async for item in breaker.call_async_generator(failing_gen):
                results.append(item)

        assert results == ["start"]
        assert breaker.stats.failure_count == 1

    @pytest.mark.asyncio
    async def test_open_breaker_raises_circuit_breaker_error(self) -> None:
        """Open circuit breaker raises CircuitBreakerError."""
        breaker = CircuitBreaker("test", failure_threshold=1, timeout=60)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        async def gen() -> AsyncIterator[str]:
            yield "should not run"

        with pytest.raises(CircuitBreakerError) as exc_info:
            async for _ in breaker.call_async_generator(gen):
                pass

        assert exc_info.value.provider == "test"
        assert exc_info.value.state == CircuitState.OPEN
        assert exc_info.value.retry_after > 0
        assert breaker.stats.rejections_total == 1


class TestCircuitBreakerMetrics:
    """Test metrics callback integration."""

    def test_metrics_callback_on_open(self) -> None:
        """Metrics callback called when circuit opens."""
        callback_calls: list[tuple[str, CircuitState]] = []

        def callback(provider: str, state: CircuitState) -> None:
            callback_calls.append((provider, state))

        breaker = CircuitBreaker(
            "openai", failure_threshold=1, metrics_callback=callback
        )
        breaker.record_failure()

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("openai", CircuitState.OPEN)

    def test_metrics_callback_on_closed(self) -> None:
        """Metrics callback called when circuit recovers to CLOSED."""
        callback_calls: list[tuple[str, CircuitState]] = []

        def callback(provider: str, state: CircuitState) -> None:
            callback_calls.append((provider, state))

        breaker = CircuitBreaker(
            "google",
            failure_threshold=1,
            success_threshold=1,
            metrics_callback=callback,
        )

        breaker.record_failure()
        breaker._transition_to(CircuitState.HALF_OPEN)
        callback_calls.clear()

        breaker.record_success()

        assert len(callback_calls) == 1
        assert callback_calls[0] == ("google", CircuitState.CLOSED)


class TestCircuitBreakerManager:
    """Test per-provider circuit breaker management."""

    @pytest.mark.asyncio
    async def test_get_breaker_creates_new(self) -> None:
        """get_breaker creates new breaker for unknown provider."""
        manager = CircuitBreakerManager()

        breaker = await manager.get_breaker("openai")
        assert breaker.provider == "openai"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_get_breaker_returns_same_instance(self) -> None:
        """get_breaker returns same instance for same provider."""
        manager = CircuitBreakerManager()

        breaker1 = await manager.get_breaker("anthropic")
        breaker2 = await manager.get_breaker("anthropic")

        assert breaker1 is breaker2

    @pytest.mark.asyncio
    async def test_providers_are_isolated(self) -> None:
        """Different providers have independent circuit breakers."""
        manager = CircuitBreakerManager(failure_threshold=1)

        openai = await manager.get_breaker("openai")
        anthropic = await manager.get_breaker("anthropic")

        openai.record_failure()
        assert openai.state == CircuitState.OPEN
        assert anthropic.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_get_all_states(self) -> None:
        """get_all_states returns state of all breakers."""
        manager = CircuitBreakerManager(failure_threshold=1)

        await manager.get_breaker("openai")
        anthropic = await manager.get_breaker("anthropic")
        anthropic.record_failure()

        states = manager.get_all_states()

        assert states["openai"] == CircuitState.CLOSED
        assert states["anthropic"] == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reset_all_resets_all_breakers(self) -> None:
        """reset_all resets all breakers to CLOSED."""
        manager = CircuitBreakerManager(failure_threshold=1)

        openai = await manager.get_breaker("openai")
        anthropic = await manager.get_breaker("anthropic")

        openai.record_failure()
        anthropic.record_failure()

        manager.reset_all()

        assert openai.state == CircuitState.CLOSED
        assert anthropic.state == CircuitState.CLOSED


class TestCircuitBreakerError:
    """Test CircuitBreakerError exception."""

    def test_error_attributes(self) -> None:
        """CircuitBreakerError has correct attributes."""
        error = CircuitBreakerError("openai", CircuitState.OPEN, 45)

        assert error.provider == "openai"
        assert error.state == CircuitState.OPEN
        assert error.retry_after == 45
        assert "OPEN" in str(error)
        assert "openai" in str(error)


class TestCircuitBreakerReset:
    """Test circuit breaker reset functionality."""

    def test_reset_clears_state(self) -> None:
        """reset() clears state and statistics."""
        breaker = CircuitBreaker("test", failure_threshold=1)

        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.failure_count == 0
        assert breaker.stats.trips_total == 0
