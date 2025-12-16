"""Tests for approval API."""

import pytest

from consoul.ai.tools import RiskLevel
from consoul.ai.tools.approval import (
    ApprovalError,
    ApprovalProvider,
    ToolApprovalRequest,
    ToolApprovalResponse,
)


class TestToolApprovalRequest:
    """Tests for ToolApprovalRequest dataclass."""

    def test_create_minimal_request(self):
        """Test creating request with minimal fields."""
        request = ToolApprovalRequest(
            tool_name="test_tool",
            arguments={"arg": "value"},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_123",
        )

        assert request.tool_name == "test_tool"
        assert request.arguments == {"arg": "value"}
        assert request.risk_level == RiskLevel.SAFE
        assert request.tool_call_id == "call_123"
        assert request.description == ""
        assert request.context == {}

    def test_create_full_request(self):
        """Test creating request with all fields."""
        request = ToolApprovalRequest(
            tool_name="bash",
            arguments={"command": "ls"},
            risk_level=RiskLevel.DANGEROUS,
            tool_call_id="call_456",
            description="Execute bash command",
            context={"user": "jared", "session": "abc"},
        )

        assert request.description == "Execute bash command"
        assert request.context["user"] == "jared"
        assert request.context["session"] == "abc"


class TestToolApprovalResponse:
    """Tests for ToolApprovalResponse dataclass."""

    def test_approved_response(self):
        """Test creating approved response."""
        response = ToolApprovalResponse(approved=True)

        assert response.approved is True
        assert response.reason is None
        assert response.timeout_override is None
        assert response.metadata == {}

    def test_denied_response_with_reason(self):
        """Test creating denied response with reason."""
        response = ToolApprovalResponse(
            approved=False,
            reason="User denied: too dangerous",
        )

        assert response.approved is False
        assert response.reason == "User denied: too dangerous"

    def test_approved_with_timeout_override(self):
        """Test response with custom timeout."""
        response = ToolApprovalResponse(approved=True, timeout_override=120)

        assert response.timeout_override == 120

    def test_response_with_metadata(self):
        """Test response with metadata."""
        response = ToolApprovalResponse(
            approved=True,
            metadata={"timestamp": "2025-01-01T00:00:00"},
        )

        assert response.metadata["timestamp"] == "2025-01-01T00:00:00"


# Mock approval providers for testing


class MockApproveProvider:
    """Mock provider that always approves."""

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        return ToolApprovalResponse(approved=True)


class MockDenyProvider:
    """Mock provider that always denies."""

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        return ToolApprovalResponse(approved=False, reason="Mock denial")


class MockRaisingProvider:
    """Mock provider that raises exceptions."""

    async def request_approval(
        self, request: ToolApprovalRequest
    ) -> ToolApprovalResponse:
        raise ValueError("Mock error")


class TestApprovalProvider:
    """Tests for ApprovalProvider protocol."""

    def test_protocol_conformance_approve(self):
        """Test mock approve provider conforms to protocol."""
        provider = MockApproveProvider()
        assert isinstance(provider, ApprovalProvider)

    def test_protocol_conformance_deny(self):
        """Test mock deny provider conforms to protocol."""
        provider = MockDenyProvider()
        assert isinstance(provider, ApprovalProvider)

    def test_protocol_conformance_raising(self):
        """Test mock raising provider conforms to protocol."""
        provider = MockRaisingProvider()
        assert isinstance(provider, ApprovalProvider)

    @pytest.mark.asyncio
    async def test_approve_provider_approves(self):
        """Test approve provider returns approved=True."""
        provider = MockApproveProvider()
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        response = await provider.request_approval(request)
        assert response.approved is True

    @pytest.mark.asyncio
    async def test_deny_provider_denies(self):
        """Test deny provider returns approved=False."""
        provider = MockDenyProvider()
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        response = await provider.request_approval(request)
        assert response.approved is False
        assert "Mock denial" in response.reason


class TestApprovalError:
    """Tests for ApprovalError exception."""

    def test_raise_approval_error(self):
        """Test raising ApprovalError."""
        with pytest.raises(ApprovalError, match="Test error"):
            raise ApprovalError("Test error")

    def test_approval_error_is_exception(self):
        """Test ApprovalError inherits from Exception."""
        error = ApprovalError("Test")
        assert isinstance(error, Exception)
