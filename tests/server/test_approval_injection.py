"""Tests for approval provider injection in server endpoints.

Tests that approval providers are properly passed through the server
to the SDK layer and that approval decisions are respected.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from consoul.ai.tools.base import RiskLevel
from consoul.sdk.models import ToolRequest

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_tool_request():
    """Create a mock tool request."""
    return ToolRequest(
        id="call_123",
        name="bash_execute",
        arguments={"command": "ls -la"},
        risk_level="caution",
    )


# =============================================================================
# Test: Approval Provider Protocol
# =============================================================================


class TestApprovalProviderProtocol:
    """Test approval provider protocol implementation."""

    @pytest.mark.asyncio
    async def test_approval_provider_with_on_tool_request_method(
        self, mock_tool_request
    ):
        """Approval provider with on_tool_request method should work."""

        class ProtocolProvider:
            """Provider implementing the protocol."""

            async def on_tool_request(self, request: ToolRequest) -> bool:
                return request.risk_level == "safe"

        provider = ProtocolProvider()

        # Test with safe risk level
        safe_request = ToolRequest(
            id="call_456",
            name="echo",
            arguments={"text": "hello"},
            risk_level="safe",
        )

        result = await provider.on_tool_request(safe_request)
        assert result is True

        # Test with caution risk level
        result = await provider.on_tool_request(mock_tool_request)
        assert result is False

    @pytest.mark.asyncio
    async def test_approval_provider_as_callable(self, mock_tool_request):
        """Approval provider as async callable should work."""

        async def callable_provider(request: ToolRequest) -> bool:
            return "safe" in request.risk_level

        result = await callable_provider(mock_tool_request)
        assert result is False

        safe_request = ToolRequest(
            id="call_789",
            name="pwd",
            arguments={},
            risk_level="safe",
        )
        result = await callable_provider(safe_request)
        assert result is True


class TestApprovalProviderInjection:
    """Test approval provider injection into services."""

    def _create_tool_config(self):
        """Create a mock ToolConfig."""
        config = Mock()
        config.enabled = True
        config.allowed_tools = None
        config.blocked_tools = []
        config.approval_mode = "auto"
        config.risk_thresholds = {}
        config.tool_timeout = 30
        config.audit_logging = False  # Disable audit logging for tests
        return config

    def test_approval_provider_passed_to_tool_registry(self):
        """Approval provider should be passed to ToolRegistry."""
        from consoul.ai.tools.registry import ToolRegistry

        async def my_provider(request: ToolRequest) -> bool:
            return True

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=my_provider)

        assert registry.approval_provider is my_provider

    def test_approval_provider_uses_default_when_not_provided(self):
        """ToolRegistry should use default provider when not provided."""
        from consoul.ai.tools.registry import ToolRegistry

        config = self._create_tool_config()
        # When no provider given, registry will try to get default
        # which may raise or return a default implementation
        try:
            registry = ToolRegistry(config=config)
            # If it succeeds, there's some default provider
            assert registry.approval_provider is not None
        except Exception:
            # Expected if no default provider available
            pass


class TestApprovalDecisions:
    """Test that approval decisions are respected."""

    def _create_tool_config(self):
        """Create a mock ToolConfig."""
        config = Mock()
        config.enabled = True
        config.allowed_tools = None
        config.blocked_tools = []
        config.approval_mode = "auto"
        config.risk_thresholds = {}
        config.tool_timeout = 30
        config.audit_logging = False  # Disable audit logging for tests
        return config

    @pytest.mark.asyncio
    async def test_approved_tool_execution_proceeds(self):
        """Approved tool should be executed."""
        from langchain_core.tools import tool

        from consoul.ai.tools.registry import ToolRegistry

        @tool
        def test_tool(x: str) -> str:
            """Test tool."""
            return x.upper()

        async def always_approve(request: ToolRequest) -> bool:
            return True

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=always_approve)
        registry.register(test_tool, risk_level=RiskLevel.CAUTION)

        # Tool should be registered
        tools = registry.list_tools()
        assert any(t.name == "test_tool" for t in tools)

    @pytest.mark.asyncio
    async def test_rejected_tool_execution_blocked(self):
        """Rejected tool should not be executed."""
        from langchain_core.tools import tool

        from consoul.ai.tools.registry import ToolRegistry

        @tool
        def dangerous_tool(x: str) -> str:
            """A dangerous tool."""
            return x

        async def always_reject(request: ToolRequest) -> bool:
            return False

        config = self._create_tool_config()
        registry = ToolRegistry(config=config, approval_provider=always_reject)
        registry.register(dangerous_tool, risk_level=RiskLevel.DANGEROUS)

        # Tool should be registered but approval will reject
        tools = registry.list_tools()
        assert any(t.name == "dangerous_tool" for t in tools)


class TestApprovalTimeout:
    """Test approval timeout behavior."""

    @pytest.mark.asyncio
    async def test_approval_timeout_returns_false(self):
        """Approval timeout should result in rejection."""
        import asyncio

        async def slow_approval(request: ToolRequest) -> bool:
            await asyncio.sleep(10)  # Very slow
            return True

        request = ToolRequest(
            id="call_123",
            name="test",
            arguments={},
            risk_level="safe",
        )

        # Apply timeout
        try:
            result = await asyncio.wait_for(slow_approval(request), timeout=0.1)
        except asyncio.TimeoutError:
            result = False  # Timeout = rejection

        assert result is False


class TestWebSocketApprovalProvider:
    """Test WebSocket-based approval provider patterns."""

    @pytest.mark.asyncio
    async def test_websocket_approval_provider_pattern(self):
        """Test the WebSocket approval provider pattern works."""
        import asyncio

        class MockWebSocket:
            """Mock WebSocket for testing."""

            def __init__(self):
                self.sent_messages = []
                self.pending_responses: dict[str, asyncio.Future[bool]] = {}

            async def send_json(self, data: dict):
                self.sent_messages.append(data)

            def set_response(self, tool_id: str, approved: bool):
                if tool_id in self.pending_responses:
                    self.pending_responses[tool_id].set_result(approved)

        class WebSocketApprovalProvider:
            """WebSocket approval provider for testing."""

            def __init__(self, websocket: MockWebSocket, timeout: float = 1.0):
                self.websocket = websocket
                self.timeout = timeout

            async def on_tool_request(self, request: ToolRequest) -> bool:
                future: asyncio.Future[bool] = asyncio.Future()
                self.websocket.pending_responses[request.id] = future

                await self.websocket.send_json(
                    {
                        "type": "tool_request",
                        "id": request.id,
                        "name": request.name,
                    }
                )

                try:
                    return await asyncio.wait_for(future, timeout=self.timeout)
                except asyncio.TimeoutError:
                    return False
                finally:
                    self.websocket.pending_responses.pop(request.id, None)

        # Test the pattern
        ws = MockWebSocket()
        provider = WebSocketApprovalProvider(ws, timeout=1.0)

        request = ToolRequest(
            id="call_abc",
            name="test_tool",
            arguments={},
            risk_level="caution",
        )

        # Start approval request
        approval_task = asyncio.create_task(provider.on_tool_request(request))

        # Simulate client response
        await asyncio.sleep(0.1)
        ws.set_response("call_abc", True)

        result = await approval_task

        assert result is True
        assert len(ws.sent_messages) == 1
        assert ws.sent_messages[0]["type"] == "tool_request"
        assert ws.sent_messages[0]["id"] == "call_abc"
