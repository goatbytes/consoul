"""FileChip widget for displaying attached files with remove functionality.

This widget shows an attached file with a type-specific icon, filename,
file size, and a remove button.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["FileChip"]


class FileChip(Horizontal):
    """Display an attached file with icon, name, size, and remove button.

    Shows a horizontal chip with:
    - Type-specific emoji icon (🖼️ for images, 💾 for code, etc.)
    - Filename and human-readable file size
    - Remove button (x) to delete the attachment

    Attributes:
        file_path: Absolute path to the attached file
        file_type: Type classification (image/code/document/data/unknown)
    """

    DEFAULT_CSS = """
    FileChip {
        width: auto;
        height: 3;
        background: $panel;
        border: solid $primary;
        padding: 0 1;
        margin-right: 1;
    }

    FileChip Label {
        width: auto;
        padding-right: 1;
    }

    FileChip Button {
        width: 3;
        min-width: 3;
    }
    """

    class RemoveRequested(Message):
        """Message posted when user clicks the remove button.

        Attributes:
            file_path: Path to the file that should be removed
        """

        def __init__(self, file_path: str) -> None:
            """Initialize RemoveRequested message.

            Args:
                file_path: Path to file to remove
            """
            super().__init__()
            self.file_path = file_path

    def __init__(self, file_path: str, file_type: str = "unknown") -> None:
        """Initialize FileChip.

        Args:
            file_path: Absolute path to the file
            file_type: Type classification (image/code/document/data/unknown)
        """
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type

    def compose(self) -> ComposeResult:
        """Compose the file chip with icon, filename, size, and remove button.

        Yields:
            Label with icon, filename, and size
            Button for removing the chip
        """
        filename = Path(self.file_path).name
        icon = self._get_file_icon(self.file_type)

        # Try to get file size
        try:
            size = Path(self.file_path).stat().st_size
            size_str = self._format_size(size)
            yield Label(f"{icon} {filename} ({size_str})", id="file-info")
        except Exception:
            # File might not exist or be accessible
            yield Label(f"{icon} {filename}", id="file-info")

        yield Button("x", id="remove-chip", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle remove button press.

        Posts RemoveRequested message and removes this widget from the DOM.

        Args:
            event: Button press event
        """
        if event.button.id == "remove-chip":
            # Post removal request
            self.post_message(self.RemoveRequested(self.file_path))
            # Remove this chip from the UI
            self.remove()

    def _get_file_icon(self, file_type: str) -> str:
        """Get emoji icon based on file type.

        Args:
            file_type: Type classification string

        Returns:
            Emoji icon representing the file type
        """
        icons = {
            "image": "🖼️",
            "code": "💾",
            "document": "📄",
            "data": "📊",
            "unknown": "📎",
        }
        return icons.get(file_type, "📎")

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format.

        Args:
            size: File size in bytes

        Returns:
            Formatted string like "1.5KB" or "2.3MB"
        """
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        else:
            return f"{size / (1024 * 1024):.1f}MB"
