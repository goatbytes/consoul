"""Conversation Display Service.

This service handles loading and transforming conversation data from the database
into a format ready for UI display. It encapsulates all the business logic for:
- Loading messages from database
- Merging consecutive assistant messages
- Transforming tool call data structures
- Extracting multimodal content
- Extracting thinking tags
- Preparing UIMessage objects
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from consoul.ai.reasoning import extract_reasoning


@dataclass
class UIMessage:
    """Message prepared for UI display."""

    role: Literal["user", "assistant", "system", "error"]
    """Message role: 'user', 'assistant', 'system', or 'error'"""

    content: str
    """Display content (may be extracted from multimodal message)"""

    tool_calls: list[dict[str, Any]] | None = None
    """Tool calls in UI format (with 'name' key)"""

    attachments: list[dict[str, Any]] | None = None
    """Message attachments (for user messages)"""

    message_id: int | None = None
    """Database message ID for branching"""

    token_count: int | None = None
    """Token count from database"""

    tokens_per_second: float | None = None
    """Streaming metric from database"""

    time_to_first_token: float | None = None
    """Streaming metric from database"""

    thinking_content: str | None = None
    """Extracted thinking content for assistant messages"""


class ConversationDisplayService:
    """Service for loading and transforming conversations for display."""

    @staticmethod
    def load_conversation_for_display(
        messages: list[dict[str, Any]],
        current_model: str | None = None,
    ) -> list[UIMessage]:
        """Load and transform conversation messages for UI display.

        Args:
            messages: Raw messages from database (from load_conversation_full)
            current_model: Current model name for thinking extraction

        Returns:
            List of UIMessage objects ready for display
        """
        # Pre-process messages to merge consecutive assistant messages
        processed_messages = (
            ConversationDisplayService._merge_consecutive_assistant_messages(messages)
        )

        # Transform messages to UI format
        ui_messages = []
        for msg in processed_messages:
            role = msg["role"]
            content = msg["content"]
            tool_calls_raw = msg.get("tool_calls", [])
            attachments = msg.get("attachments", [])

            # Skip system and tool messages in display
            # Tool results are shown via the 🛠 button modal
            if role in ("system", "tool"):
                continue

            # Map database tool_call structure to UI format
            tool_calls = ConversationDisplayService._transform_tool_calls(
                tool_calls_raw
            )

            # Handle multimodal content (deserialize JSON if needed)
            display_content = ConversationDisplayService._extract_display_content(
                content
            )

            # Only create UI message for:
            # - Assistant messages (always, even if empty, for 🛠 button)
            # - User messages with content
            if role == "assistant" or (role == "user" and display_content):
                # Extract thinking for assistant messages
                thinking_to_display = None
                message_content = display_content or ""

                if role == "assistant" and message_content.strip():
                    thinking, response_text = extract_reasoning(
                        message_content, model_name=current_model
                    )
                    message_content = response_text
                    thinking_to_display = thinking if thinking else None

                # Get metadata from database
                token_count = msg.get("tokens")
                tokens_per_second = msg.get("tokens_per_second")
                time_to_first_token = msg.get("time_to_first_token")

                ui_message = UIMessage(
                    role=role,
                    content=message_content,
                    tool_calls=tool_calls if tool_calls else None,
                    attachments=attachments if attachments and role == "user" else None,
                    message_id=msg.get("id"),
                    token_count=token_count,
                    tokens_per_second=tokens_per_second,
                    time_to_first_token=time_to_first_token,
                    thinking_content=thinking_to_display
                    if role == "assistant"
                    else None,
                )
                ui_messages.append(ui_message)

        return ui_messages

    @staticmethod
    def _merge_consecutive_assistant_messages(
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge consecutive assistant messages (one with tools, one with content).

        This handles the case where an assistant message has tool_calls but no content,
        followed by tool result messages, followed by another assistant message with
        content. We merge the tool_calls from the first into the content message.

        Args:
            messages: Raw messages from database

        Returns:
            Processed messages with consecutive assistant messages merged
        """
        processed_messages = []
        i = 0
        while i < len(messages):
            msg = messages[i]

            # Check if this is an assistant message with tools but no content
            # and another assistant message follows later (after tool messages)
            if (
                msg["role"] == "assistant"
                and msg.get("tool_calls")
                and not msg["content"].strip()
                and i + 1 < len(messages)
            ):
                # Look ahead for tool message(s) and next assistant message
                next_idx = i + 1
                # Skip tool result messages
                while next_idx < len(messages) and messages[next_idx]["role"] == "tool":
                    next_idx += 1

                # If next non-tool message is assistant with content, merge them
                if (
                    next_idx < len(messages)
                    and messages[next_idx]["role"] == "assistant"
                    and messages[next_idx]["content"].strip()
                ):
                    # Merge: use tool_calls from first, content from second
                    merged = {
                        **messages[next_idx],
                        "tool_calls": msg["tool_calls"],
                    }
                    processed_messages.append(merged)
                    i = next_idx + 1  # Skip both messages
                    continue

            processed_messages.append(msg)
            i += 1

        return processed_messages

    @staticmethod
    def _transform_tool_calls(
        tool_calls_raw: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform tool calls from database format to UI format.

        Database uses 'tool_name' key, but UI expects 'name' key.

        Args:
            tool_calls_raw: Tool calls from database

        Returns:
            Tool calls in UI format
        """
        tool_calls = []
        for tc in tool_calls_raw:
            tool_calls.append(
                {
                    "name": tc.get("tool_name", "unknown"),
                    "arguments": tc.get("arguments", {}),
                    "status": tc.get("status", "unknown"),
                    "result": tc.get("result"),
                    "id": tc.get("id"),
                    "type": "tool_call",
                }
            )
        return tool_calls

    @staticmethod
    def _extract_display_content(content: str) -> str:
        """Extract display content from potentially multimodal message.

        Handles deserialization of JSON-serialized multimodal content.

        Args:
            content: Raw content from database

        Returns:
            Display content (text only)
        """
        # Check if content looks like serialized multimodal message
        if content.strip().startswith("[") and "text" in content:
            try:
                content_list = json.loads(content)
                # Extract text parts only
                text_parts = []
                for part in content_list:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                return " ".join(text_parts)
            except (json.JSONDecodeError, TypeError, AttributeError):
                # If deserialization fails, return original content
                pass
        return content
