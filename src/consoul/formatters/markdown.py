"""Markdown formatter for conversation export."""

from __future__ import annotations

from typing import Any

from consoul.formatters.base import ExportFormatter


class MarkdownFormatter(ExportFormatter):
    """Export conversations in Markdown format.

    Creates a human-readable Markdown document with formatted messages,
    timestamps, and metadata. Ideal for documentation and sharing.
    """

    def export(self, metadata: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        """Export conversation to Markdown format.

        Args:
            metadata: Conversation metadata from database
            messages: List of message dicts from database

        Returns:
            Markdown-formatted string
        """
        lines = [
            f"# Conversation: {metadata['session_id']}",
            "",
            f"**Model**: {metadata['model']}  ",
            f"**Created**: {metadata['created_at']}  ",
            f"**Updated**: {metadata['updated_at']}  ",
            f"**Messages**: {metadata['message_count']}  ",
        ]

        # Calculate total tokens if available
        total_tokens = sum(msg.get("tokens") or 0 for msg in messages)
        if total_tokens > 0:
            lines.append(f"**Total Tokens**: {total_tokens}  ")

        lines.extend(["", "---", ""])

        # Add messages
        for msg in messages:
            role_emoji = self._get_role_emoji(msg["role"])
            tokens_str = f"{msg.get('tokens') or 0} tokens"

            lines.extend(
                [
                    f"## {role_emoji} {msg['role'].title()}",
                    "",
                    f"*{msg['timestamp']}* | *{tokens_str}*",
                    "",
                    msg["content"],
                    "",
                    "---",
                    "",
                ]
            )

        return "\n".join(lines)

    @staticmethod
    def _get_role_emoji(role: str) -> str:
        """Get emoji for message role.

        Args:
            role: Message role (user, assistant, system)

        Returns:
            Emoji string
        """
        role_emojis = {
            "system": "⚙️",
            "user": "👤",
            "assistant": "🤖",
        }
        return role_emojis.get(role, "❓")

    @property
    def file_extension(self) -> str:
        """Get file extension for Markdown format."""
        return "md"
