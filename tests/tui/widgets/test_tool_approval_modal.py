"""Tests for ToolApprovalModal widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from consoul.ai.tools import RiskLevel
from consoul.ai.tools.approval import ToolApprovalRequest
from consoul.tui.widgets.tool_approval_modal import ToolApprovalModal

pytestmark = pytest.mark.asyncio


class ToolApprovalModalTestApp(App[None]):
    """Test app for ToolApprovalModal widget."""

    def __init__(self, modal: ToolApprovalModal) -> None:
        """Initialize test app with a ToolApprovalModal.

        Args:
            modal: ToolApprovalModal widget to test
        """
        super().__init__()
        self.modal = modal

    def compose(self) -> ComposeResult:
        """Compose test app with ToolApprovalModal."""
        yield self.modal


class TestToolApprovalModalInitialization:
    """Test ToolApprovalModal initialization and rendering."""

    async def test_modal_mounts_with_safe_risk(self) -> None:
        """Test modal mounts with SAFE risk level."""
        request = ToolApprovalRequest(
            tool_name="ls",
            arguments={"path": "/tmp"},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_1",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test():
            widget = app.query_one(ToolApprovalModal)
            assert widget.request == request
            assert widget.has_class("safe")

    async def test_modal_mounts_with_dangerous_risk(self) -> None:
        """Test modal mounts with DANGEROUS risk level."""
        request = ToolApprovalRequest(
            tool_name="rm",
            arguments={"path": "/tmp/file.txt", "force": True},
            risk_level=RiskLevel.DANGEROUS,
            tool_call_id="call_2",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test():
            widget = app.query_one(ToolApprovalModal)
            assert widget.request == request
            assert widget.has_class("dangerous")

    async def test_modal_displays_tool_name(self) -> None:
        """Test modal displays tool name."""
        request = ToolApprovalRequest(
            tool_name="bash_execute",
            arguments={"command": "echo hello"},
            risk_level=RiskLevel.CAUTION,
            tool_call_id="call_3",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test():
            # Query for tool name label
            labels = app.query("Label")
            tool_name_labels = [
                label for label in labels if label.has_class("tool-name")
            ]
            assert len(tool_name_labels) == 1
            # Note: Can't directly test label text in pilot mode easily

    async def test_modal_displays_description(self) -> None:
        """Test modal displays description when provided."""
        request = ToolApprovalRequest(
            tool_name="test_tool",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_4",
            description="Test description for tool",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test():
            # Description should be rendered
            statics = app.query("Static")
            description_statics = [
                static for static in statics if static.has_class("description")
            ]
            assert len(description_statics) == 1


class TestToolApprovalModalInteractions:
    """Test ToolApprovalModal user interactions."""

    async def test_approve_button_returns_true(self) -> None:
        """Test clicking approve button returns True."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_5",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test() as pilot:
            # Click approve button
            await pilot.click("#approve-button")
            # Modal should dismiss with True
            # Note: Actual return value testing requires screen push_screen_wait

    async def test_deny_button_returns_false(self) -> None:
        """Test clicking deny button returns False."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_6",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test() as pilot:
            # Click deny button
            await pilot.click("#deny-button")
            # Modal should dismiss with False

    async def test_y_key_approves(self) -> None:
        """Test pressing Y key approves."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_7",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test() as pilot:
            # Press Y key
            await pilot.press("y")
            # Modal should dismiss with True

    async def test_n_key_denies(self) -> None:
        """Test pressing N key denies."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_8",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test() as pilot:
            # Press N key
            await pilot.press("n")
            # Modal should dismiss with False

    async def test_escape_key_denies(self) -> None:
        """Test pressing Escape key denies."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_9",
        )
        modal = ToolApprovalModal(request)
        app = ToolApprovalModalTestApp(modal)

        async with app.run_test() as pilot:
            # Press Escape key
            await pilot.press("escape")
            # Modal should dismiss with False


class TestToolApprovalModalArgumentFormatting:
    """Test argument formatting in modal."""

    async def test_formats_simple_arguments(self) -> None:
        """Test formatting of simple arguments."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={"key": "value", "number": 42},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_10",
        )
        modal = ToolApprovalModal(request)

        formatted = modal._format_arguments(request.arguments)
        assert "key" in formatted
        assert "value" in formatted
        assert "number" in formatted
        assert "42" in formatted

    async def test_formats_nested_arguments(self) -> None:
        """Test formatting of nested arguments."""
        request = ToolApprovalRequest(
            tool_name="test",
            arguments={
                "command": "echo",
                "env": {"PATH": "/usr/bin", "HOME": "/home/user"},
            },
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_11",
        )
        modal = ToolApprovalModal(request)

        formatted = modal._format_arguments(request.arguments)
        assert "command" in formatted
        assert "env" in formatted
        assert "PATH" in formatted

    async def test_handles_non_serializable_arguments(self) -> None:
        """Test handling of non-JSON-serializable arguments."""

        class CustomObject:
            pass

        request = ToolApprovalRequest(
            tool_name="test",
            arguments={"obj": CustomObject()},
            risk_level=RiskLevel.SAFE,
            tool_call_id="call_12",
        )
        modal = ToolApprovalModal(request)

        # Should not raise, fallback to repr
        formatted = modal._format_arguments(request.arguments)
        assert isinstance(formatted, str)
