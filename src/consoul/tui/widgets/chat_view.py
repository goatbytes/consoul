"""ChatView widget for displaying conversation messages.

This module provides the main chat display area that shows conversation
messages in a scrollable vertical layout with auto-scrolling support.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.containers import VerticalScroll
from textual.events import MouseScrollDown, MouseScrollUp
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
        self._user_scrolled_away = False  # Track if user manually scrolled away from bottom

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

        # Only auto-scroll if enabled AND user hasn't manually scrolled away
        if self.auto_scroll and not self._user_scrolled_away:
            # Defer scroll until after layout pass to avoid race condition
            # Widget height isn't finalized until after next layout
            logger.info(
                f"[SCROLL] Scheduling scroll_end after message add - "
                f"role: {role}, scroll_y: {self.scroll_y}"
            )
            self.call_after_refresh(self.scroll_end, animate=True)
        elif self._user_scrolled_away:
            logger.debug(
                f"[SCROLL] Skipping auto-scroll - user scrolled away "
                f"(role: {role}, scroll_y: {self.scroll_y})"
            )

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

            # Only auto-scroll if enabled AND user hasn't manually scrolled away
            if self.auto_scroll and not self._user_scrolled_away:
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

    def _is_at_bottom(self) -> bool:
        """Check if the scroll position is at or near the bottom.

        Returns:
            True if within 5 units of the bottom, False otherwise
        """
        return self.scroll_y >= self.max_scroll_y - 5

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        """Handle mouse scroll up event to detect user scrolling away from bottom.

        When user scrolls up and they're currently at/near the bottom, we suspend
        auto-scroll to let them review previous messages without being yanked back down.

        Args:
            event: MouseScrollUp event from Textual
        """
        # If user is scrolling up from the bottom, mark that they've scrolled away
        if self._is_at_bottom():
            self._user_scrolled_away = True
            logger.debug(
                f"[SCROLL] User scrolled up from bottom - suspending auto-scroll "
                f"(scroll_y: {self.scroll_y}, max: {self.max_scroll_y})"
            )

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        """Handle mouse scroll down event to detect user returning to bottom.

        When user scrolls back down to the bottom, we re-enable auto-scroll.

        Args:
            event: MouseScrollDown event from Textual
        """
        # Re-enable auto-scroll if user scrolls back to bottom
        if self._user_scrolled_away and self._is_at_bottom():
            self._user_scrolled_away = False
            logger.debug(
                f"[SCROLL] User scrolled back to bottom - resuming auto-scroll "
                f"(scroll_y: {self.scroll_y}, max: {self.max_scroll_y})"
            )
