"""InputArea widget for multi-line text input with keyboard shortcuts.

This module provides a text input area that supports multi-line messages
with Enter to send and Shift+Enter for newlines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import TextArea

if TYPE_CHECKING:
    from textual import events

__all__ = ["InputArea"]


class InputArea(Container):
    """Multi-line text input area for composing messages.

    Supports Enter to send, Shift+Enter for newlines, and Escape to clear.
    Posts MessageSubmit events when user sends a message.

    Attributes:
        character_count: Number of characters in the input
    """

    class MessageSubmit(Message):
        """Message posted when user submits input.

        Attributes:
            content: The message content that was submitted
        """

        def __init__(self, content: str) -> None:
            """Initialize MessageSubmit.

            Args:
                content: The submitted message text
            """
            super().__init__()
            self.content = content

    # Reactive state
    character_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        """Initialize InputArea widget.

        Args:
            **kwargs: Additional arguments passed to Container
        """
        super().__init__(**kwargs)
        self.text_area = TextArea()
        self.text_area.show_line_numbers = False

    def compose(self) -> list[TextArea]:
        """Compose the input area widgets.

        Returns:
            List containing the TextArea widget
        """
        return [self.text_area]

    def on_mount(self) -> None:
        """Initialize input area on mount."""
        self.border_title = "Message (Enter to send, Shift+Enter for newline)"
        self.can_focus = True

        # Focus the text area
        self.text_area.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update character count when text changes.

        Args:
            event: The text change event
        """
        self.character_count = len(self.text_area.text)

        # Update border title with count
        if self.character_count > 0:
            self.border_title = (
                f"Message ({self.character_count} chars) - Enter to send"
            )
        else:
            self.border_title = "Message (Enter to send, Shift+Enter for newline)"

    async def on_key(self, event: events.Key) -> None:
        """Handle keyboard shortcuts.

        Args:
            event: The key event
        """
        # Enter without shift = send
        if (event.key == "enter" and not event.shift and not event.ctrl) or (
            event.key == "enter" and event.ctrl
        ):
            event.prevent_default()
            await self._send_message()

        # Shift+Enter = newline (default TextArea behavior, don't prevent)

        # Escape = clear
        elif event.key == "escape":
            event.prevent_default()
            self.clear()

    async def _send_message(self) -> None:
        """Send the current message.

        Validates content, posts MessageSubmit event, and clears input.
        Empty or whitespace-only messages are not sent.
        """
        content = self.text_area.text.strip()

        if not content:
            return  # Don't send empty messages

        # Post message event
        self.post_message(self.MessageSubmit(content))

        # Clear input
        self.clear()

    def clear(self) -> None:
        """Clear the input area and reset character count."""
        self.text_area.clear()
        self.character_count = 0
        self.text_area.focus()
