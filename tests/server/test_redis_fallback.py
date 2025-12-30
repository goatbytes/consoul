"""Tests for Redis fallback functionality (SOUL-328).

Tests the graceful Redis degradation with automatic fallback to in-memory storage.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from consoul.server import create_server
from consoul.server.models import RateLimitConfig, ServerConfig, SessionConfig
from consoul.server.resilient_store import ResilientSessionStore


class TestRedisFallbackDisabled:
    """Test default fail-fast behavior (fallback_enabled=False)."""

    def test_redis_unavailable_raises_runtime_error(self) -> None:
        """Server fails to start when Redis unavailable and fallback disabled."""
        config = ServerConfig(
            session=SessionConfig(
                redis_url="redis://localhost:59999",  # Invalid port
                fallback_enabled=False,
            )
        )
        with pytest.raises(
            RuntimeError, match="Redis session store configured but unavailable"
        ):
            create_server(config)

    def test_default_fallback_is_false(self) -> None:
        """Verify fallback_enabled defaults to False."""
        config = SessionConfig()
        assert config.fallback_enabled is False


class TestRedisFallbackEnabled:
    """Test graceful degradation (fallback_enabled=True)."""

    def test_redis_unavailable_starts_in_degraded_mode(self) -> None:
        """Server starts with memory store when Redis unavailable."""
        config = ServerConfig(
            session=SessionConfig(
                redis_url="redis://localhost:59999",  # Invalid port
                fallback_enabled=True,
            )
        )
        app = create_server(config)
        assert hasattr(app.state.session_store, "mode")
        assert app.state.session_store.mode == "degraded"

    def test_ready_endpoint_shows_degraded(self) -> None:
        """Readiness endpoint returns 200 with degraded status."""
        config = ServerConfig(
            session=SessionConfig(
                redis_url="redis://localhost:59999",
                fallback_enabled=True,
            )
        )
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["checks"].get("session_store") == "degraded"
        assert data.get("message") == "Running in fallback mode"

    def test_health_endpoint_unaffected(self) -> None:
        """Health endpoint works normally in degraded mode."""
        config = ServerConfig(
            session=SessionConfig(
                redis_url="redis://localhost:59999",
                fallback_enabled=True,
            )
        )
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestResilientSessionStore:
    """Test ResilientSessionStore wrapper class."""

    def test_initialization_with_unavailable_redis_and_fallback_enabled(self) -> None:
        """Falls back to memory when Redis unavailable and fallback enabled."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
        )
        assert store.mode == "degraded"

    def test_initialization_with_unavailable_redis_and_fallback_disabled(self) -> None:
        """Raises RuntimeError when Redis unavailable and fallback disabled."""
        with pytest.raises(
            RuntimeError, match="Redis session store configured but unavailable"
        ):
            ResilientSessionStore(
                redis_url="redis://localhost:59999",
                ttl=3600,
                prefix="test:",
                fallback_enabled=False,
                reconnect_interval=60,
            )

    def test_save_and_load_in_degraded_mode(self) -> None:
        """Sessions work correctly in degraded mode."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
        )

        # Save a session
        store.save("test-session-1", {"data": "test-value"})

        # Load it back
        state = store.load("test-session-1")
        assert state is not None
        assert state["data"] == "test-value"

    def test_delete_in_degraded_mode(self) -> None:
        """Delete works in degraded mode."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
        )

        store.save("test-session-2", {"data": "test"})
        assert store.exists("test-session-2")

        store.delete("test-session-2")
        assert not store.exists("test-session-2")

    def test_exists_in_degraded_mode(self) -> None:
        """Exists works in degraded mode."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
        )

        assert not store.exists("nonexistent")
        store.save("existing", {"data": "test"})
        assert store.exists("existing")

    def test_list_sessions_in_degraded_mode(self) -> None:
        """List sessions works in degraded mode."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
        )

        store.save("session-a", {"data": "a"})
        store.save("session-b", {"data": "b"})

        sessions = store.list_sessions(limit=100)
        assert "session-a" in sessions
        assert "session-b" in sessions

    def test_recovery_respects_interval(self) -> None:
        """Recovery attempts respect the reconnect_interval."""
        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=10,  # 10 second interval
        )

        # Record the last check time
        last_check = store._last_check

        # Try recovery immediately - should not attempt (interval not elapsed)
        result = store._try_recover()
        assert result is False
        assert store._last_check == last_check  # Should not have updated

        # Simulate time passing
        store._last_check = time.monotonic() - 15  # 15 seconds ago

        # Now try_recover should attempt (and fail since Redis is down)
        result = store._try_recover()
        assert result is False
        assert store._last_check > last_check  # Should have updated

    def test_metrics_callback_called_on_degradation(self) -> None:
        """Metrics callback is called when entering degraded mode."""
        callback = MagicMock()

        store = ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
            metrics_callback=callback,
        )

        assert store.mode == "degraded"
        callback.assert_called_once_with("degraded", True)


class TestSessionConfigModel:
    """Test SessionConfig model fields."""

    def test_fallback_enabled_default_false(self) -> None:
        """fallback_enabled defaults to False."""
        config = SessionConfig()
        assert config.fallback_enabled is False

    def test_reconnect_interval_default_60(self) -> None:
        """reconnect_interval defaults to 60."""
        config = SessionConfig()
        assert config.reconnect_interval == 60

    def test_reconnect_interval_min_10(self) -> None:
        """reconnect_interval minimum is 10."""
        with pytest.raises(ValueError):
            SessionConfig(reconnect_interval=5)

    def test_reconnect_interval_max_3600(self) -> None:
        """reconnect_interval maximum is 3600."""
        with pytest.raises(ValueError):
            SessionConfig(reconnect_interval=7200)

    def test_valid_reconnect_interval(self) -> None:
        """Valid reconnect_interval values are accepted."""
        config = SessionConfig(reconnect_interval=120)
        assert config.reconnect_interval == 120


class TestRateLimitConfigModel:
    """Test RateLimitConfig model fields."""

    def test_fallback_enabled_default_false(self) -> None:
        """fallback_enabled defaults to False."""
        config = RateLimitConfig()
        assert config.fallback_enabled is False

    def test_reconnect_interval_default_60(self) -> None:
        """reconnect_interval defaults to 60."""
        config = RateLimitConfig()
        assert config.reconnect_interval == 60

    def test_reconnect_interval_constraints(self) -> None:
        """reconnect_interval has proper constraints."""
        with pytest.raises(ValueError):
            RateLimitConfig(reconnect_interval=5)

        with pytest.raises(ValueError):
            RateLimitConfig(reconnect_interval=7200)

        # Valid value
        config = RateLimitConfig(reconnect_interval=300)
        assert config.reconnect_interval == 300


class TestMetricsCallbackIntegration:
    """Test metrics callback integration with ResilientSessionStore."""

    def test_callback_format(self) -> None:
        """Verify callback receives correct parameters."""
        events = []

        def capture_callback(event: str, value: bool) -> None:
            events.append((event, value))

        ResilientSessionStore(
            redis_url="redis://localhost:59999",
            ttl=3600,
            prefix="test:",
            fallback_enabled=True,
            reconnect_interval=60,
            metrics_callback=capture_callback,
        )

        assert len(events) == 1
        assert events[0] == ("degraded", True)
