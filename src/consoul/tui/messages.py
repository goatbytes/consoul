"""Custom Textual message types for TUI event communication.

This module defines custom message classes for event-driven communication
between TUI widgets and the main application.
"""

from __future__ import annotations

from textual.message import Message

__all__ = [
    "StreamComplete",
    "StreamError",
    "StreamToken",
]


class StreamToken(Message):
    """Message sent when a new token is received from AI stream.

    Args:
        token: The text token received from the AI provider
        conversation_id: ID of the conversation this token belongs to
    """

    def __init__(self, token: str, conversation_id: str | None = None) -> None:
        super().__init__()
        self.token = token
        self.conversation_id = conversation_id


class StreamComplete(Message):
    """Message sent when AI streaming completes successfully.

    Args:
        conversation_id: ID of the conversation that completed
        token_count: Total number of tokens in the response
    """

    def __init__(
        self, conversation_id: str | None = None, token_count: int = 0
    ) -> None:
        super().__init__()
        self.conversation_id = conversation_id
        self.token_count = token_count


class StreamError(Message):
    """Message sent when an error occurs during streaming.

    Args:
        error: The exception that occurred
        conversation_id: ID of the conversation where error occurred
    """

    def __init__(self, error: Exception, conversation_id: str | None = None) -> None:
        super().__init__()
        self.error = error
        self.conversation_id = conversation_id
