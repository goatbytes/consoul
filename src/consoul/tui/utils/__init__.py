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
from consoul.tui.utils.attachment_persistence import (
    display_reconstructed_attachments,
    persist_attachments,
)
from consoul.tui.utils.conversation_helpers import extract_tool_calls_from_conversation
from consoul.tui.utils.message_preparation import (
    create_error_bubble,
    create_model_not_initialized_error,
    inject_command_output,
)
from consoul.tui.utils.message_renderer import (
    render_tool_calls,
    render_ui_message,
    render_ui_messages_to_chat,
)

__all__ = [
    "create_error_bubble",
    "create_model_not_initialized_error",
    "display_reconstructed_attachments",
    "extract_tool_calls_from_conversation",
    "inject_command_output",
    "persist_attachments",
    "process_image_attachments",
    "process_text_attachments",
    "render_tool_calls",
    "render_ui_message",
    "render_ui_messages_to_chat",
    "validate_attachment_size",
]
