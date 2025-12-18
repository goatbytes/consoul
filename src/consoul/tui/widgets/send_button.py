"""SendButton widget for submitting messages.

This widget provides a button that submits the current message text,
matching the style and behavior of the AttachmentButton.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from textual.message import Message
from textual.widgets import Button

__all__ = ["SendButton"]


class SendButton(Button):
    """Button that submits the current message.

    Posts MessageSubmit message when clicked, matching the style
    of the AttachmentButton for UI consistency.

    Attributes:
        DEFAULT_VARIANT: Button variant (default styling)
    """

    DEFAULT_VARIANT: ClassVar[
        Literal["default", "primary", "success", "warning", "error"]
    ] = "default"

    class MessageSubmit(Message):
        """Message posted when user clicks the send button.

        Attributes:
            content: The message content to send
        """

        def __init__(self, content: str) -> None:
            """Initialize MessageSubmit message.

            Args:
                content: The message text to send
            """
            super().__init__()
            self.content = content

    def __init__(self) -> None:
        """Initialize SendButton with send label."""
        super().__init__("↑ Send", id="send-button", variant=self.DEFAULT_VARIANT)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press by posting MessageSubmit.

        Args:
            event: Button press event
        """
        # Prevent event from bubbling
        event.stop()

        # Post message to trigger send
        self.post_message(self.MessageSubmit(""))
