"""JSON formatter for conversation export/import."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from consoul.formatters.base import ExportFormatter


class JSONFormatter(ExportFormatter):
    """Export conversations in structured JSON format.

    This format is designed for round-trip import/export and preserves
    all conversation metadata and message data.

    Format specification (v1.0):
        {
            "version": "1.0",
            "exported_at": "ISO 8601 timestamp",
            "conversation": {
                "session_id": "string",
                "model": "string",
                "created_at": "ISO 8601 timestamp",
                "updated_at": "ISO 8601 timestamp",
                "message_count": int
            },
            "messages": [
                {
                    "role": "user|assistant|system",
                    "content": "string",
                    "timestamp": "ISO 8601 timestamp",
                    "tokens": int | null
                }
            ]
        }
    """

    VERSION = "1.0"

    def export(self, metadata: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        """Export conversation to JSON format.

        Args:
            metadata: Conversation metadata from database
            messages: List of message dicts from database

        Returns:
            JSON string with conversation data
        """
        data = {
            "version": self.VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "conversation": {
                "session_id": metadata["session_id"],
                "model": metadata["model"],
                "created_at": metadata["created_at"],
                "updated_at": metadata["updated_at"],
                "message_count": metadata["message_count"],
            },
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"],
                    "tokens": msg.get("tokens"),
                }
                for msg in messages
            ],
        }

        return json.dumps(data, indent=2, ensure_ascii=False)

    @property
    def file_extension(self) -> str:
        """Get file extension for JSON format."""
        return "json"

    @staticmethod
    def validate_import_data(data: dict[str, Any]) -> None:
        """Validate imported JSON data structure.

        Args:
            data: Parsed JSON data

        Raises:
            ValueError: If data structure is invalid
        """
        # Check version
        version = data.get("version")
        if version != JSONFormatter.VERSION:
            raise ValueError(
                f"Unsupported export version: {version}. "
                f"Expected version {JSONFormatter.VERSION}"
            )

        # Check required top-level keys
        required_keys = {"version", "exported_at", "conversation", "messages"}
        missing_keys = required_keys - set(data.keys())
        if missing_keys:
            raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

        # Check conversation metadata
        conv = data["conversation"]
        required_conv_keys = {"session_id", "model", "created_at", "updated_at"}
        missing_conv_keys = required_conv_keys - set(conv.keys())
        if missing_conv_keys:
            raise ValueError(
                f"Missing conversation keys: {', '.join(missing_conv_keys)}"
            )

        # Check messages structure
        messages = data["messages"]
        if not isinstance(messages, list):
            raise ValueError("'messages' must be a list")

        for i, msg in enumerate(messages):
            required_msg_keys = {"role", "content", "timestamp"}
            missing_msg_keys = required_msg_keys - set(msg.keys())
            if missing_msg_keys:
                raise ValueError(
                    f"Message {i} missing keys: {', '.join(missing_msg_keys)}"
                )

            # Validate role
            if msg["role"] not in {"user", "assistant", "system"}:
                raise ValueError(
                    f"Message {i} has invalid role: {msg['role']}. "
                    f"Must be one of: user, assistant, system"
                )
