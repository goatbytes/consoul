"""InputArea widget for multi-line text input with keyboard shortcuts and file attachments.

This module provides a text input area that supports multi-line messages
with Enter to send and Shift+Enter for newlines, plus file attachment functionality.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import TextArea

if TYPE_CHECKING:
    from textual import events
    from textual.app import ComposeResult
    from textual.binding import BindingType

__all__ = ["AttachedFile", "InputArea"]


@dataclass
class AttachedFile:
    """Metadata for an attached file.

    Attributes:
        path: Absolute path to the file
        type: File type classification (image/code/document/data/unknown)
        mime_type: MIME type of the file
        size: File size in bytes
    """

    path: str
    type: str
    mime_type: str
    size: int


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
        self.attached_files: list[AttachedFile] = []

    def compose(self) -> ComposeResult:
        """Compose the input area widgets with attachment support.

        Yields:
            Horizontal input controls (text area + attachment button)
            Horizontal file chips container
        """
        with Horizontal(id="input-controls"):
            from consoul.tui.widgets.attachment_button import AttachmentButton
            from consoul.tui.widgets.send_button import SendButton

            yield self.text_area
            yield AttachmentButton()
            yield SendButton()
        with Horizontal(id="file-chips-container"):
            # Dynamically populated with FileChip widgets
            pass

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

    def on_send_button_message_submit(
        self, event: SendButton.MessageSubmit
    ) -> None:
        """Handle Send button click from SendButton widget.

        Args:
            event: MessageSubmit event from SendButton
        """
        from consoul.tui.widgets.send_button import SendButton

        # Get current text content
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
        self._update_border_title()
        self.text_area.focus()

    def _classify_file(self, path: str) -> str:
        """Classify file by extension.

        Args:
            path: File path to classify

        Returns:
            Type classification: image, code, document, data, or unknown
        """
        ext = Path(path).suffix.lower()

        if ext in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
            return "image"
        elif ext in {
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".rs",
            ".go",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
        }:
            return "code"
        elif ext in {".pdf", ".md", ".txt", ".rst", ".doc", ".docx"}:
            return "document"
        elif ext in {".json", ".yaml", ".yml", ".csv", ".xml", ".toml"}:
            return "data"
        else:
            return "unknown"

    def on_attachment_button_attachment_selected(self, event: Message) -> None:
        """Handle file selection from attachment button.

        Validates files by type, size, and existence, then adds to attached_files list.

        Args:
            event: AttachmentSelected message with file_paths attribute
        """
        from consoul.tui.widgets.attachment_button import AttachmentButton

        # Type guard
        if not isinstance(event, AttachmentButton.AttachmentSelected):
            return

        # Get config
        try:
            config = self.app.consoul_config.tools  # type: ignore[attr-defined]
        except AttributeError:
            # Fallback if config not available
            return

        for path in event.file_paths:
            file_type = self._classify_file(path)

            # Validate images
            if file_type == "image":
                if not config.image_analysis.enabled:
                    self.app.notify(
                        "Image analysis is disabled. Image will be referenced by filename only.",
                        severity="warning",
                    )

                # Check image-specific limits
                image_count = sum(1 for f in self.attached_files if f.type == "image")
                if image_count >= config.image_analysis.max_images_per_query:
                    self.app.notify(
                        f"Maximum {config.image_analysis.max_images_per_query} images per message",
                        severity="error",
                    )
                    continue

            # Validate file existence and size
            try:
                path_obj = Path(path)
                if not path_obj.exists():
                    self.app.notify(f"File not found: {path}", severity="error")
                    continue

                size = path_obj.stat().st_size
                max_size = 20 * 1024 * 1024  # 20MB limit

                if size > max_size:
                    self.app.notify(
                        f"File too large: {path_obj.name} ({size / (1024 * 1024):.1f}MB > 20MB)",
                        severity="error",
                    )
                    continue

                # Get MIME type
                mime_type, _ = mimetypes.guess_type(path)
                if not mime_type:
                    mime_type = "application/octet-stream"

                # Add to attached files
                self.attached_files.append(
                    AttachedFile(
                        path=path,
                        type=file_type,
                        mime_type=mime_type,
                        size=size,
                    )
                )

            except Exception as e:
                self.app.notify(f"Error reading file: {e}", severity="error")
                continue

        # Update UI
        self._update_file_chips()

    def on_file_chip_remove_requested(self, event: Message) -> None:
        """Handle remove request from FileChip.

        Args:
            event: RemoveRequested message with file_path attribute
        """
        from consoul.tui.widgets.file_chip import FileChip

        # Type guard
        if not isinstance(event, FileChip.RemoveRequested):
            return

        # Remove from attached files list
        self.attached_files = [
            f for f in self.attached_files if f.path != event.file_path
        ]

        # Update UI
        self._update_file_chips()

    def _update_file_chips(self) -> None:
        """Update the file chips container with current attached files."""
        from consoul.tui.widgets.file_chip import FileChip

        try:
            container = self.query_one("#file-chips-container")
            container.remove_children()

            for file in self.attached_files:
                container.mount(FileChip(file.path, file.type))
        except Exception:
            # Container might not be mounted yet
            pass
