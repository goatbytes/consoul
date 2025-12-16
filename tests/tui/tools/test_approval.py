"""Tests for TUI approval provider."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from consoul.ai.tools import RiskLevel
from consoul.ai.tools.approval import (
    ApprovalProvider,
    ToolApprovalRequest,
)
from consoul.tui.tools.approval import TuiApprovalProvider

pytestmark = pytest.mark.asyncio


class TestTuiApprovalProvider:
    """Tests for TuiApprovalProvider."""

    def test_protocol_conformance(self):
        """Test that TuiApprovalProvider conforms to ApprovalProvider protocol."""
        app = MagicMock()
        provider = TuiApprovalProvider(app)
        assert isinstance(provider, ApprovalProvider)

    async def test_request_approval_approved(self):
        """Test approval request when user approves."""
        # Mock app
        app = MagicMock()
        app.push_screen_wait = AsyncMock(return_value=True)

        provider = TuiApprovalProvider(app)
        request = ToolApprovalRequest(
            tool_name="test_tool",
            arguments={"x": 1},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        response = await provider.request_approval(request)

        assert response.approved is True
        assert response.reason is None
        app.push_screen_wait.assert_called_once()

    async def test_request_approval_denied(self):
        """Test approval request when user denies."""
        # Mock app
        app = MagicMock()
        app.push_screen_wait = AsyncMock(return_value=False)

        provider = TuiApprovalProvider(app)
        request = ToolApprovalRequest(
            tool_name="test_tool",
            arguments={},
            risk_level=RiskLevel.DANGEROUS,
            tool_call_id="call_1",
        )

        response = await provider.request_approval(request)

        assert response.approved is False
        assert "denied via tui modal" in response.reason.lower()
        app.push_screen_wait.assert_called_once()

    async def test_request_with_complex_arguments(self):
        """Test approval with complex arguments."""
        app = MagicMock()
        app.push_screen_wait = AsyncMock(return_value=True)

        provider = TuiApprovalProvider(app)
        request = ToolApprovalRequest(
            tool_name="bash_execute",
            arguments={
                "command": "ls -la /tmp",
                "timeout": 30,
                "env": {"PATH": "/usr/bin"},
            },
            risk_level=RiskLevel.CAUTION,
            tool_call_id="call_2",
            description="Execute bash command",
        )

        response = await provider.request_approval(request)

        assert response.approved is True
        app.push_screen_wait.assert_called_once()

        # Verify modal was created with correct request
        call_args = app.push_screen_wait.call_args
        modal = call_args[0][0]
        assert modal.request == request
