"""Tests for /chat/stream SSE endpoint.

Tests the POST /chat/stream SSE streaming endpoint:
- Endpoint registration
- SSE event formatting
- Auto-approval provider
- Request validation
- Authentication integration
- Connection management
- OpenAPI documentation
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from consoul.server import create_server
from consoul.server.endpoints.sse import (
    SSEAutoApprovalProvider,
    SSEConnectionManager,
    sse_format_event,
)
from consoul.server.models import (
    ChatUsage,
    SecurityConfig,
    ServerConfig,
    SSEDoneEvent,
    SSEErrorEvent,
    SSETokenEvent,
    SSEToolRequestEvent,
)


class TestSSEEventFormatting:
    """Test SSE event string formatting."""

    def test_token_event_format(self) -> None:
        """Token event is formatted correctly."""
        event = sse_format_event("token", {"text": "Hello"})

        assert event.startswith("event: token\n")
        assert "data: " in event
        assert event.endswith("\n\n")

        # Parse the data line
        data_line = event.split("\n")[1]
        assert data_line.startswith("data: ")
        data = json.loads(data_line[6:])
        assert data == {"text": "Hello"}

    def test_done_event_format(self) -> None:
        """Done event is formatted correctly."""
        usage = ChatUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            estimated_cost=0.0001,
        )
        done_data = SSEDoneEvent(
            session_id="test",
            usage=usage,
            timestamp="2025-12-25T10:30:45.123456Z",
        )
        event = sse_format_event("done", done_data.model_dump())

        assert event.startswith("event: done\n")
        data_line = event.split("\n")[1]
        data = json.loads(data_line[6:])
        assert data["session_id"] == "test"
        assert "usage" in data
        assert data["usage"]["total_tokens"] == 15

    def test_error_event_format(self) -> None:
        """Error event is formatted correctly."""
        error_data = SSEErrorEvent(
            code="E900",
            error="internal_error",
            message="Something went wrong",
            recoverable=False,
        )
        event = sse_format_event("error", error_data.model_dump())

        assert event.startswith("event: error\n")
        data_line = event.split("\n")[1]
        data = json.loads(data_line[6:])
        assert data["code"] == "E900"
        assert data["error"] == "internal_error"
        assert data["message"] == "Something went wrong"
        assert data["recoverable"] is False

    def test_tool_request_event_format(self) -> None:
        """Tool request event is formatted correctly."""
        tool_data = SSEToolRequestEvent(
            id="call_123",
            name="search",
            arguments={"query": "weather"},
            risk_level="safe",
        )
        event = sse_format_event("tool_request", tool_data.model_dump())

        assert event.startswith("event: tool_request\n")
        data_line = event.split("\n")[1]
        data = json.loads(data_line[6:])
        assert data["id"] == "call_123"
        assert data["name"] == "search"
        assert data["arguments"] == {"query": "weather"}
        assert data["risk_level"] == "safe"

    def test_unicode_in_token_event(self) -> None:
        """Unicode characters are preserved in events."""
        event = sse_format_event("token", {"text": "Hello 世界 🌍"})

        data_line = event.split("\n")[1]
        data = json.loads(data_line[6:])
        assert data["text"] == "Hello 世界 🌍"


class TestSSEAutoApprovalProvider:
    """Test SSE auto-approval modes."""

    @pytest.mark.asyncio
    async def test_auto_mode_approves_all(self) -> None:
        """Auto mode approves all tool requests."""
        provider = SSEAutoApprovalProvider(mode="auto")

        mock_request = MagicMock()
        mock_request.id = "call_123"
        mock_request.name = "dangerous_tool"
        mock_request.arguments = {}
        mock_request.risk_level = "dangerous"

        approved = await provider.on_tool_request(mock_request)
        assert approved is True

    @pytest.mark.asyncio
    async def test_safe_only_mode_approves_safe(self) -> None:
        """Safe-only mode approves safe tools."""
        provider = SSEAutoApprovalProvider(mode="safe_only")

        mock_request = MagicMock()
        mock_request.id = "call_123"
        mock_request.name = "safe_tool"
        mock_request.arguments = {}
        mock_request.risk_level = "safe"

        approved = await provider.on_tool_request(mock_request)
        assert approved is True

    @pytest.mark.asyncio
    async def test_safe_only_mode_denies_dangerous(self) -> None:
        """Safe-only mode denies dangerous tools."""
        provider = SSEAutoApprovalProvider(mode="safe_only")

        mock_request = MagicMock()
        mock_request.id = "call_123"
        mock_request.name = "dangerous_tool"
        mock_request.arguments = {}
        mock_request.risk_level = "dangerous"

        approved = await provider.on_tool_request(mock_request)
        assert approved is False

    @pytest.mark.asyncio
    async def test_none_mode_denies_all(self) -> None:
        """None mode denies all tool requests."""
        provider = SSEAutoApprovalProvider(mode="none")

        mock_request = MagicMock()
        mock_request.id = "call_123"
        mock_request.name = "safe_tool"
        mock_request.arguments = {}
        mock_request.risk_level = "safe"

        approved = await provider.on_tool_request(mock_request)
        assert approved is False

    @pytest.mark.asyncio
    async def test_sends_notification_when_callback_provided(self) -> None:
        """Provider sends notification when send_func provided."""
        notifications: list[str] = []

        async def mock_send(event: str) -> None:
            notifications.append(event)

        provider = SSEAutoApprovalProvider(mode="auto", send_func=mock_send)

        mock_request = MagicMock()
        mock_request.id = "call_123"
        mock_request.name = "search"
        mock_request.arguments = {"query": "test"}
        mock_request.risk_level = "safe"

        await provider.on_tool_request(mock_request)

        assert len(notifications) == 1
        assert "tool_request" in notifications[0]


class TestSSEConnectionManager:
    """Test SSE connection counting."""

    @pytest.mark.asyncio
    async def test_connect_increments(self) -> None:
        """Connect increments active count."""
        manager = SSEConnectionManager()

        assert manager.active_count == 0
        await manager.connect()
        assert manager.active_count == 1
        await manager.connect()
        assert manager.active_count == 2

    @pytest.mark.asyncio
    async def test_disconnect_decrements(self) -> None:
        """Disconnect decrements active count."""
        manager = SSEConnectionManager()

        await manager.connect()
        await manager.connect()
        assert manager.active_count == 2

        await manager.disconnect()
        assert manager.active_count == 1

        await manager.disconnect()
        assert manager.active_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_never_below_zero(self) -> None:
        """Disconnect never goes below zero."""
        manager = SSEConnectionManager()

        await manager.disconnect()
        assert manager.active_count == 0

        await manager.disconnect()
        assert manager.active_count == 0


class TestSSEEndpointExists:
    """Test /chat/stream endpoint is registered correctly."""

    def test_chat_stream_endpoint_registered(self) -> None:
        """SSE endpoint is registered at POST /chat/stream."""
        app = create_server()

        routes = [route.path for route in app.routes]
        assert "/chat/stream" in routes

    def test_chat_stream_requires_post_method(self) -> None:
        """SSE endpoint only accepts POST requests."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/chat/stream")
        assert response.status_code == 405

    def test_sse_connection_manager_initialized(self) -> None:
        """SSE connection manager is initialized in app.state."""
        app = create_server()

        assert hasattr(app.state, "sse_connections")
        assert isinstance(app.state.sse_connections, SSEConnectionManager)


class TestSSERequestValidation:
    """Test request validation for /chat/stream endpoint."""

    def test_missing_session_id_returns_422(self) -> None:
        """Missing session_id returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post("/chat/stream", json={"message": "Hello"})
        assert response.status_code == 422

    def test_missing_message_returns_422(self) -> None:
        """Missing message returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post("/chat/stream", json={"session_id": "test"})
        assert response.status_code == 422

    def test_empty_session_id_returns_422(self) -> None:
        """Empty session_id returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/stream", json={"session_id": "", "message": "Hello"}
        )
        assert response.status_code == 422

    def test_empty_message_returns_422(self) -> None:
        """Empty message returns 422 validation error."""
        app = create_server()
        client = TestClient(app)

        response = client.post(
            "/chat/stream", json={"session_id": "test", "message": ""}
        )
        assert response.status_code == 422


class TestSSEAuthentication:
    """Test authentication for /chat/stream endpoint."""

    def test_chat_stream_works_without_auth_configured(self) -> None:
        """SSE endpoint bypasses auth when no API keys configured."""
        config = ServerConfig(security=SecurityConfig(api_keys=[]))
        app = create_server(config)
        client = TestClient(app, raise_server_exceptions=False)

        # Without API keys configured, auth middleware should not be active
        # The response will fail during streaming (500) but should NOT be 401
        response = client.post(
            "/chat/stream", json={"session_id": "test", "message": "Hello"}
        )
        # Key assertion: should not be 401 (no auth required)
        # May fail with 500 during actual streaming, which is fine for this test
        assert response.status_code != 401

    def test_chat_stream_requires_auth_when_configured(self) -> None:
        """SSE endpoint requires authentication when API keys configured."""
        config = ServerConfig(security=SecurityConfig(api_keys=["secret-key"]))
        app = create_server(config)
        client = TestClient(app)

        response = client.post(
            "/chat/stream", json={"session_id": "test", "message": "Hello"}
        )
        assert response.status_code == 401

    def test_chat_stream_succeeds_with_valid_api_key(self) -> None:
        """SSE endpoint accepts valid API key."""
        config = ServerConfig(security=SecurityConfig(api_keys=["valid-key"]))
        app = create_server(config)
        client = TestClient(app, raise_server_exceptions=False)

        # With a valid API key, auth should pass
        # The response may fail during streaming (500) but should NOT be 401
        response = client.post(
            "/chat/stream",
            json={"session_id": "test", "message": "Hello"},
            headers={"X-API-Key": "valid-key"},
        )
        # Key assertion: should not be 401 (valid key provided)
        assert response.status_code != 401


class TestSSEOpenAPIDocumentation:
    """Test OpenAPI documentation for SSE endpoint."""

    def test_chat_stream_in_openapi_schema(self) -> None:
        """SSE endpoint is documented in OpenAPI spec."""
        app = create_server()
        openapi_schema = app.openapi()

        assert "/chat/stream" in openapi_schema["paths"]
        assert "post" in openapi_schema["paths"]["/chat/stream"]

    def test_chat_stream_response_documented(self) -> None:
        """SSE response type is documented."""
        app = create_server()
        openapi_schema = app.openapi()

        endpoint = openapi_schema["paths"]["/chat/stream"]["post"]
        responses = endpoint.get("responses", {})

        # 200 should be documented
        assert "200" in responses

    def test_chat_stream_uses_chat_request(self) -> None:
        """SSE endpoint uses ChatRequest for request body."""
        app = create_server()
        openapi_schema = app.openapi()

        endpoint = openapi_schema["paths"]["/chat/stream"]["post"]
        request_body = endpoint.get("requestBody", {})

        # Should have a request body
        assert request_body.get("required") is True
        # Should reference ChatRequest schema
        schema = (
            request_body.get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        assert "$ref" in schema or "properties" in schema

    def test_chat_stream_422_documented(self) -> None:
        """422 validation error is documented."""
        app = create_server()
        openapi_schema = app.openapi()

        endpoint = openapi_schema["paths"]["/chat/stream"]["post"]
        responses = endpoint.get("responses", {})

        assert "422" in responses


class TestHealthEndpointIncludesSSE:
    """Test that health endpoint includes SSE connections."""

    def test_health_shows_zero_connections_initially(self) -> None:
        """Health endpoint shows 0 connections initially."""
        app = create_server()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["connections"] == 0

    @pytest.mark.asyncio
    async def test_health_counts_sse_connections(self) -> None:
        """Health endpoint counts SSE connections."""
        app = create_server()

        # Manually increment SSE connections
        await app.state.sse_connections.connect()

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        # Should include the SSE connection
        assert data["connections"] >= 1

        # Cleanup
        await app.state.sse_connections.disconnect()


class TestSSEModels:
    """Test SSE Pydantic models."""

    def test_sse_token_event_model(self) -> None:
        """SSETokenEvent model validates correctly."""
        event = SSETokenEvent(text="Hello")
        assert event.text == "Hello"

    def test_sse_done_event_model(self) -> None:
        """SSEDoneEvent model validates correctly."""
        usage = ChatUsage(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            estimated_cost=0.0001,
        )
        event = SSEDoneEvent(
            session_id="test",
            usage=usage,
            timestamp="2025-12-25T10:30:45Z",
        )
        assert event.session_id == "test"
        assert event.usage.total_tokens == 15

    def test_sse_error_event_model(self) -> None:
        """SSEErrorEvent model validates correctly."""
        event = SSEErrorEvent(
            code="E900",
            error="internal_error",
            message="Something went wrong",
            recoverable=False,
        )
        assert event.code == "E900"
        assert event.error == "internal_error"
        assert event.message == "Something went wrong"
        assert event.recoverable is False

    def test_sse_tool_request_event_model(self) -> None:
        """SSEToolRequestEvent model validates correctly."""
        event = SSEToolRequestEvent(
            id="call_123",
            name="search",
            arguments={"query": "test"},
            risk_level="safe",
        )
        assert event.id == "call_123"
        assert event.name == "search"
        assert event.arguments == {"query": "test"}
        assert event.risk_level == "safe"
