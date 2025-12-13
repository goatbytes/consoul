"""TUI utility functions and helpers.

This package contains utility functions for error handling, formatting,
attachment processing, message preparation, and other common TUI operations.
"""

from __future__ import annotations

from consoul.tui.utils.attachment_handler import (
    process_image_attachments,
    process_text_attachments,
    validate_attachment_size,
)
from consoul.tui.utils.message_preparation import (
    create_error_bubble,
    create_model_not_initialized_error,
    inject_command_output,
)

__all__ = [
    "create_error_bubble",
    "create_model_not_initialized_error",
    "inject_command_output",
    "process_image_attachments",
    "process_text_attachments",
    "validate_attachment_size",
]
