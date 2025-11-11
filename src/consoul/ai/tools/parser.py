"""Tool call parsing utilities for LangChain streaming responses.

Provides detection and parsing of tool_calls from AIMessage objects,
handling validation, error recovery, and multiple parallel tool calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage


@dataclass
class ParsedToolCall:
    """Parsed representation of a tool call from AIMessage.

    Attributes:
        id: Unique identifier for the tool call (from provider)
        name: Tool name to execute (e.g., 'bash_execute')
        arguments: Dictionary of arguments to pass to tool
        raw: Original raw tool call dict for debugging
    """

    id: str
    name: str
    arguments: dict[str, Any]
    raw: dict[str, Any]

    def __repr__(self) -> str:
        """Human-readable representation."""
        args_preview = str(self.arguments)[:50]
        if len(str(self.arguments)) > 50:
            args_preview += "..."
        return (
            f"ParsedToolCall(id={self.id!r}, name={self.name!r}, args={args_preview})"
        )


def parse_tool_calls(message: AIMessage) -> list[ParsedToolCall]:
    """Parse tool calls from an AIMessage object.

    Extracts and validates tool_calls from LangChain AIMessage, handling
    multiple parallel tool calls and malformed data gracefully.

    Args:
        message: AIMessage object potentially containing tool_calls

    Returns:
        List of parsed tool calls. Empty list if no tool calls or message is None.

    Example:
        >>> message.tool_calls = [
        ...     {'id': 'call_123', 'name': 'bash_execute',
        ...      'args': {'command': 'ls -la'}}
        ... ]
        >>> parsed = parse_tool_calls(message)
        >>> parsed[0].name
        'bash_execute'
        >>> parsed[0].arguments['command']
        'ls -la'

    Note:
        - Skips tool calls with missing required fields (id, name)
        - Handles invalid JSON in arguments gracefully
        - Returns empty list rather than raising on errors
        - Logs warnings for malformed tool calls
    """
    if message is None:
        return []

    # Check if message has tool_calls attribute
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return []

    parsed_calls: list[ParsedToolCall] = []

    for tool_call in message.tool_calls:
        try:
            # Validate required fields
            if not isinstance(tool_call, dict):
                continue

            tool_id = tool_call.get("id") or tool_call.get("call_id")
            tool_name = tool_call.get("name")

            if not tool_id or not tool_name:
                # Skip tool calls missing required fields
                continue

            # Extract arguments (may be dict or JSON string)
            raw_args = tool_call.get("args") or tool_call.get("arguments", {})

            # Parse arguments if JSON string
            if isinstance(raw_args, str):
                try:
                    arguments = json.loads(raw_args)
                except json.JSONDecodeError:
                    # Invalid JSON - skip this tool call
                    continue
            elif isinstance(raw_args, dict):
                arguments = raw_args
            else:
                # Unknown argument format - skip
                continue

            # Create parsed tool call
            parsed_call = ParsedToolCall(
                id=str(tool_id),
                name=str(tool_name),
                arguments=arguments,
                raw=tool_call,
            )
            parsed_calls.append(parsed_call)

        except Exception:
            # Silently skip malformed tool calls
            # (Don't crash the entire stream)
            continue

    return parsed_calls


def has_tool_calls(message: AIMessage | None) -> bool:
    """Check if an AIMessage contains any tool calls.

    Args:
        message: AIMessage object to check

    Returns:
        True if message has non-empty tool_calls, False otherwise

    Example:
        >>> if has_tool_calls(response):
        ...     parsed = parse_tool_calls(response)
    """
    if message is None:
        return False
    return hasattr(message, "tool_calls") and bool(message.tool_calls)
