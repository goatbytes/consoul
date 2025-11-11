"""InputArea widget for multi-line text input with keyboard shortcuts.

This module provides a text input area that supports multi-line messages
with Enter to send and Shift+Enter for newlines.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import TextArea

if TYPE_CHECKING:
    from textual import events
    from textual.binding import BindingType

__all__ = ["InputArea"]


class SendableTextArea(TextArea):
    """TextArea that sends message on Enter, newline on Shift+Enter.

    This subclass intercepts key events BEFORE TextArea processes them,
    allowing us to handle Enter for sending while preserving Shift+Enter
    for newlines.
    """

    class Submitted(Message):
        """Posted when Enter (without Shift) is pressed.

        Attributes:
            text: The text content when submitted
        """

        def __init__(self, text: str) -> None:
            """Initialize Submitted message.

            Args:
                text: The text content
            """
            super().__init__()
            self.text = text

    async def _on_key(self, event: events.Key) -> None:
        """Intercept keys BEFORE TextArea processes them.

        This is called BEFORE the default TextArea key handling,
        allowing us to intercept Enter while letting Shift+Enter through.

        Args:
            event: The key event
        """
        # Check for plain Enter (without Shift modifier)
        # When Shift is pressed, the key becomes "shift+enter", not "enter"
        if event.key == "enter":
            # Prevent TextArea from inserting a newline
            event.prevent_default()
            event.stop()

            # Post submitted event to parent
            self.post_message(self.Submitted(self.text))
            return

        # Handle Shift+Enter to insert newline manually
        if event.key == "shift+enter":
            event.prevent_default()
            event.stop()

            # Insert newline at cursor position
            self.insert("\n")
            return

        # For all other keys, delegate to TextArea
        await super()._on_key(event)


class InputArea(Container):
    """Multi-line text input area for composing messages.

    Supports Enter to send, Shift+Enter for newlines, and Escape to clear.
    Posts MessageSubmit events when user sends a message.

    Attributes:
        character_count: Number of characters in the input
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        # Note: Enter binding is handled in on_key to allow Shift+Enter for newlines
        Binding("escape", "clear_input", "Clear", show=False),
    ]

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
        self.text_area = SendableTextArea()
        self.text_area.show_line_numbers = False
        self.text_area.can_focus = True

    def compose(self) -> list[SendableTextArea]:
        """Compose the input area widgets.

        Returns:
            List containing the SendableTextArea widget
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
        self._update_border_title()

    def _update_border_title(self) -> None:
        """Update border title based on character count.

        Shows character count when text is present, otherwise shows help text.
        """
        if self.character_count > 0:
            self.border_title = (
                f"Message ({self.character_count} chars) - Enter to send"
            )
        else:
            self.border_title = "Message (Enter to send, Shift+Enter for newline)"

    def action_clear_input(self) -> None:
        """Action to clear the input (bound to Escape key)."""
        self.clear()

    def on_sendable_text_area_submitted(
        self, event: SendableTextArea.Submitted
    ) -> None:
        """Handle submission from SendableTextArea (Enter key pressed).

        Args:
            event: Submitted event containing the text
        """
        content = event.text.strip()

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
        self._update_border_title()
        self.text_area.focus()
