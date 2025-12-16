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

    Format specification (v1.0 - single conversation):
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

    Format specification (v1.0-multi - multiple conversations):
        {
            "version": "1.0-multi",
            "exported_at": "ISO 8601 timestamp",
            "conversation_count": int,
            "conversations": [
                {
                    "conversation": { ... },
                    "messages": [ ... ]
                },
                ...
            ]
        }
    """

    VERSION = "1.0"
    VERSION_MULTI = "1.0-multi"

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

    @staticmethod
    def export_multiple(
        conversations_data: list[tuple[dict[str, Any], list[dict[str, Any]]]],
    ) -> str:
        """Export multiple conversations to JSON format.

        Args:
            conversations_data: List of (metadata, messages) tuples for each conversation

        Returns:
            JSON string with multiple conversations
        """
        data = {
            "version": JSONFormatter.VERSION_MULTI,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "conversation_count": len(conversations_data),
            "conversations": [
                {
                    "conversation": {
                        "session_id": meta["session_id"],
                        "model": meta["model"],
                        "created_at": meta["created_at"],
                        "updated_at": meta["updated_at"],
                        "message_count": meta["message_count"],
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
                for meta, messages in conversations_data
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

        Supports both single (v1.0) and multi-conversation (v1.0-multi) formats.

        Args:
            data: Parsed JSON data

        Raises:
            ValueError: If data structure is invalid
        """
        # Check version
        version = data.get("version")
        if version not in {JSONFormatter.VERSION, JSONFormatter.VERSION_MULTI}:
            raise ValueError(
                f"Unsupported export version: {version}. "
                f"Expected version {JSONFormatter.VERSION} or {JSONFormatter.VERSION_MULTI}"
            )

        if version == JSONFormatter.VERSION_MULTI:
            # Validate multi-conversation format
            required_keys = {
                "version",
                "exported_at",
                "conversation_count",
                "conversations",
            }
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

            conversations = data["conversations"]
            if not isinstance(conversations, list):
                raise ValueError("'conversations' must be a list")

            for i, conv_data in enumerate(conversations):
                if "conversation" not in conv_data or "messages" not in conv_data:
                    raise ValueError(
                        f"Conversation {i} missing 'conversation' or 'messages' key"
                    )
                JSONFormatter._validate_single_conversation(
                    conv_data["conversation"], conv_data["messages"], i
                )
        else:
            # Validate single conversation format
            required_keys = {"version", "exported_at", "conversation", "messages"}
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                raise ValueError(f"Missing required keys: {', '.join(missing_keys)}")

            JSONFormatter._validate_single_conversation(
                data["conversation"], data["messages"]
            )

    @staticmethod
    def _validate_single_conversation(
        conversation: dict[str, Any],
        messages: list[dict[str, Any]],
        index: int | None = None,
    ) -> None:
        """Validate a single conversation's structure.

        Args:
            conversation: Conversation metadata dict
            messages: List of message dicts
            index: Optional conversation index (for multi-conversation imports)

        Raises:
            ValueError: If structure is invalid
        """
        prefix = f"Conversation {index}: " if index is not None else ""

        # Check conversation metadata
        required_conv_keys = {"session_id", "model", "created_at", "updated_at"}
        missing_conv_keys = required_conv_keys - set(conversation.keys())
        if missing_conv_keys:
            raise ValueError(
                f"{prefix}Missing conversation keys: {', '.join(missing_conv_keys)}"
            )

        # Check messages structure
        if not isinstance(messages, list):
            raise ValueError(f"{prefix}'messages' must be a list")

        for i, msg in enumerate(messages):
            required_msg_keys = {"role", "content", "timestamp"}
            missing_msg_keys = required_msg_keys - set(msg.keys())
            if missing_msg_keys:
                raise ValueError(
                    f"{prefix}Message {i} missing keys: {', '.join(missing_msg_keys)}"
                )

            # Validate role
            if msg["role"] not in {"user", "assistant", "system"}:
                raise ValueError(
                    f"{prefix}Message {i} has invalid role: {msg['role']}. "
                    f"Must be one of: user, assistant, system"
                )
