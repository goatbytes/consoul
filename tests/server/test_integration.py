"""Integration tests for server HTTP and WebSocket endpoints (SOUL-330).

Comprehensive integration test suite that verifies full request/response flows
with mocked LLM providers. Tests cover HTTP and WebSocket endpoints with various
server configurations (auth, rate limiting, sessions).

Run integration tests only:
    pytest -m integration tests/server/test_integration.py

Run all tests except integration:
    pytest -m "not integration"
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from consoul.server import create_server
from consoul.server.models import RateLimitConfig, SecurityConfig, ServerConfig

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_console() -> MagicMock:
    """Create a mock Consoul instance with standard responses."""
    console = MagicMock()
    console.chat.return_value = "Hello! I'm an AI assistant."
    console.last_cost = {
        "input_tokens": 10,
        "output_tokens": 20,
        "total_tokens": 30,
        "estimated_cost": 0.0003,
    }
    console.model_name = "gpt-4o-mini"
    return console


# =============================================================================
# Health/Ready Endpoint Tests
# =============================================================================


@pytest.mark.integration
class TestHealthEndpoints:
    """Integration tests for health and readiness endpoints."""

    def test_health_returns_ok_with_required_fields(self) -> None:
        """GET /health returns 200 with status, service, version, timestamp."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_bypasses_auth(self) -> None:
        """Health endpoint works without authentication."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_ready_returns_checks(self) -> None:
        """GET /ready returns 200 with dependency checks."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data


# =============================================================================
# Authentication Tests
# =============================================================================


@pytest.mark.integration
class TestAuthentication:
    """Integration tests for API key authentication."""

    def test_chat_without_auth_returns_401(self) -> None:
        """POST /chat without X-API-Key returns 401."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        client = TestClient(app)

        response = client.post("/chat", json={"session_id": "test", "message": "Hello"})
        assert response.status_code == 401

    def test_chat_with_invalid_key_returns_401(self) -> None:
        """POST /chat with invalid API key returns 401."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        client = TestClient(app)

        response = client.post(
            "/chat",
            json={"session_id": "test", "message": "Hello"},
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 401

    def test_chat_with_valid_key_succeeds(self, mock_console: MagicMock) -> None:
        """POST /chat with valid API key returns 200."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        app.state.metrics = None  # Initialize metrics (normally done in lifespan)
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session", return_value=mock_console),
            patch("consoul.sdk.save_session_state", return_value={}),
        ):
            response = client.post(
                "/chat",
                json={"session_id": "test", "message": "Hello"},
                headers={"X-API-Key": "test-api-key"},
            )
            assert response.status_code == 200

    def test_websocket_without_auth_rejected(self) -> None:
        """WebSocket connection without api_key query param is rejected."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect):  # noqa: SIM117
            with client.websocket_connect("/ws/chat/test-session"):
                pass

    def test_websocket_with_auth_query_param(self) -> None:
        """WebSocket connection with api_key query param is accepted."""
        config = ServerConfig(security=SecurityConfig(api_keys=["test-api-key"]))
        app = create_server(config)
        client = TestClient(app)

        with client.websocket_connect(
            "/ws/chat/test-session?api_key=test-api-key"
        ) as ws:
            # Connection accepted - send a ping to verify
            ws.send_json({"type": "ping"})
            # Don't wait for response, just verify connection works


# =============================================================================
# Chat Endpoint Session Tests
# =============================================================================


@pytest.mark.integration
class TestChatSession:
    """Integration tests for chat endpoint with session management."""

    def test_new_session_created(self, mock_console: MagicMock) -> None:
        """POST /chat with new session_id creates session."""
        app = create_server()
        app.state.metrics = None  # Initialize metrics (normally done in lifespan)
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session", return_value=mock_console),
            patch("consoul.sdk.save_session_state", return_value={}),
        ):
            response = client.post(
                "/chat", json={"session_id": "new-session", "message": "Hello"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "new-session"
            assert "response" in data
            assert "model" in data
            assert "usage" in data

    def test_session_persists_across_requests(self, mock_console: MagicMock) -> None:
        """Same session_id uses session store for persistence."""
        app = create_server()
        app.state.metrics = None  # Initialize metrics (normally done in lifespan)
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session", return_value=mock_console),
            patch("consoul.sdk.restore_session", return_value=mock_console),
            patch("consoul.sdk.save_session_state", return_value={"messages": []}),
        ):
            # First request - creates session
            r1 = client.post(
                "/chat", json={"session_id": "persist-test", "message": "Hello"}
            )
            assert r1.status_code == 200

            # Second request - should work with same session
            r2 = client.post(
                "/chat",
                json={"session_id": "persist-test", "message": "Follow up"},
            )
            assert r2.status_code == 200

    def test_response_format_complete(self, mock_console: MagicMock) -> None:
        """Response includes all required fields."""
        app = create_server()
        app.state.metrics = None  # Initialize metrics (normally done in lifespan)
        client = TestClient(app)

        with (
            patch("consoul.sdk.create_session", return_value=mock_console),
            patch("consoul.sdk.save_session_state", return_value={}),
        ):
            response = client.post(
                "/chat", json={"session_id": "format-test", "message": "Test"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "response" in data
            assert "model" in data
            assert "usage" in data
            assert "timestamp" in data


# =============================================================================
# Rate Limiting Tests
# =============================================================================


@pytest.mark.integration
class TestRateLimiting:
    """Integration tests for rate limiting."""

    def test_rate_limiter_configured(self) -> None:
        """Rate limiter is configured when rate_limit config provided."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["2/minute"]))
        app = create_server(config)

        # Verify rate limiter is attached to app
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None

    def test_health_bypasses_rate_limit(self) -> None:
        """Health endpoint is not rate limited."""
        config = ServerConfig(rate_limit=RateLimitConfig(default_limits=["2/minute"]))
        app = create_server(config)
        client = TestClient(app)

        # Many rapid requests should all succeed
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200


# =============================================================================
# WebSocket Streaming Tests
# =============================================================================


@pytest.mark.integration
class TestWebSocketStreaming:
    """Integration tests for WebSocket streaming."""

    def test_websocket_accepts_connection(self) -> None:
        """WebSocket endpoint accepts connections."""
        app = create_server()
        client = TestClient(app)

        with client.websocket_connect("/ws/chat/ws-test") as ws:
            # Connection accepted
            assert ws is not None

    def test_invalid_message_returns_error(self) -> None:
        """Invalid message format returns error event."""
        app = create_server()
        client = TestClient(app)

        with client.websocket_connect("/ws/chat/error-test") as ws:
            # Send message missing required fields
            ws.send_json({"invalid": "format"})

            data = ws.receive_json()
            assert data["type"] == "error"
            assert "message" in data["data"]


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.integration
class TestErrorHandling:
    """Integration tests for error scenarios."""

    def test_missing_message_returns_422(self) -> None:
        """POST /chat without message field returns 422."""
        app = create_server()
        client = TestClient(app)

        response = client.post("/chat", json={"session_id": "test"})
        assert response.status_code == 422

    def test_missing_session_id_returns_422(self) -> None:
        """POST /chat without session_id returns 422."""
        app = create_server()
        client = TestClient(app)

        response = client.post("/chat", json={"message": "Hello"})
        assert response.status_code == 422

    def test_sdk_error_returns_500(self) -> None:
        """SDK error during chat returns 500."""
        app = create_server()
        client = TestClient(app)

        with patch("consoul.sdk.create_session", side_effect=RuntimeError("SDK error")):
            response = client.post(
                "/chat", json={"session_id": "error-test", "message": "Hello"}
            )
            assert response.status_code == 500
