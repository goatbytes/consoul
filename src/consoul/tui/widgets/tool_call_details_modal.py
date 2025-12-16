"""ToolCallDetailsModal - Modal for viewing tool call execution details.

Displays detailed information about tool calls executed for an assistant message,
including arguments, status, and output.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, ClassVar

from rich.syntax import Syntax
from rich.text import Text
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Collapsible, Label, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["ToolCallDetailsModal"]


class ToolCallDetailsModal(ModalScreen[None]):
    """Modal dialog for viewing tool call execution details.

    Displays a list of tool calls with their arguments, status, and results.
    Supports multiple tool calls per message with collapsible output sections.

    Args:
        tool_calls: List of tool call dicts with keys:
            - name: Tool name
            - arguments: Dict of arguments
            - status: Tool status (PENDING, EXECUTING, SUCCESS, ERROR, DENIED)
            - result: Tool execution result/output

    Keyboard Shortcuts:
        - Escape: Close modal
        - Enter: Close modal
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "close", "Close", show=False),
        Binding("enter", "close", "Close", show=False),
    ]

    DEFAULT_CSS = """
    ToolCallDetailsModal {
        align: center middle;
    }

    ToolCallDetailsModal > Vertical {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ToolCallDetailsModal .modal-title {
        dock: top;
        width: 100%;
        height: 3;
        content-align: center middle;
        background: $primary;
        color: $text;
        text-style: bold;
        margin: 0 0 1 0;
    }

    ToolCallDetailsModal .tool-call-section {
        width: 100%;
        height: auto;
        padding: 1 0;
        border-bottom: solid $accent;
    }

    ToolCallDetailsModal .tool-call-section:last-child {
        border-bottom: none;
    }

    ToolCallDetailsModal .tool-header {
        width: 100%;
        height: auto;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }

    ToolCallDetailsModal .tool-status {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    ToolCallDetailsModal .section-label {
        width: 100%;
        height: auto;
        text-style: bold;
        color: $text-muted;
        margin: 1 0 0 0;
    }

    ToolCallDetailsModal .tool-arguments {
        width: 100%;
        height: auto;
        padding: 0 2;
    }

    ToolCallDetailsModal .tool-output-scroll {
        width: 100%;
        height: auto;
        max-height: 20;
        padding: 0 2;
    }

    ToolCallDetailsModal .button-row {
        dock: bottom;
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ToolCallDetailsModal Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        tool_calls: list[dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Initialize ToolCallDetailsModal.

        Args:
            tool_calls: List of tool call data dicts
            **kwargs: Additional arguments passed to ModalScreen
        """
        super().__init__(**kwargs)
        self.tool_calls = tool_calls

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            # Modal title
            yield Label(
                f"Tool Calls ({len(self.tool_calls)})",
                classes="modal-title",
            )

            # Scrollable content area
            with VerticalScroll():
                # Render each tool call
                for idx, tool_call in enumerate(self.tool_calls, 1):
                    with Vertical(classes="tool-call-section"):
                        # Tool header with number
                        # Use Text to avoid markup interpretation
                        header_text = Text()
                        header_text.append(
                            f"Tool {idx} of {len(self.tool_calls)}: 🔧 {tool_call['name']}"
                        )
                        yield Static(
                            header_text,
                            classes="tool-header",
                        )

                        # Status indicator
                        yield Static(
                            self._format_status(tool_call.get("status", "UNKNOWN")),
                            classes="tool-status",
                        )

                        # Arguments section
                        yield Label("Arguments:", classes="section-label")
                        yield Static(
                            self._format_arguments(
                                tool_call["name"], tool_call.get("arguments", {})
                            ),
                            classes="tool-arguments",
                        )

                        # Output section (if result exists)
                        result = tool_call.get("result")
                        if result:
                            yield Label("Output:", classes="section-label")

                            # Use Collapsible for long outputs
                            collapsed = len(result.splitlines()) > 10
                            with (
                                Collapsible(
                                    title="",
                                    collapsed=collapsed,
                                ),
                                VerticalScroll(classes="tool-output-scroll"),
                            ):
                                # Use Text to avoid markup interpretation issues
                                yield Static(Text(result, no_wrap=False))

            # Close button
            with Horizontal(classes="button-row"):
                yield Button("Close", variant="primary", id="close-btn")

    def _format_status(self, status: str) -> Text:
        """Format status with emoji and color.

        Args:
            status: Status string (PENDING, EXECUTING, SUCCESS, ERROR, DENIED)

        Returns:
            Rich Text with formatted status
        """
        status_map = {
            "PENDING": ("⏳ Pending", "yellow"),
            "EXECUTING": ("⚙️  Executing", "cyan"),
            "SUCCESS": ("✅ Completed", "green"),
            "ERROR": ("❌ Error", "red"),
            "DENIED": ("🚫 Denied", "dim"),
        }

        emoji_text, color = status_map.get(status, (f"❓ {status}", "white"))
        text = Text()
        text.append(f"Status: {emoji_text}", style=f"bold {color}")
        return text

    def _format_arguments(self, tool_name: str, arguments: dict[str, Any]) -> Syntax:
        """Format tool arguments with syntax highlighting.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments dict

        Returns:
            Syntax object with highlighted arguments
        """
        if tool_name == "bash_execute" and "command" in arguments:
            # Syntax highlight bash commands
            command = arguments["command"]
            return Syntax(
                command,
                "bash",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
        else:
            # Pretty-print arguments as JSON
            args_json = json.dumps(arguments, indent=2)
            return Syntax(
                args_json,
                "json",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.action_close()
