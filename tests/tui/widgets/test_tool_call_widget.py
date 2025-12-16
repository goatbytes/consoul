"""Tests for ToolCallWidget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Collapsible, Static

from consoul.ai.tools import ToolStatus
from consoul.tui.widgets.tool_call_widget import ToolCallWidget

pytestmark = pytest.mark.asyncio


class ToolCallWidgetTestApp(App[None]):
    """Test app for ToolCallWidget."""

    def __init__(self, widget: ToolCallWidget) -> None:
        super().__init__()
        self._widget = widget

    def compose(self) -> ComposeResult:
        yield self._widget


class TestToolCallWidgetBasics:
    """Basic rendering tests."""

    async def test_renders_initial_state(self) -> None:
        widget = ToolCallWidget("bash_execute", {"command": "ls"})
        app = ToolCallWidgetTestApp(widget)

        async with app.run_test():
            rendered = app.query_one(ToolCallWidget)
            assert rendered.tool_name == "bash_execute"
            assert rendered.status == ToolStatus.PENDING

    async def test_status_updates_apply_css_class(self) -> None:
        widget = ToolCallWidget("bash_execute", {"command": "ls"})
        app = ToolCallWidgetTestApp(widget)

        async with app.run_test():
            rendered = app.query_one(ToolCallWidget)
            rendered.update_status(ToolStatus.EXECUTING)

            assert rendered.status == ToolStatus.EXECUTING
            assert rendered.has_class("tool-executing")


class TestToolCallWidgetOutput:
    """Output rendering tests."""

    async def test_update_result_mounts_output(self) -> None:
        widget = ToolCallWidget("bash_execute", {"command": "pwd"})
        app = ToolCallWidgetTestApp(widget)

        async with app.run_test() as pilot:
            rendered = app.query_one(ToolCallWidget)

            # Verify result is set and status updated
            rendered.update_result("line1\nline2", ToolStatus.SUCCESS)
            assert rendered.result == "line1\nline2"
            assert rendered.status == ToolStatus.SUCCESS

            # Wait for the output widget to be mounted
            await pilot.pause()

            # Verify output widget was mounted
            output = rendered.query_one("#tool-output", Static)
            assert output is not None

    async def test_long_output_collapses(self) -> None:
        widget = ToolCallWidget("bash_execute", {"command": "ls"})
        app = ToolCallWidgetTestApp(widget)

        long_output = "\n".join(f"line {i}" for i in range(100))

        async with app.run_test() as pilot:
            rendered = app.query_one(ToolCallWidget)
            rendered.update_result(long_output, ToolStatus.SUCCESS)

            # Wait for the collapsible to be mounted
            await pilot.pause()

            collapsible = rendered.query_one("#tool-output-collapsible", Collapsible)
            assert collapsible.collapsed is True

    async def test_non_bash_arguments_render_as_json(self) -> None:
        widget = ToolCallWidget("custom_tool", {"foo": "bar", "num": 42})
        app = ToolCallWidgetTestApp(widget)

        async with app.run_test():
            # Verify arguments were stored correctly
            assert widget.arguments == {"foo": "bar", "num": 42}
            assert widget.tool_name == "custom_tool"

            # Verify arguments static widget exists
            args_static = app.query_one("#tool-arguments", Static)
            assert args_static is not None
