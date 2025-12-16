"""CommandOutputBubble widget for displaying inline shell command execution results.

This module provides a widget that displays the results of user-executed shell
commands (using ! prefix syntax) with syntax highlighting and collapsible output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.syntax import Syntax
from rich.text import Text
from textual.containers import Container, Vertical
from textual.widgets import Collapsible, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["CommandOutputBubble"]


class CommandOutputBubble(Container):
    """Widget for displaying shell command execution results.

    Shows command, stdout/stderr output, and exit code with appropriate styling.
    Long output is automatically made collapsible for better UX.

    Attributes:
        command: The shell command that was executed
        stdout: Standard output from command
        stderr: Standard error from command
        exit_code: Command exit code (0 = success, non-zero = error)
        execution_time: Time taken to execute in seconds
    """

    # Threshold for collapsing output (lines)
    COLLAPSE_THRESHOLD = 20

    def __init__(
        self,
        command: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        execution_time: float | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CommandOutputBubble.

        Args:
            command: Shell command that was executed
            stdout: Standard output text
            stderr: Standard error text
            exit_code: Exit code (0 = success)
            execution_time: Execution time in seconds
            **kwargs: Additional Container arguments
        """
        super().__init__(**kwargs)
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.execution_time = execution_time

    def compose(self) -> ComposeResult:
        """Compose the command output widget structure."""
        # Header with command
        yield Static(
            self._format_header(),
            id="command-header",
            classes="command-header",
        )

        # Command text with syntax highlighting
        yield Static(
            self._format_command(),
            id="command-text",
            classes="command-text",
        )

        # Output section - always expanded by default
        output_text = self._combine_output()
        if output_text:
            with (
                Vertical(id="command-output-container"),
                Collapsible(
                    title="Output",
                    collapsed=False,  # Always show by default
                    id="command-output-collapsible",
                ),
            ):
                yield Static(
                    self._format_output(output_text),
                    id="command-output",
                    classes="command-output",
                )

        # Status footer
        yield Static(
            self._format_status(),
            id="command-status",
            classes="command-status",
        )

    def on_mount(self) -> None:
        """Initialize widget styling on mount."""
        # Add success or error class based on exit code
        if self.exit_code == 0:
            self.add_class("command-success")
        else:
            self.add_class("command-error")

    def _format_header(self) -> Text:
        """Format the command header.

        Returns:
            Rich Text with formatted header
        """
        text = Text()
        icon = "✓" if self.exit_code == 0 else "✗"
        style = "bold green" if self.exit_code == 0 else "bold red"

        text.append(f"{icon} ", style=style)
        text.append("Inline Command Execution", style="bold")

        return text

    def _format_command(self) -> Syntax:
        """Format command with bash syntax highlighting.

        Returns:
            Syntax object with highlighted command
        """
        return Syntax(
            self.command,
            "bash",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )

    def _combine_output(self) -> str:
        """Combine stdout and stderr into single output string.

        Returns:
            Combined output text
        """
        parts = []

        if self.stdout:
            parts.append(self.stdout.rstrip())

        if self.stderr:
            if parts:
                parts.append("")  # Blank line separator
            parts.append("=== STDERR ===")
            parts.append(self.stderr.rstrip())

        return "\n".join(parts) if parts else ""

    def _format_output(self, output: str) -> Syntax | Text:
        """Format output with syntax highlighting.

        Args:
            output: Output text to format

        Returns:
            Syntax or Text object with formatted output
        """
        if not output:
            return Text("(no output)", style="dim italic")

        # Try to detect if output looks like code/structured data
        # For now, just use plain text with ANSI preservation
        # Could enhance later with automatic language detection
        return Syntax(
            output,
            "text",
            theme="monokai",
            line_numbers=False,
            word_wrap=True,
        )

    def _format_status(self) -> Text:
        """Format status footer with exit code and timing.

        Returns:
            Rich Text with status information
        """
        text = Text()

        # Exit code
        if self.exit_code == 0:
            text.append("Exit code: 0", style="green")
        else:
            text.append(f"Exit code: {self.exit_code}", style="red bold")

        # Execution time
        if self.execution_time is not None:
            text.append(" • ", style="dim")
            text.append(f"{self.execution_time:.2f}s", style="dim")

        return text

    def _should_collapse_output(self) -> bool:
        """Determine if output should be collapsed by default.

        Returns:
            True if output exceeds collapse threshold
        """
        output = self._combine_output()
        if not output:
            return False

        line_count = len(output.split("\n"))
        return line_count > self.COLLAPSE_THRESHOLD
