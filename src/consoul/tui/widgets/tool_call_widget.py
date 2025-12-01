"""ToolCallWidget for displaying tool execution in chat.

Provides visual representation of tool calls with status tracking,
argument display, and collapsible output for long results.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rich.syntax import Syntax
from rich.text import Text
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.widgets import Collapsible, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from consoul.ai.tools.status import ToolStatus

__all__ = ["ToolCallWidget"]


class ToolCallWidget(Container):
    """Widget for displaying tool execution with status and results.

    Shows tool name, arguments, execution status, and collapsible output.
    Updates reactively as execution progresses through states.

    Attributes:
        tool_name: Name of the tool being executed
        arguments: Tool arguments dict
        status: Current execution status (reactive)
        result: Execution result (None until completed)

    Example:
        >>> widget = ToolCallWidget("bash_execute", {"command": "ls -la"})
        >>> await chat_view.add_message(widget)
        >>> # Later, after execution:
        >>> widget.update_result("file1.txt\\nfile2.txt", ToolStatus.SUCCESS)
    """

    # Reactive status that triggers UI updates
    # Initial value set in __init__ to avoid import at module level
    DEFAULT_STATUS_PLACEHOLDER: Any = None
    status: reactive[Any] = reactive(DEFAULT_STATUS_PLACEHOLDER)

    # Maximum lines before collapsing output
    COLLAPSE_THRESHOLD = 20

    def __init__(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        status: ToolStatus | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ToolCallWidget.

        Args:
            tool_name: Name of tool being executed
            arguments: Tool arguments dictionary
            status: Initial execution status
            **kwargs: Additional Container arguments
        """
        # Import here to avoid circular dependency
        from consoul.ai.tools.status import ToolStatus

        # Set non-reactive attributes first
        self.tool_name = tool_name
        self.arguments = arguments
        self.result: str | None = None
        self._output_container: Collapsible | None = None
        self._initial_status = status or ToolStatus.PENDING

        # Call super().__init__() BEFORE setting reactive properties
        super().__init__(**kwargs)

        # Set reactive status AFTER super().__init__()
        self.status = self._initial_status

    def compose(self) -> ComposeResult:
        """Compose the tool call widget structure."""
        # Tool header with name and arguments
        yield Static(
            self._format_tool_header(),
            id="tool-header",
            classes="tool-header",
        )

        # Arguments section
        yield Static(
            self._format_arguments(),
            id="tool-arguments",
            classes="tool-arguments",
        )

        # Status indicator
        yield Static(
            self._format_status(),
            id="tool-status",
            classes="tool-status",
        )

        # Output section - conditionally render only when we have a result
        if self.result:
            with Vertical(id="tool-output-container"):
                collapsed = self._should_collapse_output()
                with Collapsible(
                    title="Output",
                    collapsed=collapsed,
                    id="tool-output-collapsible",
                ):
                    yield Static(
                        self.result,
                        id="tool-output",
                        classes="tool-output",
                    )

    def on_mount(self) -> None:
        """Initialize widget styling on mount."""
        self._update_widget_classes()

    def _truncate_arg(self, value: str, max_len: int) -> str:
        """Truncate argument value to maximum length with ellipsis.

        Args:
            value: Argument value to truncate
            max_len: Maximum length before truncation

        Returns:
            Truncated string with '...' if longer than max_len
        """
        if len(value) <= max_len:
            return value
        return value[: max_len - 3] + "..."

    def _format_tool_header(self) -> Text:
        """Format tool header with tool name and arguments.

        Shows arguments inline in the header for immediate visibility
        of what the tool is executing. Different formatting strategies
        are used based on tool type and argument complexity.

        Returns:
            Rich Text object with formatted header
        """
        header = Text()
        header.append("🔧 ", style="bold")

        # Format based on tool type
        if self.tool_name == "bash_execute" and "command" in self.arguments:
            # Show bash command inline
            cmd = self.arguments["command"]
            truncated = self._truncate_arg(cmd, max_len=80)
            header.append(f'bash_execute("{truncated}")', style="bold cyan")

        elif self.tool_name in ("read_file", "write_file", "edit_file"):
            # File operations - show path prominently
            if "path" in self.arguments:
                path = self.arguments["path"]
                truncated_path = self._truncate_arg(str(path), max_len=60)
                # Show other args abbreviated
                other_args = [k for k in self.arguments if k != "path"]
                if other_args:
                    args_str = f'path="{truncated_path}", {", ".join(f"{k}=..." for k in other_args[:2])}'
                else:
                    args_str = f'path="{truncated_path}"'
                header.append(f"{self.tool_name}({args_str})", style="bold cyan")
            else:
                # Fallback to generic format
                header.append(self._format_generic_header(), style="bold cyan")

        elif self.tool_name in (
            "grep_search",
            "code_search",
            "ripgrep_search",
            "search",
        ):
            # Search tools - show pattern/query prominently
            pattern_key = None
            for key in ["pattern", "query", "search_term", "term"]:
                if key in self.arguments:
                    pattern_key = key
                    break

            if pattern_key:
                pattern = self.arguments[pattern_key]
                truncated_pattern = self._truncate_arg(str(pattern), max_len=50)
                # Show path if present
                if "path" in self.arguments:
                    path = self._truncate_arg(str(self.arguments["path"]), max_len=30)
                    args_str = f'{pattern_key}="{truncated_pattern}", path="{path}"'
                else:
                    args_str = f'{pattern_key}="{truncated_pattern}"'
                header.append(f"{self.tool_name}({args_str})", style="bold cyan")
            else:
                # Fallback to generic format
                header.append(self._format_generic_header(), style="bold cyan")

        elif len(self.arguments) == 1:
            # Single argument - show inline
            key, value = next(iter(self.arguments.items()))
            truncated = self._truncate_arg(str(value), max_len=60)
            header.append(f'{self.tool_name}({key}="{truncated}")', style="bold cyan")

        else:
            # Multiple arguments - show abbreviated
            header.append(self._format_generic_header(), style="bold cyan")

        return header

    def _format_generic_header(self) -> str:
        """Format header for tools with multiple/generic arguments.

        Returns:
            String with tool name and abbreviated argument list
        """
        if not self.arguments:
            return f"{self.tool_name}()"

        # Show first 3 argument names with ellipsis
        args_preview = ", ".join(f"{k}=..." for k in list(self.arguments.keys())[:3])
        if len(self.arguments) > 3:
            args_preview += ", ..."
        return f"{self.tool_name}({args_preview})"

    def _format_arguments(self) -> Text | Syntax:
        """Format tool arguments for display.

        Returns syntax-highlighted JSON for general args,
        or syntax-highlighted bash for bash_execute commands.

        Returns:
            Syntax object with formatted arguments
        """
        if self.tool_name == "bash_execute" and "command" in self.arguments:
            # Syntax highlight bash commands
            command = self.arguments["command"]
            return Syntax(
                command,
                "bash",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
        else:
            # Pretty-print arguments as JSON
            args_json = json.dumps(self.arguments, indent=2)
            return Syntax(
                args_json,
                "json",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )

    def _format_status(self) -> Text:
        """Format status indicator with emoji and text.

        Returns:
            Rich Text object with styled status
        """
        status_text = Text()

        # During compose(), status may not be set yet - use _initial_status
        current_status = getattr(self, "status", None) or getattr(
            self, "_initial_status", None
        )

        # Handle None status (shouldn't happen but defensive)
        if current_status is None:
            status_text.append("⏳ Initializing...", style="bold yellow")
            return status_text

        # Get status color based on state
        color_map = {
            "PENDING": "yellow",
            "EXECUTING": "cyan",
            "SUCCESS": "green",
            "ERROR": "red",
            "DENIED": "dim",
        }

        color = color_map.get(current_status.name, "white")
        status_text.append(f"{current_status.value}", style=f"bold {color}")

        return status_text

    def _should_collapse_output(self) -> bool:
        """Determine if output should be collapsed.

        Returns:
            True if output exceeds threshold, False otherwise
        """
        if not self.result:
            return False

        line_count = len(self.result.splitlines())
        return line_count > self.COLLAPSE_THRESHOLD

    def _update_widget_classes(self) -> None:
        """Update widget CSS classes based on current status."""
        # Remove all status classes
        for status_name in ["pending", "executing", "success", "error", "denied"]:
            self.remove_class(f"tool-{status_name}")

        # Add base class
        self.add_class("tool-call-widget")

        # Get current status (fallback to _initial_status if reactive not set)
        current_status = getattr(self, "status", None) or getattr(
            self, "_initial_status", None
        )

        # Add current status class
        if current_status:
            status_class = f"tool-{current_status.name.lower()}"
            self.add_class(status_class)
            # Update border title with status
            self.border_title = f"Tool Call - {current_status.value}"
        else:
            self.border_title = "Tool Call"

    def update_result(self, result: str, status: ToolStatus) -> None:
        """Update tool execution result and status.

        Args:
            result: Tool execution output or error message
            status: New execution status (SUCCESS, ERROR, or DENIED)

        Example:
            >>> widget.update_result("Success!", ToolStatus.SUCCESS)
        """
        self.result = result
        self.status = status

        # Check if output section already exists
        try:
            output_widget = self.query_one("#tool-output", Static)
            collapsible = self.query_one("#tool-output-collapsible", Collapsible)

            # Update existing widgets
            output_widget.update(result)
            collapsible.collapsed = self._should_collapse_output()

        except Exception:
            # Output section doesn't exist yet - mount it dynamically
            collapsed = self._should_collapse_output()

            # Create output static first
            output_static = Static(
                result,
                id="tool-output",
                classes="tool-output",
            )

            # Create collapsible with the static as child
            collapsible = Collapsible(
                output_static,
                title="Output",
                collapsed=collapsed,
                id="tool-output-collapsible",
            )

            # Create container with collapsible as child
            container = Vertical(collapsible, id="tool-output-container")

            # Mount the entire structure at once
            self.mount(container)

    def update_status(self, status: ToolStatus) -> None:
        """Update execution status without changing result.

        Used for transitioning from PENDING → EXECUTING.

        Args:
            status: New execution status

        Example:
            >>> widget.update_status(ToolStatus.EXECUTING)
        """
        self.status = status

    def watch_status(self, new_status: ToolStatus) -> None:
        """React to status changes by updating UI.

        Called automatically when status reactive property changes.

        Args:
            new_status: New status value
        """
        # Update widget classes for styling
        self._update_widget_classes()

        # Update status text
        try:
            status_widget = self.query_one("#tool-status", Static)
            status_widget.update(self._format_status())
        except Exception:
            # Widget not mounted yet, will be set in compose()
            pass
