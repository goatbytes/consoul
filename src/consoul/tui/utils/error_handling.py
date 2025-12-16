"""Error handling utilities for TUI.

This module provides functions for graceful error handling, user-friendly
error messages, and error recovery strategies for the TUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from textual.app import App

__all__ = [
    "format_error_message",
    "handle_stream_error",
    "show_error_notification",
]


def handle_stream_error(error: Exception, app: App[None]) -> None:
    """Handle streaming errors gracefully.

    Args:
        error: The exception that occurred
        app: The Textual app instance for notifications

    Example:
        >>> try:
        ...     await stream_ai_response()
        ... except Exception as e:
        ...     handle_stream_error(e, app)
    """
    # Placeholder implementation - will be enhanced in SOUL-50
    error_msg = format_error_message(error)
    app.notify(error_msg, severity="error", timeout=5)


def format_error_message(error: Exception) -> str:
    """Format an error for user-friendly display.

    Args:
        error: The exception to format

    Returns:
        User-friendly error message string

    Example:
        >>> err = ConnectionError("API unavailable")
        >>> format_error_message(err)
        'Connection error: API unavailable'
    """
    # Placeholder implementation - will be enhanced in SOUL-50
    error_type = type(error).__name__
    error_str = str(error)

    # Common error type translations
    translations = {
        "ConnectionError": "Connection error",
        "TimeoutError": "Request timed out",
        "HTTPError": "API error",
        "ValueError": "Invalid value",
    }

    friendly_type = translations.get(error_type, "Error")
    return f"{friendly_type}: {error_str}"


def show_error_notification(
    app: App[None],
    message: str,
    severity: Literal["information", "warning", "error"] = "error",
) -> None:
    """Show an error notification to the user.

    Args:
        app: The Textual app instance
        message: Error message to display
        severity: Notification severity level

    Example:
        >>> show_error_notification(app, "Failed to load conversation")
    """
    # Placeholder implementation - will be enhanced in SOUL-50
    app.notify(message, severity=severity, timeout=5)
