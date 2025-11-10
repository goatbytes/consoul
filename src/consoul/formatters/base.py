"""Base interface for conversation export formatters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class ExportFormatter(ABC):
    """Base class for conversation export formatters.

    Formatters convert conversation data (metadata + messages) into
    various output formats for different use cases.
    """

    @abstractmethod
    def export(self, metadata: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        """Export conversation to formatted string.

        Args:
            metadata: Conversation metadata (session_id, model, created_at, etc.)
            messages: List of message dicts (role, content, timestamp, tokens)

        Returns:
            Formatted string representation of the conversation
        """
        pass

    def export_to_file(
        self,
        metadata: dict[str, Any],
        messages: list[dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Export conversation to file.

        Args:
            metadata: Conversation metadata
            messages: List of messages
            output_path: Path to write output file

        Raises:
            IOError: If file cannot be written
        """
        content = self.export(metadata, messages)
        output_path.write_text(content, encoding="utf-8")

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Get the default file extension for this format (e.g., 'json', 'md')."""
        pass
