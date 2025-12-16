"""Message rendering utilities for TUI.

Provides helper functions for rendering UI messages, tool calls, and attachments
to the chat view, reducing complexity in conversation loading handlers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from consoul.sdk.services import UIMessage
    from consoul.tui.widgets.chat_view import ChatView

logger = logging.getLogger(__name__)

__all__ = [
    "render_tool_calls",
    "render_ui_message",
    "render_ui_messages_to_chat",
]


async def render_tool_calls(
    chat_view: ChatView,
    tool_calls: list[dict[str, Any]],
    theme: str,
) -> None:
    """Render tool call indicators for a message.

    Args:
        chat_view: Chat view to add tool indicators to
        tool_calls: List of tool call dictionaries with 'name' and 'arguments'
        theme: Current theme name for formatting
    """
    from textual.widgets import Static

    from consoul.tui.widgets.tool_formatter import format_tool_header

    for tc in tool_calls:
        tool_name = tc.get("name", "unknown")
        tool_args = tc.get("arguments", {})
        header_renderable = format_tool_header(tool_name, tool_args, theme=theme)
        tool_indicator = Static(header_renderable, classes="system-message")
        await chat_view.add_message(tool_indicator)


async def render_ui_message(
    chat_view: ChatView,
    ui_msg: UIMessage,
    theme: str,
    thinking_to_display: str | None = None,
    attachment_display_callback: Callable[[list[dict[str, Any]]], Awaitable[None]]
    | None = None,
) -> None:
    """Render a single UI message with tool calls, bubble, and attachments.

    Args:
        chat_view: Chat view to add message to
        ui_msg: UI message object to render
        theme: Current theme name for formatting
        thinking_to_display: Optional thinking content to display for assistant messages
        attachment_display_callback: Optional async callback for displaying attachments
    """
    from consoul.tui.widgets import MessageBubble

    # Show tool execution indicator for assistant messages with tools
    if ui_msg.tool_calls and ui_msg.role == "assistant":
        await render_tool_calls(chat_view, ui_msg.tool_calls, theme)

    # Create message bubble
    bubble = MessageBubble(
        ui_msg.content,
        role=ui_msg.role,
        show_metadata=True,
        token_count=ui_msg.token_count,
        tool_calls=ui_msg.tool_calls,
        message_id=ui_msg.message_id,
        thinking_content=thinking_to_display if ui_msg.role == "assistant" else None,
        tokens_per_second=ui_msg.tokens_per_second,
        time_to_first_token=ui_msg.time_to_first_token,
    )
    await chat_view.add_message(bubble)

    # Display attachments for user messages
    if ui_msg.attachments and ui_msg.role == "user" and attachment_display_callback:
        await attachment_display_callback(ui_msg.attachments)


async def render_ui_messages_to_chat(
    chat_view: ChatView,
    ui_messages: list[UIMessage],
    theme: str,
    thinking_filter_callback: Callable[[str | None], str | None] | None = None,
    attachment_display_callback: Callable[[list[dict[str, Any]]], Awaitable[None]]
    | None = None,
) -> None:
    """Render list of UIMessages to chat view.

    Args:
        chat_view: Chat view to add messages to
        ui_messages: List of UI messages to render
        theme: Current theme name for formatting
        thinking_filter_callback: Optional callback to filter thinking content
        attachment_display_callback: Optional async callback for displaying attachments
    """
    for ui_msg in ui_messages:
        # Apply thinking display filter if provided
        thinking_to_display = None
        if thinking_filter_callback and ui_msg.thinking_content:
            thinking_to_display = thinking_filter_callback(ui_msg.thinking_content)

        await render_ui_message(
            chat_view,
            ui_msg,
            theme,
            thinking_to_display=thinking_to_display,
            attachment_display_callback=attachment_display_callback,
        )
