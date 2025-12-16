"""AttachmentButton widget for file selection via TUI modal.

This widget provides a button that opens a Textual modal with directory tree
navigation to select files (images, code, documents, data) for attachment.
"""

from __future__ import annotations

from typing import ClassVar, Literal

from textual.message import Message
from textual.widgets import Button

__all__ = ["AttachmentButton"]


class AttachmentButton(Button):
    """Button that opens TUI modal for selecting files to attach.

    When clicked, opens a FileAttachmentModal with directory tree navigation
    allowing users to select multiple files using Space key to toggle selection.
    Posts AttachmentSelected message with the list of selected file paths.

    Attributes:
        DEFAULT_VARIANT: Button variant (default styling)
    """

    DEFAULT_VARIANT: ClassVar[
        Literal["default", "primary", "success", "warning", "error"]
    ] = "default"

    class AttachmentSelected(Message):
        """Message posted when user selects files from the modal.

        Attributes:
            file_paths: List of absolute paths to selected files
        """

        def __init__(self, file_paths: list[str]) -> None:
            """Initialize AttachmentSelected message.

            Args:
                file_paths: List of file paths selected by the user
            """
            super().__init__()
            self.file_paths = file_paths

    def __init__(self) -> None:
        """Initialize AttachmentButton with attach label."""
        super().__init__(
            "+ Attach", id="attachment-button", variant=self.DEFAULT_VARIANT
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press by opening file attachment modal.

        Opens FileAttachmentModal in a worker and posts AttachmentSelected
        message with the results if files were selected.

        Args:
            event: Button press event
        """
        # Prevent event from bubbling
        event.stop()

        # Run modal in a worker (required for push_screen_wait)
        self.run_worker(self._show_modal(), exclusive=False)

    async def _show_modal(self) -> None:
        """Show file attachment modal and handle result.

        Must run in a worker context to use push_screen_wait.
        """
        from consoul.tui.widgets.file_attachment_modal import FileAttachmentModal

        file_paths = await self.app.push_screen_wait(FileAttachmentModal())

        # Post message if files were selected
        if file_paths:
            self.post_message(self.AttachmentSelected(file_paths))
