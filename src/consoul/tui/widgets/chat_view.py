"""ChatView widget for displaying conversation messages.

This module provides the main chat display area that shows conversation
messages in a scrollable vertical layout with auto-scrolling support.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.reactive import reactive

if TYPE_CHECKING:
    from textual.widget import Widget

__all__ = ["ChatView"]

logger = logging.getLogger(__name__)


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
        Only counts user and assistant messages (not system/error/tool messages).

        Args:
            message_widget: Widget (typically MessageBubble) to add
        """
        role = getattr(message_widget, "role", "unknown") if hasattr(message_widget, "role") else "unknown"
        logger.debug(
            f"[SCROLL] Adding message - role: {role}, "
            f"auto_scroll: {self.auto_scroll}, "
            f"current_scroll_y: {self.scroll_y}, "
            f"max_scroll_y: {self.max_scroll_y}"
        )

        await self.mount(message_widget)

        # Only count user and assistant messages (not system/error/tool)
        if hasattr(message_widget, "role"):
            if role in ("user", "assistant"):
                self.message_count += 1

        if self.auto_scroll:
            # Defer scroll until after layout pass to avoid race condition
            # Widget height isn't finalized until after next layout
            logger.info(
                f"[SCROLL] Scheduling scroll_end after message add - "
                f"role: {role}, scroll_y: {self.scroll_y}"
            )
            self.call_after_refresh(self.scroll_end, animate=True)

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
            logger.debug("[SCROLL] Showing typing indicator")
            self._typing_indicator = TypingIndicator()
            await self.mount(self._typing_indicator)

            if self.auto_scroll:
                # Defer scroll until after layout pass to avoid race condition
                # Use two refresh cycles to ensure both user message and typing indicator are laid out
                def _scroll_after_layout() -> None:
                    logger.debug(
                        f"[SCROLL] Scrolling after typing indicator layout - "
                        f"scroll_y: {self.scroll_y}, max_scroll_y: {self.max_scroll_y}"
                    )
                    self.call_after_refresh(self.scroll_end, animate=True)

                self.call_after_refresh(_scroll_after_layout)

    async def hide_typing_indicator(self) -> None:
        """Hide typing indicator when streaming begins.

        Removes the typing indicator widget if currently displayed.
        Safe to call even if indicator is not showing.
        """
        if self._typing_indicator is not None:
            await self._typing_indicator.remove()
            self._typing_indicator = None
