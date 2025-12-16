"""Tests for CLI approval provider."""

from unittest.mock import patch

import pytest

from consoul.ai.tools import RiskLevel
from consoul.ai.tools.approval import ToolApprovalRequest
from consoul.ai.tools.providers import CliApprovalProvider

pytestmark = pytest.mark.asyncio


class TestCliApprovalProvider:
    """Tests for CliApprovalProvider."""

    async def test_cli_approval_yes(self):
        """Test CLI provider with 'y' input."""
        provider = CliApprovalProvider()
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={"x": 1},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        with patch("builtins.input", return_value="y"):
            response = await provider.request_approval(request)

        assert response.approved is True
        assert response.reason is None

    async def test_cli_approval_no(self):
        """Test CLI provider with 'n' input."""
        provider = CliApprovalProvider()
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        with patch("builtins.input", return_value="n"):
            response = await provider.request_approval(request)

        assert response.approved is False
        assert "denied" in response.reason.lower()

    async def test_cli_approval_yes_full_word(self):
        """Test CLI provider with 'yes' input."""
        provider = CliApprovalProvider()
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        with patch("builtins.input", return_value="yes"):
            response = await provider.request_approval(request)

        assert response.approved is True

    async def test_cli_approval_no_arguments(self):
        """Test CLI provider with show_arguments=False."""
        provider = CliApprovalProvider(show_arguments=False)
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={"command": "ls -la"},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )

        with patch("builtins.input", return_value="y"):
            response = await provider.request_approval(request)

        assert response.approved is True

    async def test_cli_approval_verbose(self):
        """Test CLI provider with verbose=True."""
        provider = CliApprovalProvider(verbose=True)
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.DANGEROUS,
            tool_call_id="call_1",
            description="Test description",
            context={"user": "test"},
        )

        with patch("builtins.input", return_value="y"):
            response = await provider.request_approval(request)

        assert response.approved is True
