"""HistoricalFileChip widget for displaying attachments from saved conversations.

This widget shows an attachment from a loaded conversation with read-only display.
Unlike FileChip, it has no remove button and indicates if the file no longer exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.containers import Horizontal
from textual.widgets import Label

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["HistoricalFileChip"]


class HistoricalFileChip(Horizontal):
    """Display a historical file attachment (read-only, no remove button).

    Shows a horizontal chip with:
    - Type-specific emoji icon
    - Filename and file size (if available)
    - Warning indicator if file no longer exists

    Attributes:
        file_path: Absolute path to the attached file
        file_type: Type classification (image/code/document/data/unknown)
        file_exists: Whether the file still exists on disk
    """

    DEFAULT_CSS = """
    HistoricalFileChip {
        width: auto;
        height: auto;
        background: $surface;
        border: solid $primary-darken-2;
        padding: 0 1;
        margin-right: 1;
        margin-bottom: 1;
    }

    HistoricalFileChip.missing {
        background: $error 20%;
        border: solid $error;
        opacity: 0.7;
    }

    HistoricalFileChip Label {
        width: auto;
    }

    HistoricalFileChip .warning-icon {
        color: $warning;
        padding-right: 1;
    }
    """

    def __init__(
        self,
        file_path: str,
        file_type: str = "unknown",
        file_size: int | None = None,
    ) -> None:
        """Initialize HistoricalFileChip.

        Args:
            file_path: Absolute path to the file
            file_type: Type classification (image/code/document/data/unknown)
            file_size: Optional stored file size (used if file doesn't exist)
        """
        super().__init__()
        self.file_path = file_path
        self.file_type = file_type
        self.stored_file_size = file_size
        self.file_exists = Path(file_path).exists() if file_path else False

    def compose(self) -> ComposeResult:
        """Compose the file chip with icon and filename.

        Yields:
            Labels showing file info and optional warning
        """
        filename = Path(self.file_path).name if self.file_path else "Unknown file"
        icon = self._get_file_icon(self.file_type)

        # Warning indicator for missing files
        if not self.file_exists:
            yield Label("⚠️", classes="warning-icon")

        # Try to get current file size, fall back to stored size
        size_str = ""
        if self.file_exists:
            try:
                size = Path(self.file_path).stat().st_size
                size_str = f" ({self._format_size(size)})"
            except Exception:
                if self.stored_file_size:
                    size_str = f" ({self._format_size(self.stored_file_size)})"
        elif self.stored_file_size:
            size_str = f" ({self._format_size(self.stored_file_size)})"

        yield Label(f"{icon} {filename}{size_str}", id="file-info")

    def on_mount(self) -> None:
        """Apply styling based on file existence."""
        if not self.file_exists:
            self.add_class("missing")

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
