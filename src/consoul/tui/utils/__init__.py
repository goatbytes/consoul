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
from consoul.tui.utils.command_execution import (
    CommandExecutionHandler,
    InlineCommandInfo,
)
from consoul.tui.utils.conversation_branching import create_conversation_branch
from consoul.tui.utils.conversation_helpers import extract_tool_calls_from_conversation
from consoul.tui.utils.conversation_loading import (
    load_conversation_to_view,
    reconstruct_conversation_history,
)
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
from consoul.tui.utils.message_submission import (
    convert_attachments_to_sdk,
    handle_attachment_persistence,
)
from consoul.tui.utils.modal_helpers import (
    create_screensaver_screen,
    show_ollama_library_modal,
    show_system_prompt_modal,
)
from consoul.tui.utils.streaming_widget_manager import StreamingWidgetManager

__all__ = [
    "CommandExecutionHandler",
    "InlineCommandInfo",
    "StreamingWidgetManager",
    "convert_attachments_to_sdk",
    "create_conversation_branch",
    "create_error_bubble",
    "create_model_not_initialized_error",
    "create_screensaver_screen",
    "display_reconstructed_attachments",
    "extract_tool_calls_from_conversation",
    "handle_attachment_persistence",
    "inject_command_output",
    "load_conversation_to_view",
    "persist_attachments",
    "process_image_attachments",
    "process_text_attachments",
    "reconstruct_conversation_history",
    "render_tool_calls",
    "render_ui_message",
    "render_ui_messages_to_chat",
    "show_ollama_library_modal",
    "show_system_prompt_modal",
    "validate_attachment_size",
]
