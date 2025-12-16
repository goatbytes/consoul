"""Error screen shown when TUI initialization fails.

This screen provides clear error messages with troubleshooting guidance
and allows users to retry initialization or exit gracefully.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from rich.traceback import Traceback
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["InitializationErrorScreen"]


class InitializationErrorScreen(Screen[None]):
    """Screen shown when initialization fails.

    Displays error message, type, troubleshooting tips, and action buttons.
    """

    CSS = """
    InitializationErrorScreen {
        align: center middle;
        background: $surface;
    }

    #error-container {
        width: 80;
        height: auto;
        border: heavy $error;
        padding: 2;
        background: $panel;
    }

    #error-title {
        text-style: bold;
        color: $error;
        text-align: center;
        margin-bottom: 1;
    }

    #error-message {
        color: $text;
        margin-bottom: 2;
    }

    #error-details {
        display: none;
        margin-top: 2;
        border: solid $primary;
        padding: 1;
        max-height: 20;
        overflow-y: auto;
        background: $boost;
    }

    #buttons {
        align: center middle;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, error: Exception, app_instance: Any = None) -> None:
        """Initialize the error screen.

        Args:
            error: The exception that caused initialization to fail
            app_instance: Reference to the app for retry functionality
        """
        super().__init__()
        self.error = error
        self.app_instance = app_instance
        self.show_details = False

    def compose(self) -> ComposeResult:
        """Compose the error screen widgets."""
        error_type = type(self.error).__name__
        error_msg = str(self.error)

        # Get troubleshooting tip based on error type
        tip = self._get_troubleshooting_tip(error_type, error_msg)

        with Vertical(id="error-container"):
            yield Static("Initialization Failed", id="error-title")
            yield Static(
                f"[b]{error_type}[/b]\n\n{error_msg}\n\n{tip}",
                id="error-message",
            )

            # Stack trace details (hidden by default)
            try:
                tb = Traceback.from_exception(
                    type(self.error),
                    self.error,
                    self.error.__traceback__,
                )
                yield Static(str(tb), id="error-details")
            except Exception:
                # Fallback if rich traceback fails
                import traceback

                tb_str = "".join(
                    traceback.format_exception(
                        type(self.error), self.error, self.error.__traceback__
                    )
                )
                yield Static(tb_str, id="error-details")

            with Horizontal(id="buttons"):
                yield Button("Retry", id="retry", variant="primary")
                yield Button("View Details", id="details", variant="default")
                yield Button("Exit", id="exit", variant="error")

    def _get_troubleshooting_tip(self, error_type: str, error_msg: str) -> str:
        """Get troubleshooting guidance based on error type.

        Args:
            error_type: The exception class name
            error_msg: The error message

        Returns:
            Helpful troubleshooting tip for the user
        """
        error_msg_lower = error_msg.lower()

        # Configuration file errors
        if "yaml" in error_type.lower() or "yaml" in error_msg_lower:
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Check your configuration file for syntax errors\n"
                "• Verify YAML formatting (indentation, colons, quotes)\n"
                "• Try running: consoul config validate"
            )

        # File not found errors
        if "filenotfound" in error_type.lower() or "not found" in error_msg_lower:
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Run 'consoul config init' to create default configuration\n"
                "• Check that ~/.consoul/config.yaml exists\n"
                "• Verify file paths in your configuration"
            )

        # Network/connection errors
        if any(
            keyword in error_type.lower() or keyword in error_msg_lower
            for keyword in ["connection", "network", "timeout", "unreachable"]
        ):
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Check your internet connection\n"
                "• Verify the AI provider service is available\n"
                "• Check for firewall or proxy issues\n"
                "• Try again in a few moments"
            )

        # Authentication errors
        if any(
            keyword in error_type.lower() or keyword in error_msg_lower
            for keyword in ["auth", "api key", "credential", "permission", "401", "403"]
        ):
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Verify your API key is correct and active\n"
                "• Check that environment variables are set\n"
                "• Ensure API key has required permissions\n"
                "• Try regenerating your API key"
            )

        # Database errors
        if any(
            keyword in error_type.lower() or keyword in error_msg_lower
            for keyword in ["database", "sqlite", "db", "sql"]
        ):
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Check database file permissions\n"
                "• Verify disk space is available\n"
                "• Try deleting and recreating database\n"
                "• Database location: ~/.consoul/conversations.db"
            )

        # Import/module errors
        if any(
            keyword in error_type.lower()
            for keyword in ["import", "module", "attribute"]
        ):
            return (
                "[yellow]💡 Troubleshooting:[/yellow]\n"
                "• Reinstall Consoul: pip install --force-reinstall consoul\n"
                "• Check Python version (3.12+ required)\n"
                "• Verify all dependencies are installed\n"
                "• Try in a fresh virtual environment"
            )

        # Generic fallback
        return (
            "[yellow]💡 Troubleshooting:[/yellow]\n"
            "• Check the error details below for more information\n"
            "• Try running with --debug flag for verbose logging\n"
            "• Report persistent issues at:\n"
            "  https://github.com/goatbytes/consoul/issues"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: The button pressed event
        """
        if event.button.id == "retry":
            self._handle_retry()
        elif event.button.id == "details":
            self._toggle_details()
        elif event.button.id == "exit":
            self._handle_exit()

    def _handle_retry(self) -> None:
        """Handle retry button - restart initialization."""
        # Pop this error screen
        self.dismiss()

        # Restart initialization if we have app reference
        if self.app_instance and hasattr(self.app_instance, "_start_initialization"):
            self.app_instance.log.info("[ERROR SCREEN] Retrying initialization...")
            self.app_instance._start_initialization()
        else:
            if self.app_instance:
                self.app_instance.log.warning(
                    "[ERROR SCREEN] Cannot retry: app instance not available"
                )

    def _toggle_details(self) -> None:
        """Toggle visibility of stack trace details."""
        self.show_details = not self.show_details
        details_widget = self.query_one("#error-details", Static)

        if self.show_details:
            details_widget.styles.display = "block"
            self.query_one("#details", Button).label = "Hide Details"
        else:
            details_widget.styles.display = "none"
            self.query_one("#details", Button).label = "View Details"

    def _handle_exit(self) -> None:
        """Handle exit button - gracefully exit application."""
        if self.app_instance:
            self.app_instance.log.info(
                "[ERROR SCREEN] User requested exit after initialization failure"
            )
        # Exit with error code 1
        self.app.exit(return_code=1)
        sys.exit(1)
