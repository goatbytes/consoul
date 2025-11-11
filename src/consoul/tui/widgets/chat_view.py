"""ChatView widget for displaying conversation messages.

This module provides the main chat display area that shows conversation
messages in a scrollable vertical layout with auto-scrolling support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.reactive import reactive

if TYPE_CHECKING:
    from textual.widget import Widget

__all__ = ["ChatView"]


class ChatView(VerticalScroll):
    """Main chat message display area.

    Displays conversation messages in a scrollable vertical layout.
    Automatically scrolls to bottom when new messages arrive.

    Attributes:
        auto_scroll: Whether to automatically scroll to bottom on new messages
        message_count: Number of messages currently displayed
    """

    # Reactive state
    auto_scroll: reactive[bool] = reactive(True)
    message_count: reactive[int] = reactive(0)

    def __init__(self) -> None:
        """Initialize ChatView."""
        super().__init__()
        self.can_focus = True
        self._typing_indicator: Widget | None = None

    def on_mount(self) -> None:
        """Initialize chat view on mount."""
        self.border_title = "Conversation"

    async def add_message(self, message_widget: Widget) -> None:
        """Add a message to the chat view.

        Mounts the message widget and auto-scrolls to bottom if enabled.

        Args:
            message_widget: Widget (typically MessageBubble) to add
        """
        await self.mount(message_widget)
        self.message_count += 1

        if self.auto_scroll:
            # Scroll to bottom to show new message
            self.scroll_end(animate=True)

    async def clear_messages(self) -> None:
        """Remove all messages from the chat view.

        Resets message count to 0 and removes all child widgets.
        """
        await self.remove_children()
        self.message_count = 0

    def watch_message_count(self, count: int) -> None:
        """Update border title with message count.

        Called automatically when message_count changes.

        Args:
            count: New message count value
        """
        if count > 0:
            self.border_title = f"Conversation ({count} messages)"
        else:
            self.border_title = "Conversation"

    async def show_typing_indicator(self) -> None:
        """Show typing indicator to signal AI is processing.

        Displays animated "Thinking..." indicator below last message.
        Call hide_typing_indicator() when first streaming token arrives.
        """
        from consoul.tui.widgets.typing_indicator import TypingIndicator

        # Only show if not already showing
        if self._typing_indicator is None:
            self._typing_indicator = TypingIndicator()
            await self.mount(self._typing_indicator)

            if self.auto_scroll:
                self.scroll_end(animate=True)

    async def hide_typing_indicator(self) -> None:
        """Hide typing indicator when streaming begins.

        Removes the typing indicator widget if currently displayed.
        Safe to call even if indicator is not showing.
        """
        if self._typing_indicator is not None:
            await self._typing_indicator.remove()
            self._typing_indicator = None
