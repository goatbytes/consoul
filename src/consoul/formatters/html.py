"""HTML formatter for conversation export."""

from __future__ import annotations

import html
from typing import Any

from consoul.formatters.base import ExportFormatter

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consoul Conversation - {session_id}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        .header h1 {{
            font-size: 1.8em;
            margin-bottom: 15px;
        }}
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            opacity: 0.95;
        }}
        .metadata-item {{
            font-size: 0.9em;
        }}
        .metadata-label {{
            font-weight: 600;
            opacity: 0.9;
        }}
        .messages {{
            padding: 20px 30px 30px;
        }}
        .message {{
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        .message.system {{
            background: #fff3cd;
            border-left-color: #ffc107;
        }}
        .message.user {{
            background: #d1ecf1;
            border-left-color: #17a2b8;
        }}
        .message.assistant {{
            background: #d4edda;
            border-left-color: #28a745;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }}
        .role {{
            font-weight: 600;
            font-size: 1.1em;
            text-transform: capitalize;
        }}
        .meta {{
            color: #666;
            font-size: 0.85em;
        }}
        .content {{
            white-space: pre-wrap;
            word-wrap: break-word;
            line-height: 1.7;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
        }}
        pre {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: "Courier New", Courier, monospace;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 Consoul Conversation</h1>
            <div class="metadata">
                <div class="metadata-item">
                    <span class="metadata-label">Session:</span> {session_id}
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Model:</span> {model}
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Created:</span> {created_at}
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Updated:</span> {updated_at}
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Messages:</span> {message_count}
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Total Tokens:</span> {total_tokens}
                </div>
            </div>
        </div>
        <div class="messages">
{messages}
        </div>
        <div class="footer">
            Exported from Consoul • {exported_at}
        </div>
    </div>
</body>
</html>"""

MESSAGE_TEMPLATE = """            <div class="message {role}">
                <div class="message-header">
                    <span class="role">{role_emoji} {role_title}</span>
                    <span class="meta">{timestamp} • {tokens} tokens</span>
                </div>
                <div class="content">{content}</div>
            </div>"""


class HTMLFormatter(ExportFormatter):
    """Export conversations in standalone HTML format.

    Creates a self-contained HTML file with embedded CSS styling.
    The output can be opened directly in a web browser for viewing
    and sharing.
    """

    def export(self, metadata: dict[str, Any], messages: list[dict[str, Any]]) -> str:
        """Export conversation to HTML format.

        Args:
            metadata: Conversation metadata from database
            messages: List of message dicts from database

        Returns:
            HTML string with embedded styling
        """
        from datetime import datetime, timezone

        # Calculate total tokens
        total_tokens = sum(msg.get("tokens") or 0 for msg in messages)

        # Format messages
        messages_html = []
        for msg in messages:
            role = msg["role"]
            role_emoji = self._get_role_emoji(role)
            content = html.escape(msg["content"])

            message_html = MESSAGE_TEMPLATE.format(
                role=role,
                role_emoji=role_emoji,
                role_title=role.title(),
                timestamp=html.escape(msg["timestamp"]),
                tokens=msg.get("tokens") or 0,
                content=content,
            )
            messages_html.append(message_html)

        # Build final HTML
        return HTML_TEMPLATE.format(
            session_id=html.escape(metadata["session_id"]),
            model=html.escape(metadata["model"]),
            created_at=html.escape(metadata["created_at"]),
            updated_at=html.escape(metadata["updated_at"]),
            message_count=metadata["message_count"],
            total_tokens=total_tokens,
            messages="\n".join(messages_html),
            exported_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

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
        """Get file extension for HTML format."""
        return "html"
