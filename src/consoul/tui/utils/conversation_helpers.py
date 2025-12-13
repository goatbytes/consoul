"""Conversation helper utilities for TUI.

Provides helper functions for extracting and processing conversation data,
reducing complexity in message handling and streaming logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.ai import ConversationHistory

logger = logging.getLogger(__name__)

__all__ = [
    "extract_tool_calls_from_conversation",
]


def extract_tool_calls_from_conversation(
    conversation: ConversationHistory,
) -> list[dict[str, Any]] | None:
    """Extract tool call data from conversation for UI display.

    Converts LangChain SDK types (AIMessage.tool_calls) to simple TUI data model
    (list[dict]) for presentation in MessageBubble widgets.

    Args:
        conversation: Conversation history containing messages

    Returns:
        List of tool call dicts with name, arguments, status, and result,
        or None if no tool calls found
    """
    from langchain_core.messages import AIMessage, ToolMessage

    # Find the most recent AIMessage with tool_calls
    ai_message = None
    for msg in reversed(conversation.messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            ai_message = msg
            break

    if not ai_message or not ai_message.tool_calls:
        return None

    # Build tool_calls_list with results from ToolMessages
    tool_calls_data = []
    for tool_call in ai_message.tool_calls:
        # Find corresponding ToolMessage result
        result = None
        status = "SUCCESS"
        for msg in conversation.messages:
            if isinstance(msg, ToolMessage) and msg.tool_call_id == tool_call["id"]:
                result = msg.content
                # Check if result indicates error
                if isinstance(result, str) and "error" in result.lower():
                    status = "ERROR"
                break

        tool_calls_data.append(
            {
                "name": tool_call["name"],
                "arguments": tool_call["args"],
                "status": status,
                "result": result,
            }
        )

    return tool_calls_data if tool_calls_data else None
