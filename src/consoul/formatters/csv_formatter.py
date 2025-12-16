"""CSV formatter for conversation export."""

from __future__ import annotations

import csv
import io
from typing import Any

from consoul.formatters.base import ExportFormatter


class CSVFormatter(ExportFormatter):
    """Export conversations in CSV format.

    Creates a CSV file with one row per message, suitable for
    importing into spreadsheets or analytics tools.

    Columns:
        - session_id: Conversation session ID
        - model: Model name used
        - timestamp: Message timestamp (ISO 8601)
        - role: Message role (user, assistant, system)
        - content: Message content
        - tokens: Token count (null if not available)
    """

    def export(self, metadata: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        """Export conversation to CSV format.

        Args:
            metadata: Conversation metadata from database
            messages: List of message dicts from database

        Returns:
            CSV-formatted string
        """
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "session_id",
                "model",
                "timestamp",
                "role",
                "content",
                "tokens",
            ],
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for msg in messages:
            writer.writerow(
                {
                    "session_id": metadata["session_id"],
                    "model": metadata["model"],
                    "timestamp": msg["timestamp"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "tokens": msg.get("tokens") or "",
                }
            )

        return output.getvalue()

    @property
    def file_extension(self) -> str:
        """Get file extension for CSV format."""
        return "csv"
